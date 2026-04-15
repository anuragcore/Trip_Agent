"""
★ PHASE 4 — Architect Agent

Plans the STRUCTURAL rhythm of a trip before the itinerary is written.
"""
from __future__ import annotations
import re
from app.services.llm_service import call_llm, is_llm_available


def run(dest: str, days: int, prefs: list, weather: list, start_date: str) -> dict:
    """Returns { base_area, pacing, must_dos, avoid_notes, source }"""
    if not is_llm_available():
        return _fallback(dest, days, prefs)

    pref_str = ", ".join(prefs) if prefs else "general sightseeing"

    weather_note = ""
    if weather:
        avg_max = round(sum(d.get("temp_max", 28) for d in weather) / len(weather))
        avg_min = round(sum(d.get("temp_min", 18) for d in weather) / len(weather))
        weather_note = f"Weather during trip: {avg_min}°C – {avg_max}°C"

    # Force the LLM to output ONLY the 4 answers, no preamble
    prompt = (
        f"You are a local travel expert for {dest}, India.\n"
        f"A traveller visits for {days} days from {start_date}. "
        f"Preferences: {pref_str}. {weather_note}\n\n"
        f"Answer each question in ONE sentence. "
        f"Output ONLY the 4 answers, numbered 1-4. No intro, no explanation.\n\n"
        f"1. Best neighbourhood / base area to stay in {dest}?\n"
        f"2. Ideal day-by-day pacing for {days} days (e.g. 'Day 1-2 beaches, Day 3 heritage...')?\n"
        f"3. Top 3 must-do experiences for someone who likes {pref_str}?\n"
        f"4. One key timing/logistics tip to avoid crowds or problems?"
    )

    raw = call_llm(prompt)
    if not raw or raw.startswith("__LLM"):
        return _fallback(dest, days, prefs)

    answers = _parse_numbered(raw, 4)

    return {
        "base_area":   answers[0] if len(answers) > 0 else f"Central {dest}",
        "pacing":      answers[1] if len(answers) > 1 else f"Balanced {days}-day plan",
        "must_dos":    answers[2] if len(answers) > 2 else "Local landmarks & food",
        "avoid_notes": answers[3] if len(answers) > 3 else "Avoid midday heat outdoors",
        "source":      "llm",
    }


def _parse_numbered(text: str, expected: int) -> list:
    """
    Extract answers from a numbered list.
    Handles: '1. answer', '1) answer', or falling back to non-empty lines.
    """
    # Try to find lines starting with a digit
    pattern = re.compile(r"^\s*\d+[.)]\s*(.+)", re.MULTILINE)
    matches = pattern.findall(text)
    if matches:
        return [m.strip() for m in matches if m.strip()]

    # Fallback: take non-empty, non-preamble lines
    skip = {"here are", "here's", "sure", "certainly", "of course", "answer"}
    lines = []
    for l in text.strip().split("\n"):
        l = l.strip()
        if not l:
            continue
        if any(kw in l.lower() for kw in skip) and len(l) < 60:
            continue
        lines.append(l)
    return lines[:expected]


def _fallback(dest: str, days: int, prefs: list) -> dict:
    return {
        "base_area":   f"Central {dest}",
        "pacing":      f"Day 1-2: orientation, Day 3+: deep exploration",
        "must_dos":    "Local landmarks, street food, scenic viewpoints",
        "avoid_notes": "Avoid midday heat for outdoor activities",
        "source":      "fallback",
    }
