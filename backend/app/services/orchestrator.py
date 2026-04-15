from __future__ import annotations
import math
import random
import requests
from datetime import datetime, date

from app.services.llm_service import generate_reasoning, generate_itinerary, score_destination_llm
from app.services.weather import get_weather_forecast, get_packing_suggestions
from app.services.cost_agent import CostAgent

_cost_agent = CostAgent()


class Orchestrator:
    def __init__(self):
        self.cache: dict = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Geocoding
    # ─────────────────────────────────────────────────────────────────────────

    def get_coords(self, city: str) -> tuple[float, float] | None:
        city_key = city.lower().strip()
        if city_key in self.cache:
            return self.cache[city_key]
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"city": city, "country": "india", "format": "json"},
                headers={"User-Agent": "tripai/2.0"},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                self.cache[city_key] = coords
                return coords
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Distance (Haversine)
    # ─────────────────────────────────────────────────────────────────────────

    def distance(self, city1: str, city2: str) -> float:
        c1 = self.get_coords(city1)
        c2 = self.get_coords(city2)
        if not c1 or not c2:
            return 1200.0  # default fallback

        lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
        lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
        dlat, dlon = lat2 - lat1, lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ─────────────────────────────────────────────────────────────────────────
    # Cost Estimation  ★ PHASE 1: Return trip — travel cost × 2
    # ─────────────────────────────────────────────────────────────────────────

    def estimate_cost(
        self, dest: str, days: int, from_city: str, prefs: list
    ) -> tuple[float, str, dict]:
        km = self.distance(from_city, dest)
        prefs_lower = [p.lower() for p in prefs]

        # ── One-way travel cost ──
        if km < 300:
            one_way = 500
            mode = "🚗 Car / Bus"
        elif km < 800:
            one_way = 1200
            mode = "🚂 Train (Sleeper)"
        elif km < 1500:
            one_way = 2500
            mode = "🚂 Train (3AC)"
        else:
            one_way = 4500
            mode = "✈️ Flight"

        # Phase 1: Return trip — both directions included
        total_travel_cost = one_way * 2

        # ── Hotel ──
        if "luxury" in prefs_lower:
            hotel_per_night = 5000
        elif any(p in prefs_lower for p in ["budget", "cheap"]):
            hotel_per_night = 1000
        elif "mid-range" in prefs_lower:
            hotel_per_night = 2500
        else:
            hotel_per_night = 2000
        hotel_cost = hotel_per_night * days

        # ── Food ──
        if "luxury" in prefs_lower:
            food_per_day = 1200
        elif any(p in prefs_lower for p in ["food", "culinary"]):
            food_per_day = 900
        else:
            food_per_day = 600
        food_cost = food_per_day * days

        # ── Activities ──
        if "nightlife" in prefs_lower:
            act_per_day = 1200
        elif "shopping" in prefs_lower:
            act_per_day = 1000
        elif any(p in prefs_lower for p in ["adventure", "trekking"]):
            act_per_day = 800
        else:
            act_per_day = 400
        activities_cost = act_per_day * days

        total = total_travel_cost + hotel_cost + food_cost + activities_cost

        breakdown = {
            "travel": total_travel_cost,
            "hotel": hotel_cost,
            "food": food_cost,
            "activities": activities_cost,
            "total": total,
        }
        return total, f"{from_city} → {dest} via {mode} (return)", breakdown

    # ─────────────────────────────────────────────────────────────────────────
    # Destination Scoring
    # ─────────────────────────────────────────────────────────────────────────

    PREF_MAP = {
        "adventure": {"ladakh", "manali", "sikkim", "rishikesh", "coorg", "spiti", "meghalaya", "auli"},
        "food": {"delhi", "amritsar", "mumbai", "lucknow", "hyderabad", "kolkata", "chennai", "jaipur"},
        "culture": {"jaipur", "varanasi", "tirupati", "hampi", "mysore", "udaipur", "agra", "khajuraho"},
        "beach": {"goa", "pondicherry", "kerala", "andaman", "kovalam", "puri", "varkala", "gokarna"},
        "mountains": {"manali", "shimla", "darjeeling", "mussoorie", "nainital", "ooty", "munnar", "sikkim"},
        "spiritual": {"varanasi", "tirupati", "rishikesh", "haridwar", "amritsar", "bodh gaya", "mathura"},
        "nightlife": {"goa", "mumbai", "delhi", "bangalore", "pune", "hyderabad"},
        "shopping": {"delhi", "mumbai", "jaipur", "bangalore", "kolkata", "hyderabad"},
        "luxury": {"udaipur", "goa", "kerala", "jaipur", "shimla", "andaman"},
        "trekking": {"ladakh", "manali", "sikkim", "spiti", "meghalaya", "kodaikanal", "munnar"},
    }

    def score(self, dest: str, cost: float, budget: float, prefs: list) -> float:
        score = 100.0
        dest_lower = dest.lower().strip()

        # Budget adjustments
        if cost > budget:
            score -= min(50, (cost - budget) / 100)
        else:
            score += min(10, (budget - cost) / 200)

        # Preference matching
        matched = 0
        for pref in prefs:
            cities = self.PREF_MAP.get(pref.lower(), set())
            if dest_lower in cities:
                score += 15
                matched += 1

        if matched >= 2:
            score += 10

        return round(score, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Itinerary Builder
    # ─────────────────────────────────────────────────────────────────────────

    POI_DB = {
        "goa": {
            "beaches": ["Baga Beach", "Calangute Beach", "Anjuna Beach", "Palolem Beach", "Vagator Beach"],
            "landmarks": ["Basilica of Bom Jesus", "Fort Aguada", "Chapora Fort", "Se Cathedral"],
            "food_spots": ["Thalassa Greek Restaurant", "Fisherman's Wharf", "Gunpowder Panjim", "Cafe Lilliput"],
            "activities": ["Water sports at Baga", "Scuba diving @ Grande Island", "Dolphin spotting cruise", "Casino night"],
            "culture": ["Old Goa churches tour", "Fontainhas Latin Quarter walk", "Goa Carnival vibes"],
        },
        "manali": {
            "nature": ["Solang Valley", "Rohtang Pass", "Hadimba Temple meadow", "Bhrigu Lake trek"],
            "landmarks": ["Hadimba Devi Temple", "Manu Temple", "Tibetan Monastery"],
            "activities": ["Paragliding at Solang", "Snow skiing at Rohtang", "River rafting on Beas"],
            "food_spots": ["Johnson's Cafe", "Cafe 1947", "Drifters Inn", "Lazy Dog Lounge"],
            "culture": ["Old Manali village walk", "Mall Road stroll"],
        },
        "jaipur": {
            "landmarks": ["Amber Fort", "Hawa Mahal", "City Palace", "Jantar Mantar", "Nahargarh Fort"],
            "culture": ["Block printing workshop", "Puppet show at Chokhi Dhani", "Sound & Light show at Amber"],
            "food_spots": ["Laxmi Mishthan Bhandar", "Rawat Mishtan Bhandar", "1135 AD at Amber Fort"],
            "activities": ["Elephant ride at Amer", "Hot-air balloon over pink city", "Gem shopping in Johari Bazaar"],
            "shopping": ["Johari Bazaar", "Bapu Bazaar", "Tripolia Bazaar"],
        },
        "varanasi": {
            "landmarks": ["Kashi Vishwanath Temple", "Sarnath", "Ramnagar Fort", "Alamgir Mosque"],
            "culture": ["Ganga Aarti at Dashashwamedh Ghat", "Sunrise boat ride on Ganges", "Silk weaving workshop"],
            "food_spots": ["Kashi Chat Bhandar", "Deena Chat Bhandar", "Blue Lassi Shop"],
            "activities": ["Evening aarti ceremony", "Dev Deepawali if in season", "Silk saree shopping"],
            "spiritual": ["Manikarnika Ghat visit", "Assi Ghat meditation"],
        },
        "delhi": {
            "landmarks": ["Red Fort", "Qutub Minar", "India Gate", "Humayun's Tomb", "Lotus Temple"],
            "culture": ["Hauz Khas Village", "Dilli Haat crafts market", "Chandni Chowk heritage walk"],
            "food_spots": ["Karim's Jama Masjid", "Paranthe Wali Gali", "Khan Chacha", "Indian Accent"],
            "activities": ["Metro ride across Old & New Delhi", "Connaught Place evening", "Sarojini Nagar shopping"],
            "nightlife": ["Hauz Khas bar scene", "Cyber Hub Gurgaon", "Auro Kitchen & Bar"],
        },
        "kerala": {
            "nature": ["Alleppey backwaters", "Munnar tea gardens", "Periyar Tiger Reserve", "Varkala cliffs"],
            "landmarks": ["Padmanabhaswamy Temple", "Fort Kochi", "Mattancherry Palace"],
            "activities": ["Houseboat stay in Alleppey", "Kathakali dance performance", "Ayurvedic massage"],
            "food_spots": ["Malabar Junction", "Dal Roti Kochi", "Casino Hotel buffet"],
            "culture": ["Fort Kochi art galleries", "Jew Town antiques", "Spice plantation tour"],
        },
    }

    def build_itinerary(self, dest: str, days: int, prefs: list, start_date: str = "") -> list:
        dest_lower = dest.lower().strip()
        poi_data = self.POI_DB.get(dest_lower, {})

        # Flatten all POIs
        all_pois = []
        for cat_pois in poi_data.values():
            all_pois.extend(cat_pois)

        if not all_pois:
            # Generic fallback for unknown cities
            all_pois = [
                f"Famous landmarks of {dest}",
                f"Local market exploration in {dest}",
                f"Historical sites of {dest}",
                f"Street food tour in {dest}",
                f"Nature walk near {dest}",
                f"Cultural center / museum of {dest}",
                f"Sunset point near {dest}",
                f"Local temple / heritage site",
            ]

        random.shuffle(all_pois)
        prefs_lower = [p.lower() for p in prefs]

        itinerary = []
        poi_pool = list(all_pois)

        for day_num in range(1, days + 1):
            # Pick 3 activities, recycling pool if needed
            activities = []
            for _ in range(3):
                if not poi_pool:
                    poi_pool = list(all_pois)
                    random.shuffle(poi_pool)
                activities.append(poi_pool.pop())

            # Add food spot on food preference days
            if "food" in prefs_lower:
                food_spots = poi_data.get("food_spots", [])
                if food_spots:
                    activities.append(random.choice(food_spots))

            # Day titles
            if day_num == 1:
                title = f"Arrival & First Impressions in {dest}"
            elif day_num == days:
                title = f"Final Day & Departure from {dest}"
                activities.append("Pack up, souvenir shopping, and departure")
            else:
                title = f"Exploring {dest} — Day {day_num}"

            itinerary.append({"day": day_num, "title": title, "activities": activities})

        return itinerary

    # ─────────────────────────────────────────────────────────────────────────
    # Hotel Recommendation
    # ─────────────────────────────────────────────────────────────────────────

    def recommend_hotel(self, budget: float, days: int, prefs: list) -> str:
        prefs_lower = [p.lower() for p in prefs]
        if "luxury" in prefs_lower:
            return "🏰 5-Star Luxury Resort"
        per_day = budget / max(days, 1)
        if per_day < 1500:
            return "🏠 Budget Stay / Hostel"
        elif per_day < 3000:
            return "🏨 2-Star Hotel"
        elif per_day < 5000:
            return "🏨 3-Star Hotel"
        return "🏰 4-Star Premium Hotel"

    # ─────────────────────────────────────────────────────────────────────────
    # Main Entry Point  ★ PHASE 2: Fetch weather first, LLM-first itinerary
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, data: dict) -> dict:
        try:
            from_city    = data.get("from_city", "").strip()
            start_date   = data.get("start_date", "")
            end_date     = data.get("end_date", "")
            destinations = data.get("destinations", [])
            members      = data.get("members", [])

            if not from_city:
                return {"error": "Origin city is required."}
            if not destinations:
                return {"error": "At least one destination is required."}

            # ── Compute days from date range (Phase 1) ──
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").date()
                days     = (end_dt - start_dt).days + 1
                if days < 1:
                    return {"error": "end_date must be on or after start_date."}
                if days > 30:
                    return {"error": "Trip duration cannot exceed 30 days."}
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD."}

            # ── Budget resolution ──
            if members:
                budgets = [m.get("budget", 0) if isinstance(m, dict) else m.budget for m in members]
                budget  = min(b for b in budgets if b > 0) if budgets else data.get("budget", 5000)
            else:
                budget = data.get("budget", 5000) or 5000

            # ── Preference resolution ──
            raw_prefs = []
            for m in members:
                pref_str = m.get("preferences", "") if isinstance(m, dict) else m.preferences
                raw_prefs.extend([p.strip() for p in pref_str.split(",") if p.strip()])
            prefs = list(dict.fromkeys([p.lower() for p in raw_prefs]))

            # ── Score all destinations ──
            evaluations = []
            dest_km     = {}   # cache km per destination for later

            for dest in destinations:
                km            = self.distance(from_city, dest)
                dest_km[dest] = km

                # ── ★ Phase 3: CostAgent (LLM) → heuristic fallback ──
                heuristic_cost, mode, heuristic_breakdown = self.estimate_cost(
                    dest, days, from_city, prefs
                )
                agent_result = _cost_agent.estimate(
                    dest=dest, from_city=from_city,
                    start_date=start_date, end_date=end_date,
                    days=days, km=km, mode_hint=mode, prefs=prefs,
                    budget=budget,
                )
                if agent_result:
                    cost      = agent_result["total"]
                    breakdown = {
                        "travel":     agent_result["travel"],
                        "hotel":      agent_result["hotel"],
                        "food":       agent_result["food"],
                        "activities": agent_result["activities"],
                        "total":      agent_result["total"],
                    }
                    season_note  = agent_result.get("season_note", "")
                    cost_source  = "llm_agent"
                else:
                    cost         = heuristic_cost
                    breakdown    = heuristic_breakdown
                    season_note  = ""
                    cost_source  = "heuristic"

                within_budget = cost <= budget

                # ── ★ Phase 3: LLM Scorer → heuristic fallback ──
                # Weather not fetched yet at this point, so pass empty list.
                # Scores will be re-evaluated for the best pick after weather fetch.
                llm_score_result = score_destination_llm({
                    "destination":  dest,
                    "cost":         cost,
                    "budget":       budget,
                    "preferences":  prefs,
                    "start_date":   start_date,
                    "weather":      [],  # weather fetched after selection
                })
                if llm_score_result:
                    s            = llm_score_result["score"]
                    score_reason = llm_score_result["reason"]
                    score_source = "llm"
                else:
                    s            = self.score(dest, cost, budget, prefs)
                    score_reason = ""
                    score_source = "heuristic"

                evaluations.append({
                    "destination":   dest,
                    "cost":          cost,
                    "score":         s,
                    "mode":          mode,
                    "within_budget": within_budget,
                    "breakdown":     breakdown,
                    "season_note":   season_note,
                    "cost_source":   cost_source,
                    "score_reason":  score_reason,
                    "score_source":  score_source,
                })

            # ── Select best destination ──
            within = [e for e in evaluations if e["within_budget"]]
            if within:
                best       = max(within, key=lambda e: e["score"])
                all_exceed = False
            else:
                best       = min(evaluations, key=lambda e: e["cost"])
                all_exceed = True

            best_dest = best["destination"]
            best_km   = dest_km.get(best_dest, 1200.0)

            # ── ★ Phase 2: Fetch weather FIRST so it can inform the itinerary ──
            weather = get_weather_forecast(best_dest, start_date, end_date)

            # ── ★ Phase 2: LLM-first itinerary (falls back to POI database) ──
            llm_itinerary = generate_itinerary({
                "destination": best_dest,
                "days":        days,
                "start_date":  start_date,
                "from_city":   from_city,
                "preferences": prefs,
                "weather":     weather,        # real forecast data
                "km":          best_km,        # distance for travel hint
                "mode":        best["mode"],   # transport mode
            })

            # Fall back to POI-based builder when LLM is unavailable
            if llm_itinerary:
                itinerary          = llm_itinerary
                itinerary_source   = "llm"
            else:
                itinerary          = self.build_itinerary(best_dest, days, prefs, start_date)
                itinerary_source   = "poi_fallback"

            # ── Hotel ──
            hotel = self.recommend_hotel(budget, days, prefs)

            # ── Packing ──
            packing = get_packing_suggestions(weather, prefs)

            # ── LLM Reasoning (now includes weather context) ──
            reasoning = generate_reasoning({
                "destination": best_dest,
                "cost":        best["cost"],
                "budget":      budget,
                "preferences": prefs,
                "evaluations": evaluations,
                "start_date":  start_date,
                "end_date":    end_date,
                "all_exceed":  all_exceed,
                "weather":     weather,        # ★ Phase 2: weather context in reasoning
            })

            return {
                "destination":      best_dest,
                "cost":             best["cost"],
                "travel":           best["mode"],
                "hotel":            hotel,
                "itinerary":        itinerary,
                "reasoning":        reasoning,
                "budget_breakdown": best["breakdown"],
                "weather":          weather,
                "packing":          packing,
                "all_scores": [
                    {k: v for k, v in e.items() if k != "breakdown"}
                    for e in evaluations
                ],
                "season_note":  best.get("season_note", ""),
                "score_reason": best.get("score_reason", ""),
                "meta": {
                    "budget":           budget,
                    "all_exceed":       all_exceed,
                    "from_city":        from_city,
                    "start_date":       start_date,
                    "end_date":         end_date,
                    "days":             days,
                    "preferences":      prefs,
                    "member_count":     len(members) if members else 1,
                    "itinerary_source": itinerary_source,
                    "cost_source":      best.get("cost_source", "heuristic"),
                    "score_source":     best.get("score_source", "heuristic"),
                },
            }

        except Exception as e:
            return {"error": f"Orchestration failed: {str(e)}"}
