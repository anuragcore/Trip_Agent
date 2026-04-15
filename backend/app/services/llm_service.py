from __future__ import annotations
import requests
from app.core.config import settings

_LLM_UNAVAILABLE = "__LLM_UNAVAILABLE__"
_LLM_TIMEOUT = "__LLM_TIMEOUT__"
_LLM_ERROR = "__LLM_ERROR__"


def call_llm(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=settings.LLM_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.Timeout:
        return _LLM_TIMEOUT
    except requests.exceptions.ConnectionError:
        return _LLM_UNAVAILABLE
    except Exception:
        return _LLM_ERROR


def is_llm_available() -> bool:
    try:
        resp = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
# Reasoning
# ══════════════════════════════════════════════════════════════════════

def generate_reasoning(payload: dict) -> str:
    llm_ok = is_llm_available()

    if llm_ok:
        dest       = payload.get("destination", "Unknown")
        cost       = payload.get("cost", 0)
        budget     = payload.get("budget", 0)
        prefs      = payload.get("preferences", [])
        evaluations = payload.get("evaluations", [])
        start_date = payload.get("start_date", "")
        end_date   = payload.get("end_date", "")
        weather    = payload.get("weather", [])

        eval_str = "\n".join(
            [f"  - {e['destination']}: Rs{e['cost']}, score={e['score']:.1f}, mode={e['mode']}"
             for e in evaluations]
        )

        weather_note = ""
        if weather:
            avg_max = round(sum(d.get("temp_max", 30) for d in weather) / len(weather))
            avg_min = round(sum(d.get("temp_min", 20) for d in weather) / len(weather))
            first_cond = weather[0].get("condition", "")
            weather_note = f"Expected weather: {avg_min}C - {avg_max}C, {first_cond}"

        prompt = (
            f"You are TripAI, an expert Indian travel planner. "
            f"Explain in 3-4 sentences why {dest} was selected for this trip.\n\n"
            f"Trip dates: {start_date} to {end_date}\n"
            f"User budget: Rs{budget}\n"
            f"Selected destination cost: Rs{cost}\n"
            f"User preferences: {', '.join(prefs)}\n"
            f"{weather_note}\n\n"
            f"All destinations evaluated:\n{eval_str}\n\n"
            f"Rules:\n"
            f"- If cost > budget, you MUST explicitly say it exceeds budget\n"
            f"- Weave in the weather context naturally\n"
            f"- Be specific about why {dest} matches the preferences\n"
            f"- Keep it warm, conversational, and helpful (3-4 sentences only)"
        )

        result = call_llm(prompt)
        if result not in (_LLM_UNAVAILABLE, _LLM_TIMEOUT, _LLM_ERROR):
            return f"🤖 AI Reasoning\n\n{result}"

    # ── Fallback template ──
    if not settings.FALLBACK_MODE:
        return "AI reasoning unavailable."

    dest        = payload.get("destination", "Unknown")
    cost        = payload.get("cost", 0)
    budget      = payload.get("budget", 0)
    prefs       = payload.get("preferences", [])
    evaluations = payload.get("evaluations", [])
    all_exceed  = payload.get("all_exceed", False)
    start_date  = payload.get("start_date", "")
    end_date    = payload.get("end_date", "")
    weather     = payload.get("weather", [])

    if all_exceed:
        budget_note = (
            f"All destinations exceed your Rs{budget} budget. "
            f"{dest} was chosen as the most affordable option."
        )
    elif cost <= budget:
        budget_note = f"{dest} fits within your Rs{budget} budget at Rs{cost}."
    else:
        budget_note = f"{dest} (Rs{cost}) slightly exceeds your Rs{budget} budget."

    weather_note = ""
    if weather:
        avg_max = round(sum(d.get("temp_max", 30) for d in weather) / len(weather))
        avg_min = round(sum(d.get("temp_min", 20) for d in weather) / len(weather))
        weather_note = f"\n🌡️ Weather: {avg_min}°C – {avg_max}°C during your stay."

    pref_str   = ", ".join(prefs) if prefs else "general travel"
    eval_lines = "\n".join(
        [f"  • {e['destination']}: Rs{e['cost']} via {e['mode']} — score {e['score']:.0f}"
         for e in evaluations]
    )

    return (
        f"🤖 AI Reasoning (Template Mode)\n\n"
        f"{budget_note}{weather_note}\n\n"
        f"Trip window: {start_date} → {end_date}\n"
        f"Your preferences ({pref_str}) were scored against each destination "
        f"and {dest} ranked highest.\n\n"
        f"All destinations evaluated:\n{eval_lines}\n\n"
        f"💡 Tip: Start Ollama (`ollama serve`) for richer AI reasoning."
    )


# ══════════════════════════════════════════════════════════════════════
# ★ PHASE 2 — LLM-First Itinerary Generation
# ══════════════════════════════════════════════════════════════════════

def _build_weather_summary(weather: list) -> str:
    """Convert weather list into a human-readable block for LLM prompts."""
    if not weather:
        return "Weather data unavailable."
    lines = []
    for d in weather:
        lines.append(
            f"  {d['date']}: {d['temp_min']}C - {d['temp_max']}C, "
            f"{d['condition']}, rain chance {d['rain_chance']}%"
        )
    return "\n".join(lines)


def _travel_time_hint(km: float, mode: str) -> str:
    """
    Returns a travel-time recommendation that the LLM can weave into Day 1.
    E.g. 'Take the overnight Volvo bus and arrive fresh on Day 1 morning'.
    """
    mode_lower = mode.lower()
    if km > 800 or "flight" in mode_lower:
        return (
            "Recommend an early morning or late-night flight so the traveller "
            "arrives by Day 1 morning and gets the full day at the destination."
        )
    elif km > 300 or "3ac" in mode_lower or "sleeper" in mode_lower:
        return (
            "Recommend an overnight train or Volvo bus — depart the evening "
            "before Day 1, arrive fresh in the morning, saving a hotel night "
            "and hitting the ground running."
        )
    else:
        return (
            "Short drive/bus. Suggest departing early morning so the traveller "
            "can check-in by noon and enjoy the afternoon."
        )


def generate_itinerary(payload: dict):
    """
    ★ Phase 2 core: prompt the LLM to act as a local travel expert and produce
    a weather-grounded, timing-aware day-by-day itinerary.

    Returns a list of {day, title, activities} dicts, or None if LLM unavailable.
    """
    dest       = payload.get("destination", "")
    days       = payload.get("days", 3)
    start_date = payload.get("start_date", "")
    from_city  = payload.get("from_city", "")
    prefs      = payload.get("preferences", [])
    weather    = payload.get("weather", [])
    km         = payload.get("km", 500)
    mode       = payload.get("mode", "")

    weather_summary = _build_weather_summary(weather)
    travel_hint     = _travel_time_hint(km, mode)
    pref_str        = ", ".join(prefs) if prefs else "general travel"

    prompt = (
        f"You are a seasoned local travel expert for India. "
        f"Create a vivid, realistic {days}-day itinerary for {dest}.\n\n"
        f"Trip details:\n"
        f"- Traveller starts from: {from_city} ({km:.0f} km away, mode: {mode})\n"
        f"- Travel dates: {start_date} ({days} days total)\n"
        f"- Traveller preferences: {pref_str}\n\n"
        f"Actual weather forecast for the trip:\n{weather_summary}\n\n"
        f"Travel time recommendation:\n{travel_hint}\n\n"
        f"Instructions (follow EXACTLY):\n"
        f"1. Use the real weather data. If hot, suggest early-morning/evening outings. "
        f"If rainy, prefer indoor/covered spots. If cold/snowy, include warmth breaks.\n"
        f"2. Include 3 activities per day with time-of-day labels: Morning, Afternoon, Evening.\n"
        f"3. Day 1 must factor in arrival logistics from {from_city}.\n"
        f"4. The final day must end with departure preparation.\n"
        f"5. Use real place names, restaurants, and street names where known.\n"
        f"6. Format your output EXACTLY like this (start immediately with Day 1, no preamble):\n\n"
        f"Day 1: [Creative title]\n"
        f"- Morning: [Activity]\n"
        f"- Afternoon: [Activity]\n"
        f"- Evening: [Activity]\n\n"
        f"Day 2: [Creative title]\n"
        f"- Morning: [Activity]\n"
        f"- Afternoon: [Activity]\n"
        f"- Evening: [Activity]\n\n"
        f"(continue for all {days} days)"
    )

    result = call_llm(prompt)
    if result in (_LLM_UNAVAILABLE, _LLM_TIMEOUT, _LLM_ERROR, ""):
        return None

    parsed = parse_llm_itinerary(result, days, dest)
    return parsed if parsed else None


def parse_llm_itinerary(text: str, days: int, dest: str) -> list:
    """
    Parse LLM-generated itinerary text into [{day, title, activities}] objects.
    Handles formatting variations gracefully; fills gaps when the LLM skips days.
    """
    import re

    itinerary   = []
    day_pattern = re.compile(r"(?:^|\n)\s*Day\s+(\d+)\s*[:\-\u2013]\s*(.+)", re.IGNORECASE)
    act_pattern = re.compile(
        r"^\s*[-\u2022*]\s*(?:(Morning|Afternoon|Evening|Night|Noon)\s*[:：]\s*)?(.+)",
        re.IGNORECASE,
    )

    matches = list(day_pattern.finditer(text))

    for i, match in enumerate(matches):
        day_num = int(match.group(1))
        title   = match.group(2).strip().strip('"').strip("'")

        block_start = match.end()
        block_end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block       = text[block_start:block_end]

        activities = []
        for line in block.split("\n"):
            m = act_pattern.match(line)
            if m:
                time_label = m.group(1)
                activity   = m.group(2).strip()
                activities.append(f"{time_label}: {activity}" if time_label else activity)

        if not activities:
            activities = [f"Explore {dest}"]

        if not title or len(title) < 3:
            if day_num == 1:
                title = f"Arrival & First Impressions in {dest}"
            elif day_num == days:
                title = f"Final Day & Departure from {dest}"
            else:
                title = f"Exploring {dest} — Day {day_num}"

        itinerary.append({"day": day_num, "title": title, "activities": activities})

    if not itinerary:
        return []

    # Fill any days the LLM skipped
    present = {d["day"] for d in itinerary}
    for d in range(1, days + 1):
        if d not in present:
            itinerary.append({
                "day": d,
                "title": f"Day {d} in {dest}",
                "activities": [
                    f"Morning: Explore local attractions in {dest}",
                    "Afternoon: Visit markets and street food stalls",
                    "Evening: Relax and enjoy local cuisine",
                ],
            })

    itinerary.sort(key=lambda x: x["day"])
    return itinerary


# ══════════════════════════════════════════════════════════════════════
# ★ PHASE 3 — LLM-Based Preference Scorer
# ══════════════════════════════════════════════════════════════════════

def score_destination_llm(payload: dict) -> dict | None:
    """
    Phase 3: Ask the LLM to score a destination against the traveller's
    *full* preference string — including nuanced, free-text vibes like
    "dark academia, vegan food, quiet" — rather than a fixed keyword list.

    Returns { score: float, reason: str } or None if LLM unavailable.
    The caller keeps the heuristic scorer as fallback.
    """
    import json, re

    dest       = payload.get("destination", "")
    cost       = payload.get("cost", 0)
    budget     = payload.get("budget", 0)
    prefs      = payload.get("preferences", [])   # list of strings
    raw_prefs  = payload.get("raw_preferences", "") # original free-text if available
    start_date = payload.get("start_date", "")
    weather    = payload.get("weather", [])

    pref_str = raw_prefs or (", ".join(prefs) if prefs else "general travel")

    weather_note = ""
    if weather:
        avg_max = round(sum(d.get("temp_max", 28) for d in weather) / len(weather))
        avg_min = round(sum(d.get("temp_min", 18) for d in weather) / len(weather))
        weather_note = f"Weather during trip: {avg_min}°C – {avg_max}°C"

    budget_note = (
        f"Cost (₹{cost}) is within the ₹{budget} budget."
        if cost <= budget else
        f"Cost (₹{cost}) EXCEEDS the ₹{budget} budget by ₹{cost - budget}."
    )

    prompt = (
        f"You are an expert Indian travel advisor. Score how well {dest} matches "
        f"this traveller's preferences.\n\n"
        f"Traveller preferences: \"{pref_str}\"\n"
        f"Travel date: {start_date}\n"
        f"{weather_note}\n"
        f"{budget_note}\n\n"
        f"Think about:\n"
        f"- Does {dest} genuinely match the vibe/mood/personality described?\n"
        f"- Are the activities available there suited to those preferences?\n"
        f"- Does the weather align?\n"
        f"- Budget situation?\n\n"
        f"Return ONLY valid JSON — no markdown, no extra text:\n"
        f'{{\n'
        f'  "score": <integer 0-150>,\n'
        f'  "reason": "<one sentence explaining the score>"\n'
        f'}}'
    )

    raw = call_llm(prompt)
    if not raw or raw.startswith("__LLM"):
        return None

    # Extract JSON
    match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            score  = float(data.get("score", 100))
            reason = str(data.get("reason", "")).strip()
            # Clamp to valid range
            score = max(0.0, min(150.0, score))
            return {"score": round(score, 1), "reason": reason}
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return None
