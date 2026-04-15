"""
★ PHASE 4 — Mission Control

The top-level coordinator that replaces the single-shot Orchestrator.run().

Flow:
  1. POST /negotiate  → validates, generates trip_id, fires background thread
  2. Background thread runs 4 agents in sequence, pushing SSE events to a queue
  3. GET /negotiate/stream/{trip_id}  → SSE endpoint drains the queue

Agent order:
  🏗️  Architect  → structural trip plan
  🌤️  Logistics  → weather + cost (CostAgent)
  🗺️  Itinerary  → day-by-day (LLM or POI fallback)
  📄  Artifact   → downloadable trip brief
"""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime

from app.services.orchestrator import Orchestrator
from app.services.weather import get_weather_forecast, get_packing_suggestions
from app.services.cost_agent import CostAgent
from app.services.llm_service import (
    generate_reasoning, generate_itinerary, score_destination_llm,
)
from app.services.trip_store import trip_store
from app.services.agents import architect_agent, artifact_agent


# ── Singleton helpers ──────────────────────────────────────────────────────
_orch       = Orchestrator()
_cost_agent = CostAgent()

# Per trip_id event queues  { trip_id: queue.Queue }
_event_queues: dict[str, queue.Queue] = {}
_event_queues_lock = threading.Lock()


def get_or_create_queue(trip_id: str) -> queue.Queue:
    with _event_queues_lock:
        if trip_id not in _event_queues:
            _event_queues[trip_id] = queue.Queue()
        return _event_queues[trip_id]


def cleanup_queue(trip_id: str):
    with _event_queues_lock:
        _event_queues.pop(trip_id, None)


# ── SSE helpers ───────────────────────────────────────────────────────────

def _push(q: queue.Queue, agent: str, status: str, message: str = "", extra: dict | None = None):
    event = {"agent": agent, "status": status, "message": message}
    if extra:
        event.update(extra)
    q.put(event)


# ── Main dispatcher (runs in a background thread) ─────────────────────────

def dispatch(data: dict, trip_id: str):
    q = get_or_create_queue(trip_id)
    try:
        _run_pipeline(data, trip_id, q)
    except Exception as e:
        _push(q, "mission_control", "error", str(e))
    finally:
        # Sentinel so the SSE generator knows to stop
        q.put(None)


def _run_pipeline(data: dict, trip_id: str, q: queue.Queue):
    from_city    = data.get("from_city", "").strip()
    start_date   = data.get("start_date", "")
    end_date     = data.get("end_date", "")
    destinations = data.get("destinations", [])
    members      = data.get("members", [])

    # ── Compute days ──────────────────────────────────────────────────────
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").date()
    days     = (end_dt - start_dt).days + 1

    # ── Budget / prefs ────────────────────────────────────────────────────
    if members:
        budgets = [m.get("budget", 0) if isinstance(m, dict) else m.budget for m in members]
        budget  = min(b for b in budgets if b > 0) if budgets else data.get("budget", 5000)
    else:
        budget = data.get("budget", 5000) or 5000

    raw_prefs = []
    for m in members:
        prf = m.get("preferences", "") if isinstance(m, dict) else m.preferences
        raw_prefs.extend([p.strip() for p in prf.split(",") if p.strip()])
    prefs = list(dict.fromkeys([p.lower() for p in raw_prefs]))

    # ════════════════════════════════════════════════════════════════════
    # AGENT 1 — Logistics (weather + cost per destination)
    # ════════════════════════════════════════════════════════════════════
    _push(q, "logistics", "running", f"Fetching weather & pricing for {len(destinations)} destination(s)…")

    evaluations = []
    dest_km     = {}
    for dest in destinations:
        km            = _orch.distance(from_city, dest)
        dest_km[dest] = km
        h_cost, mode, h_breakdown = _orch.estimate_cost(dest, days, from_city, prefs)
        agent_res = _cost_agent.estimate(
            dest=dest, from_city=from_city,
            start_date=start_date, end_date=end_date,
            days=days, km=km, mode_hint=mode, prefs=prefs, budget=budget,
        )
        if agent_res:
            cost, breakdown  = agent_res["total"], {
                "travel": agent_res["travel"], "hotel": agent_res["hotel"],
                "food":   agent_res["food"],   "activities": agent_res["activities"],
                "total":  agent_res["total"],
            }
            season_note, cost_source = agent_res.get("season_note", ""), "llm_agent"
        else:
            cost, breakdown, season_note, cost_source = h_cost, h_breakdown, "", "heuristic"

        llm_sc = score_destination_llm({
            "destination": dest, "cost": cost, "budget": budget,
            "preferences": prefs, "start_date": start_date, "weather": [],
        })
        if llm_sc:
            score, score_reason, score_source = llm_sc["score"], llm_sc["reason"], "llm"
        else:
            score, score_reason, score_source = _orch.score(dest, cost, budget, prefs), "", "heuristic"

        evaluations.append({
            "destination": dest, "cost": cost, "score": score, "mode": mode,
            "within_budget": cost <= budget, "breakdown": breakdown,
            "season_note": season_note, "cost_source": cost_source,
            "score_reason": score_reason, "score_source": score_source,
        })

    within = [e for e in evaluations if e["within_budget"]]
    best       = max(within, key=lambda e: e["score"]) if within else min(evaluations, key=lambda e: e["cost"])
    all_exceed = not bool(within)
    best_dest  = best["destination"]
    best_km    = dest_km.get(best_dest, 1200.0)

    # Fetch actual weather for best destination
    weather = get_weather_forecast(best_dest, start_date, end_date)
    _push(q, "logistics", "done",
          f"Selected {best_dest} — ₹{best['cost']:,} | weather loaded",
          {"weather": weather, "evaluations": [{k: v for k, v in e.items() if k != "breakdown"} for e in evaluations]})

    # ════════════════════════════════════════════════════════════════════
    # AGENT 2 — Architect (structural trip plan)
    # ════════════════════════════════════════════════════════════════════
    _push(q, "architect", "running", f"Planning structural rhythm for {best_dest}…")
    arch = architect_agent.run(best_dest, days, prefs, weather, start_date)
    _push(q, "architect", "done",
          f"Base: {arch.get('base_area', best_dest)} | Pacing mapped",
          {"architect": arch})

    # ════════════════════════════════════════════════════════════════════
    # AGENT 3 — Itinerary (LLM day-by-day, informed by architect)
    # ════════════════════════════════════════════════════════════════════
    _push(q, "itinerary", "running", f"Writing {days}-day itinerary with real weather…")

    # Enrich the LLM itinerary prompt with architect context
    llm_itin = generate_itinerary({
        "destination": best_dest, "days": days, "start_date": start_date,
        "from_city": from_city, "preferences": prefs,
        "weather": weather, "km": best_km, "mode": best["mode"],
        # Phase 4: pass architect context
        "base_area": arch.get("base_area", ""),
        "pacing":    arch.get("pacing", ""),
        "must_dos":  arch.get("must_dos", ""),
    })

    if llm_itin:
        itinerary, itin_source = llm_itin, "llm"
    else:
        itinerary, itin_source = _orch.build_itinerary(best_dest, days, prefs, start_date), "poi_fallback"

    _push(q, "itinerary", "done",
          f"{'AI-written' if itin_source == 'llm' else 'Template'} itinerary ready ({days} days)",
          {"itinerary": itinerary, "itinerary_source": itin_source})

    # ════════════════════════════════════════════════════════════════════
    # Auxiliary: hotel, packing, reasoning
    # ════════════════════════════════════════════════════════════════════
    hotel    = _orch.recommend_hotel(budget, days, prefs)
    packing  = get_packing_suggestions(weather, prefs)
    reasoning = generate_reasoning({
        "destination": best_dest, "cost": best["cost"], "budget": budget,
        "preferences": prefs, "evaluations": evaluations,
        "start_date": start_date, "end_date": end_date,
        "all_exceed": all_exceed, "weather": weather,
    })

    # Assemble full result
    trip_result = {
        "destination": best_dest, "cost": best["cost"],
        "travel": best["mode"], "hotel": hotel,
        "itinerary": itinerary, "reasoning": reasoning,
        "budget_breakdown": best["breakdown"], "weather": weather,
        "packing": packing, "season_note": best.get("season_note", ""),
        "score_reason": best.get("score_reason", ""), "architect": arch,
        "all_scores": [{k: v for k, v in e.items() if k != "breakdown"} for e in evaluations],
        "meta": {
            "budget": budget, "all_exceed": all_exceed,
            "from_city": from_city, "start_date": start_date,
            "end_date": end_date, "days": days, "preferences": prefs,
            "member_count": len(members) if members else 1,
            "itinerary_source": itin_source,
            "cost_source": best.get("cost_source", "heuristic"),
            "score_source": best.get("score_source", "heuristic"),
        },
    }

    # ════════════════════════════════════════════════════════════════════
    # AGENT 4 — Artifact (Trip Brief markdown)
    # ════════════════════════════════════════════════════════════════════
    _push(q, "artifact", "running", "Generating downloadable Trip Brief…")
    trip_brief = artifact_agent.run(trip_result)
    trip_result["trip_brief"] = trip_brief
    _push(q, "artifact", "done", "Trip Brief ready — download available")

    # ════════════════════════════════════════════════════════════════════
    # Persist + emit final result
    # ════════════════════════════════════════════════════════════════════
    try:
        saved_id = trip_store.save(trip_result)
        trip_result["trip_id"] = saved_id
    except Exception:
        trip_result["trip_id"] = trip_id

    trip_store.update(trip_id, trip_result)   # ensure correct id is retrievable
    _push(q, "mission_control", "complete", f"Trip to {best_dest} planned!", {"result": trip_result})
