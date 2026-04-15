from __future__ import annotations
import requests
from datetime import datetime, timedelta


def _weather_code_to_text(code: int) -> str:
    mapping = {
        0: "Clear sky ☀️",
        1: "Mainly clear 🌤️",
        2: "Partly cloudy ⛅",
        3: "Overcast ☁️",
        45: "Foggy 🌫️",
        48: "Icy fog 🌫️",
        51: "Light drizzle 🌦️",
        53: "Drizzle 🌦️",
        55: "Heavy drizzle 🌧️",
        61: "Slight rain 🌧️",
        63: "Moderate rain 🌧️",
        65: "Heavy rain 🌧️",
        71: "Slight snow 🌨️",
        73: "Moderate snow ❄️",
        75: "Heavy snow ❄️",
        77: "Snow grains 🌨️",
        80: "Slight showers 🌦️",
        81: "Moderate showers 🌧️",
        82: "Violent showers ⛈️",
        85: "Snow showers 🌨️",
        86: "Heavy snow showers ❄️",
        95: "Thunderstorm ⛈️",
        96: "Thunderstorm with hail ⛈️",
        99: "Thunderstorm with heavy hail ⛈️",
    }
    return mapping.get(code, "Unknown 🌡️")


def _geocode_city(city: str) -> tuple[float, float] | None:
    """Geocode using Open-Meteo's geocoding API."""
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        pass
    return None


def _fallback_weather(city: str, start_date_str: str, days: int) -> list:
    """Generate reasonable synthetic weather when the API fails."""
    cold_cities = {"manali", "shimla", "ladakh", "spiti", "auli", "mussoorie", "nainital", "darjeeling", "sikkim"}
    hot_cities = {"goa", "kerala", "andaman", "pondicherry", "chennai", "kovalam"}
    city_lower = city.lower()

    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        start = datetime.today()

    month = start.month
    if month in (12, 1, 2):
        base_max, base_min, rain = 22, 10, 10
    elif month in (3, 4, 5):
        base_max, base_min, rain = 35, 22, 5
    elif month in (6, 7, 8, 9):
        base_max, base_min, rain = 30, 22, 70
    else:
        base_max, base_min, rain = 28, 16, 20

    if any(c in city_lower for c in cold_cities):
        base_max -= 12
        base_min -= 12
    elif any(c in city_lower for c in hot_cities):
        base_max += 4

    result = []
    for i in range(days):
        day_date = start + timedelta(days=i)
        result.append({
            "date": day_date.strftime("%Y-%m-%d"),
            "temp_max": base_max + (i % 3),
            "temp_min": base_min + (i % 2),
            "rain_chance": rain,
            "condition": "Mainly clear 🌤️" if rain < 40 else "Partly cloudy ⛅",
        })
    return result


def get_weather_forecast(city: str, start_date: str, end_date: str) -> list:
    """
    Phase 1 upgrade: fetch weather for the *actual* travel date range
    using Open-Meteo's start_date / end_date parameters.
    Falls back to synthetic data if geocoding or API call fails.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        start_dt = datetime.today()
        end_dt = start_dt + timedelta(days=3)

    days = (end_dt - start_dt).days + 1

    coords = _geocode_city(city)
    if not coords:
        return _fallback_weather(city, start_date, days)

    lat, lon = coords
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "start_date": start_date,
                "end_date": end_date,
                "timezone": "Asia/Kolkata",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain_chances = daily.get("precipitation_probability_max", [])
        codes = daily.get("weathercode", [])

        result = []
        for i, date in enumerate(dates):
            result.append({
                "date": date,
                "temp_max": round(max_temps[i]) if i < len(max_temps) else 30,
                "temp_min": round(min_temps[i]) if i < len(min_temps) else 20,
                "rain_chance": int(rain_chances[i]) if i < len(rain_chances) else 20,
                "condition": _weather_code_to_text(int(codes[i])) if i < len(codes) else "Mainly clear 🌤️",
            })
        return result if result else _fallback_weather(city, start_date, days)

    except Exception:
        return _fallback_weather(city, start_date, days)


def get_packing_suggestions(weather: list, preferences: list) -> list:
    """Generate categorized packing list based on weather + preferences."""
    if not weather:
        return []

    avg_temp = sum(d.get("temp_max", 30) for d in weather) / len(weather)
    avg_rain = sum(d.get("rain_chance", 0) for d in weather) / len(weather)
    prefs_lower = [p.lower() for p in preferences]

    suggestions = []

    # ── Essentials (always) ──
    suggestions.append({
        "category": "🎒 Essentials",
        "items": ["Phone charger", "Power bank", "ID / Passport", "Cash & cards", "Medicines", "Hand sanitizer"],
    })

    # ── Clothing (weather-based) ──
    if avg_temp > 35:
        clothing = ["Light cotton clothes", "Sunscreen SPF50+", "Sunglasses", "Hat/cap", "Sandals"]
    elif avg_temp > 25:
        clothing = ["T-shirts & shorts", "Light jacket for evenings", "Comfortable sneakers", "Sunglasses"]
    elif avg_temp > 15:
        clothing = ["Layers (t-shirt + hoodie)", "Jeans / trousers", "Light jacket", "Closed shoes"]
    else:
        clothing = ["Thermals / base layer", "Heavy sweater / fleece", "Winter jacket", "Gloves & woollen cap", "Warm socks", "Boots"]

    if avg_rain > 40:
        clothing += ["Rain jacket / waterproof", "Compact umbrella", "Waterproof bag cover"]

    suggestions.append({"category": "👕 Clothing", "items": clothing})

    # ── Adventure gear ──
    if any(p in prefs_lower for p in ["adventure", "trekking", "hiking"]):
        suggestions.append({
            "category": "🏔️ Adventure Gear",
            "items": ["Trekking shoes", "Trekking poles", "Headlamp + batteries", "First-aid kit", "Energy bars", "Water bottle"],
        })

    # ── Beach essentials ──
    if any(p in prefs_lower for p in ["beach", "swimming"]):
        suggestions.append({
            "category": "🏖️ Beach Essentials",
            "items": ["Swimwear", "Beach towel", "Waterproof sunscreen", "Flip-flops", "Snorkelling gear (optional)"],
        })

    # ── Food explorer ──
    if any(p in prefs_lower for p in ["food", "culinary"]):
        suggestions.append({
            "category": "🍜 Food Explorer",
            "items": ["Food diary / notes app", "Antacids", "Reusable tiffin box", "Food allergy card"],
        })

    # ── Cultural visits ──
    if any(p in prefs_lower for p in ["culture", "spiritual", "temple"]):
        suggestions.append({
            "category": "🛕 Cultural Visits",
            "items": ["Modest full-length clothing", "Scarf / dupatta", "Comfortable walking shoes", "Small torch (for caves/temples)"],
        })

    # ── Tech (always) ──
    suggestions.append({
        "category": "📱 Tech",
        "items": ["Camera & memory cards", "Universal adapter", "Earphones / earbuds", "Offline maps downloaded"],
    })

    return suggestions
