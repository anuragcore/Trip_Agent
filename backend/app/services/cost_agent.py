"""
★ PHASE 3 — Agentic Cost Estimation (v2 — grounded prompts)

Fixes over v1:
- Adds realistic per-tier price anchors so the LLM doesn't drift to luxury pricing
- Passes travel_per_person (one-way) as a hint derived from the mode so the LLM
  knows the order of magnitude before it answers
- Tightened sanity bounds: hotel_per_night capped at ₹12,000 (drops luxury outliers)
- Season label is now informational, not alarmist ("prices +20%" not "PEAK PREMIUM")
- Budget tier passed explicitly so LLM skews mid-range when budget < ₹40k/trip
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from app.services.llm_service import call_llm, is_llm_available


# ── Realistic one-way fare anchors by km band ──────────────────────────────
# These mirror the heuristic in orchestrator.estimate_cost() so the LLM
# has a concrete starting point and doesn't hallucinate flight prices
# for a train journey.

TRANSPORT_TIERS = [
    (300,  "road (bus / shared cab)",         250,   500),   # (max_km, label, low, high)
    (800,  "overnight train (Sleeper/3AC)",   800,  1500),
    (1500, "train (3AC/2AC)",                1800,  3500),
    (9999, "domestic flight",                3000,  7000),
]

def _transport_meta(km: float) -> tuple[str, int, int]:
    for max_km, label, low, high in TRANSPORT_TIERS:
        if km <= max_km:
            return label, low, high
    return "domestic flight", 3000, 7000


# ── Budget tier label ──────────────────────────────────────────────────────

def _budget_tier(daily_budget: float) -> str:
    if daily_budget < 2000:
        return "budget traveller (hostels, dhabas, local buses)"
    elif daily_budget < 5000:
        return "mid-range traveller (2-3 star hotels, popular restaurants)"
    else:
        return "premium traveller (4-star hotels, fine dining)"


# ── Seasonal note (informational, not alarmist) ───────────────────────────

def _season_label(month: int, dest: str) -> str:
    d = dest.lower()
    cold  = {"manali", "shimla", "ladakh", "spiti", "auli", "darjeeling", "sikkim"}
    beach = {"goa", "kerala", "andaman", "pondicherry", "varkala", "gokarna", "puri"}

    if any(c in d for c in cold):
        if month in (12, 1, 2):
            return "peak winter; hotels ~20-40% more expensive, roads may be snow-blocked"
        elif month in (6, 7, 8):
            return "monsoon / off-season; discounts of 20-30% available"
        else:
            return "shoulder season; moderate pricing"
    elif any(b in d for b in beach):
        if month in (11, 12, 1, 2, 3):
            return "peak tourist season; hotels ~15-25% above base rate"
        elif month in (6, 7, 8, 9):
            return "monsoon; discounts available but weather unpredictable"
        else:
            return "shoulder season; moderate pricing"
    else:
        if month in (10, 11, 12, 1, 2, 3):
            return "popular travel window; moderate price premium"
        elif month in (6, 7, 8):
            return "monsoon / off-peak; some discounts available"
        else:
            return "moderate season"


# ── JSON extraction ────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


# ── CostAgent ─────────────────────────────────────────────────────────────

class CostAgent:
    """
    Agentic cost estimator with grounded, budget-aware prompts.
    Returns None on any failure so the orchestrator falls back to heuristics.
    """

    def estimate(
        self,
        dest: str,
        from_city: str,
        start_date: str,
        end_date: str,
        days: int,
        km: float,
        mode_hint: str,
        prefs: list,
        budget: float = 0,
    ) -> dict | None:
        if not is_llm_available():
            return None

        try:
            month = int(start_date.split("-")[1])
        except (IndexError, ValueError):
            month = datetime.now().month

        transport_label, fare_low, fare_high = _transport_meta(km)
        season    = _season_label(month, dest)
        pref_str  = ", ".join(prefs) if prefs else "general travel"
        daily_bud = budget / max(days, 1) if budget > 0 else 3000
        tier      = _budget_tier(daily_bud)

        # Realistic mid-range hotel anchors per destination type
        if any(b in dest.lower() for b in ["goa", "kerala", "andaman"]):
            hotel_anchor = "₹1,800–₹4,500/night (beach resort area)"
        elif any(c in dest.lower() for c in ["manali", "shimla", "ladakh"]):
            hotel_anchor = "₹1,500–₹4,000/night (hill station)"
        elif any(c in dest.lower() for c in ["jaipur", "udaipur", "agra"]):
            hotel_anchor = "₹1,200–₹3,500/night (heritage city)"
        elif any(c in dest.lower() for c in ["mumbai", "delhi", "bangalore"]):
            hotel_anchor = "₹1,500–₹5,000/night (metro city)"
        else:
            hotel_anchor = "₹1,000–₹3,000/night (typical Indian city)"

        prompt = (
            f"You are a realistic Indian travel cost estimator. "
            f"Give me ACCURATE, ground-level market prices — not luxury rates.\n\n"
            f"Trip:\n"
            f"  From: {from_city}  →  To: {dest}\n"
            f"  Dates: {start_date} to {end_date} ({days} days)\n"
            f"  Distance: {km:.0f} km  |  Transport: {transport_label}\n"
            f"  Season: {season}\n"
            f"  Traveller type: {tier}\n"
            f"  Preferences: {pref_str}\n\n"
            f"Reference prices (use these as anchors, adjust for season):\n"
            f"  • One-way {transport_label} fare: ₹{fare_low}–₹{fare_high} per person\n"
            f"  • Hotel: {hotel_anchor}\n"
            f"  • Food: ₹400–₹900/day for mid-range restaurants\n"
            f"  • Activities: ₹300–₹800/day typical\n\n"
            f"Rules:\n"
            f"  - travel_return_total = one-way fare × 2 (return trip)\n"
            f"  - hotel_per_night is for {days - 1} nights (last day is departure)\n"
            f"  - DO NOT suggest luxury/5-star costs unless preferences explicitly say 'luxury'\n"
            f"  - Be realistic: a mid-range {days}-day India trip rarely exceeds ₹40,000 total\n\n"
            f"Return ONLY this JSON (integers, no markdown):\n"
            f"{{\n"
            f'  "travel_return_total": <integer>,\n'
            f'  "hotel_per_night": <integer>,\n'
            f'  "food_per_day": <integer>,\n'
            f'  "activities_per_day": <integer>,\n'
            f'  "season_note": "<one concise sentence about seasonal pricing>"\n'
            f"}}"
        )

        raw = call_llm(prompt)
        if not raw or raw.startswith("__LLM"):
            return None

        data = _extract_json(raw)
        if not data:
            return None

        try:
            travel          = int(data.get("travel_return_total", 0))
            hotel_per_night = int(data.get("hotel_per_night", 0))
            food_per_day    = int(data.get("food_per_day", 0))
            act_per_day     = int(data.get("activities_per_day", 0))
            season_note     = str(data.get("season_note", "")).strip()
        except (TypeError, ValueError):
            return None

        # Tightened sanity bounds — if LLM still goes wild, fall back
        one_way_max = fare_high * 3   # generous 3× headroom
        if not (fare_low // 2 <= travel <= one_way_max * 2):
            return None
        if not (300 <= hotel_per_night <= 12_000):   # max ₹12k/night
            return None
        if not (200 <= food_per_day <= 3_000):
            return None
        if not (0 <= act_per_day <= 5_000):
            return None

        nights           = max(days - 1, 1)  # nights = days minus departure day
        hotel_total      = hotel_per_night * nights
        food_total       = food_per_day    * days
        activities_total = act_per_day     * days
        total            = travel + hotel_total + food_total + activities_total

        return {
            "travel":           travel,
            "hotel":            hotel_total,
            "hotel_per_night":  hotel_per_night,
            "nights":           nights,
            "food":             food_total,
            "activities":       activities_total,
            "total":            total,
            "season_note":      season_note,
            "source":           "llm_agent",
        }
