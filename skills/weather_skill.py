"""
MakiAI — Weather & Environmental Forecast Skill
Provides real-time local weather reports and forecasts for the user's current
location or any specified global city/region.

Zero API keys required (powered by Open-Meteo & wttr.in high-precision APIs with auto-IP geolocation).
"""

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional, Tuple

from skills.base_skill import BaseSkill


class WeatherSkill(BaseSkill):
    SKILL_ID = "weather"
    NAME = "Weather & Environmental Forecast"
    DESCRIPTION = "Provides real-time local and global weather forecasts, temperature, precipitation chance, humidity, and condition summaries."
    REQUIRED_FILES = []
    TRIGGERS = [
        "weather", "temperature", "forecast", "is it going to rain", "rain today",
        "raining", "climate", "panahon", "ulan", "mainit ba", "malamig ba",
        "how cold is it", "how hot is it", "humidity outside", "degrees outside"
    ]

    # In-memory caches to ensure sub-millisecond repeat queries
    _geo_cache: Dict[str, Tuple[float, float, str, str]] = {}
    _weather_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _local_ip_geo: Optional[Tuple[float, float, str, str]] = None
    _local_ip_geo_time: float = 0.0

    WMO_CODES = {
        0: ("Clear Sky", "☀️", "clear skies"),
        1: ("Mainly Clear", "🌤️", "mainly clear"),
        2: ("Partly Cloudy", "⛅", "partly cloudy"),
        3: ("Overcast", "☁️", "overcast skies"),
        45: ("Foggy", "🌫️", "foggy conditions"),
        48: ("Depositing Rime Fog", "🌫️", "rime fog"),
        51: ("Light Drizzle", "🌦️", "light drizzle"),
        53: ("Moderate Drizzle", "🌦️", "moderate drizzle"),
        55: ("Dense Drizzle", "🌧️", "dense drizzle"),
        61: ("Slight Rain", "🌧️", "slight rain"),
        63: ("Moderate Rain", "🌧️", "moderate rain"),
        65: ("Heavy Rain", "🌧️", "heavy rain"),
        66: ("Freezing Rain", "🌧️❄️", "freezing rain"),
        67: ("Heavy Freezing Rain", "🌧️❄️", "heavy freezing rain"),
        71: ("Slight Snow", "🌨️", "slight snowfall"),
        73: ("Moderate Snow", "🌨️", "moderate snowfall"),
        75: ("Heavy Snow", "❄️", "heavy snowfall"),
        77: ("Snow Grains", "❄️", "snow grains"),
        80: ("Slight Rain Showers", "🌦️", "slight rain showers"),
        81: ("Moderate Rain Showers", "🌧️", "moderate rain showers"),
        82: ("Violent Rain Showers", "⛈️", "heavy rain showers"),
        85: ("Slight Snow Showers", "🌨️", "slight snow showers"),
        86: ("Heavy Snow Showers", "❄️", "heavy snow showers"),
        95: ("Thunderstorm", "⛈️", "a thunderstorm"),
        96: ("Thunderstorm with Slight Hail", "⛈️", "a thunderstorm with slight hail"),
        99: ("Thunderstorm with Heavy Hail", "⛈️⚡", "a severe thunderstorm with heavy hail"),
    }

    def __init__(self, gemini_service=None, context_builder=None, kb_reader=None, kb_writer=None, **kwargs):
        super().__init__(
            gemini_service=gemini_service,
            context_builder=context_builder,
            kb_reader=kb_reader,
            kb_writer=kb_writer,
            **kwargs
        )
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Attach UI bridge for sending structured weather activity logs."""
        self.ui_bridge = ui_bridge

    def can_handle(self, text: str) -> bool:
        """Determine if user input is asking about weather, rain, temperature, or forecast."""
        clean = (text or "").lower()

        weather_keywords = [
            "weather", "temperature", "forecast", "is it raining", "will it rain",
            "is it going to rain", "rain today", "climate", "panahon", "ulan",
            "mainit ba", "malamig ba", "degrees outside", "how hot is it",
            "how cold is it", "humidity", "rain tomorrow"
        ]

        if any(kw in clean for kw in weather_keywords):
            return True

        # Check regex patterns like "weather in Tokyo", "what's the weather like"
        if re.search(r"\b(weather|temperature|temp|forecast|rain)\b", clean):
            return True

        return False

    # ─── Geolocation & Weather Data Engine ────────────────────────────────────

    def _get_local_location(self) -> Tuple[float, float, str, str]:
        """Detect user location, prioritizing explicit user settings over IP geolocation."""
        import os
        from services.settings.settings_service import SettingsService

        configured = os.environ.get("USER_LOCATION", "").strip()
        if not configured:
            try:
                configured = SettingsService().get_user_location()
            except Exception:
                pass

        if configured:
            geo = self._geocode_city(configured)
            if geo:
                return geo

        return self._get_local_ip_location()

    def _get_local_ip_location(self) -> Tuple[float, float, str, str]:
        """Detect the user's current city and coordinates using IP geolocation."""
        now = time.time()
        if WeatherSkill._local_ip_geo and (now - WeatherSkill._local_ip_geo_time < 3600):
            return WeatherSkill._local_ip_geo

        # Primary: ip-api.com
        try:
            req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "MakiAI/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    lat = float(data.get("lat", 0.0))
                    lon = float(data.get("lon", 0.0))
                    city = data.get("city", "Local Area")
                    country = data.get("country", "")
                    res = (lat, lon, city, country)
                    WeatherSkill._local_ip_geo = res
                    WeatherSkill._local_ip_geo_time = now
                    return res
        except Exception as e:
            print(f"[WeatherSkill] ip-api lookup note: {e}")

        # Secondary: ipapi.co
        try:
            req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "MakiAI/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                lat = float(data.get("latitude", 0.0))
                lon = float(data.get("longitude", 0.0))
                city = data.get("city", "Local Area")
                country = data.get("country_name", "")
                res = (lat, lon, city, country)
                WeatherSkill._local_ip_geo = res
                WeatherSkill._local_ip_geo_time = now
                return res
        except Exception as e:
            print(f"[WeatherSkill] ipapi.co fallback note: {e}")

        # Default fallback (Philippine coordinate baseline)
        return (8.4817, 124.6467, "Cagayan de Oro", "Philippines")

    def _geocode_city(self, city_query: str) -> Optional[Tuple[float, float, str, str]]:
        """Geocode any global city name to latitude and longitude using Open-Meteo & Nominatim APIs."""
        city_clean = city_query.strip().title()
        cache_key = city_clean.lower()

        if cache_key in WeatherSkill._geo_cache:
            return WeatherSkill._geo_cache[cache_key]

        # 1. Primary: Open-Meteo Geocoding API
        try:
            encoded = urllib.parse.quote(city_clean)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "MakiAI/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results")
                if results and len(results) > 0:
                    best = results[0]
                    lat = float(best.get("latitude", 0.0))
                    lon = float(best.get("longitude", 0.0))
                    name = best.get("name", city_clean)
                    country = best.get("country", "")
                    res = (lat, lon, name, country)
                    WeatherSkill._geo_cache[cache_key] = res
                    return res
        except Exception as e:
            print(f"[WeatherSkill] Open-Meteo Geocoding note for '{city_query}': {e}")

        # 2. Secondary: Nominatim (OpenStreetMap)
        try:
            encoded = urllib.parse.quote(city_clean)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "MakiAI-Desktop/1.0 (denjikun1008@gmail.com)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    best = data[0]
                    lat = float(best.get("lat", 0.0))
                    lon = float(best.get("lon", 0.0))
                    name = best.get("display_name", city_clean).split(",")[0]
                    country = best.get("display_name", "").split(",")[-1].strip()
                    res = (lat, lon, name, country)
                    WeatherSkill._geo_cache[cache_key] = res
                    return res
        except Exception as err:
            print(f"[WeatherSkill] Nominatim Geocoding fallback note for '{city_query}': {err}")

        return None

    def fetch_weather_data(self, lat: float, lon: float, location_name: str, country: str = "") -> Optional[Dict[str, Any]]:
        """Fetch real-time weather and forecast data from Open-Meteo."""
        cache_key = f"{lat:.3f}_{lon:.3f}"
        now = time.time()

        if cache_key in WeatherSkill._weather_cache:
            cached_time, cached_data = WeatherSkill._weather_cache[cache_key]
            if now - cached_time < 600:  # 10 minutes cache
                return cached_data

        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                f"&timezone=auto"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "MakiAI/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                current = data.get("current", {})
                daily = data.get("daily", {})

                w_code = current.get("weather_code", 0)
                cond_name, cond_emoji, cond_phrase = self.WMO_CODES.get(w_code, ("Fair", "☀️", "fair conditions"))

                temp_c = round(float(current.get("temperature_2m", 0.0)), 1)
                temp_f = round(temp_c * 9 / 5 + 32, 1)
                feels_like_c = round(float(current.get("apparent_temperature", temp_c)), 1)
                humidity = int(current.get("relative_humidity_2m", 0))
                wind_kmh = round(float(current.get("wind_speed_10m", 0.0)), 1)
                precip_mm = round(float(current.get("precipitation", 0.0)), 1)

                # Daily forecast values
                max_temps = daily.get("temperature_2m_max", [temp_c])
                min_temps = daily.get("temperature_2m_min", [temp_c])
                precip_probs = daily.get("precipitation_probability_max", [0])

                high_c = round(float(max_temps[0]), 1) if max_temps else temp_c
                low_c = round(float(min_temps[0]), 1) if min_temps else temp_c
                rain_prob = int(precip_probs[0]) if precip_probs else (100 if precip_mm > 0.5 else 10)

                result = {
                    "location": location_name,
                    "country": country,
                    "temperature_c": temp_c,
                    "temperature_f": temp_f,
                    "feels_like_c": feels_like_c,
                    "condition": cond_name,
                    "condition_phrase": cond_phrase,
                    "emoji": cond_emoji,
                    "humidity": humidity,
                    "wind_kmh": wind_kmh,
                    "precipitation_mm": precip_mm,
                    "high_c": high_c,
                    "low_c": low_c,
                    "rain_probability": rain_prob,
                    "weather_code": w_code,
                }

                WeatherSkill._weather_cache[cache_key] = (now, result)
                return result

        except Exception as e:
            print(f"[WeatherSkill] Open-Meteo fetch error: {e}")

        # Fallback to wttr.in JSON API
        try:
            city_enc = urllib.parse.quote(location_name)
            wttr_url = f"https://wttr.in/{city_enc}?format=j1"
            req = urllib.request.Request(wttr_url, headers={"User-Agent": "MakiAI/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                curr = data.get("current_condition", [{}])[0]
                temp_c = float(curr.get("temp_C", 25.0))
                feels_c = float(curr.get("FeelsLikeC", temp_c))
                humidity = int(curr.get("humidity", 60))
                desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")

                result = {
                    "location": location_name,
                    "country": country,
                    "temperature_c": temp_c,
                    "temperature_f": round(temp_c * 9 / 5 + 32, 1),
                    "feels_like_c": feels_c,
                    "condition": desc,
                    "condition_phrase": desc.lower(),
                    "emoji": "🌤️",
                    "humidity": humidity,
                    "wind_kmh": float(curr.get("windspeedKmph", 5.0)),
                    "precipitation_mm": float(curr.get("precipMM", 0.0)),
                    "high_c": temp_c + 2.0,
                    "low_c": temp_c - 2.0,
                    "rain_probability": 30 if "rain" in desc.lower() else 10,
                    "weather_code": 0,
                }
                WeatherSkill._weather_cache[cache_key] = (now, result)
                return result
        except Exception as err:
            print(f"[WeatherSkill] wttr.in fallback error: {err}")

        return None

    def _extract_target_location(self, text: str) -> Optional[str]:
        """Extract city or location name from natural speech/text."""
        clean = text.strip()

        # Check explicit location prepositions: "in Tokyo", "for London", "sa Cebu", "at Seattle"
        match = re.search(r"\b(?:in|for|at|sa)\s+([A-Za-z\s,\.\-]{2,35})", clean, re.IGNORECASE)
        if match:
            raw_target = match.group(1).strip()
            # Strip trailing temporal adverbs and punctuation
            cleaned_target = re.sub(
                r"\b(today|tomorrow|tonight|now|this morning|this afternoon|this evening|this week|ngayon|bukas|outside|here|dito|right now|please|sir|maki)\b.*$",
                "",
                raw_target,
                flags=re.IGNORECASE
            ).strip()
            cleaned_target = cleaned_target.rstrip("?.!,:; ")

            # Filter generic stop words
            stopwords = {
                "the", "my", "our", "a", "an", "this", "that", "these", "those",
                "what", "how", "current", "local", "area", "labas", "here", "morning",
                "afternoon", "evening", "night", "hour", "day", "week", "month", "details",
                "general", "advance", "case"
            }
            if cleaned_target and cleaned_target.lower() not in stopwords and len(cleaned_target) >= 2:
                return cleaned_target

        # Check front city queries: "Tokyo weather", "Paris forecast", "London temperature"
        match_front = re.match(r"^([A-Za-z\s]{2,25})\s+(?:weather|temperature|forecast|temp)\b", clean, re.IGNORECASE)
        if match_front:
            city_candidate = match_front.group(1).strip()
            # If the front contains question words, it is a question about local weather, not a city name
            question_starters = {
                "what", "whats", "what is", "what's", "what is the", "what's the",
                "how", "hows", "how is", "how's", "how is the", "how's the",
                "tell", "tell me", "tell me the", "give", "give me", "give me the",
                "can you", "can you tell me", "can you check", "check", "check the",
                "current", "local", "live", "todays", "today's", "today", "the",
                "ano", "ano ang", "ano ba", "kamusta", "kamusta ang", "paki check", "pakisabi"
            }
            if city_candidate.lower() not in question_starters and not any(city_candidate.lower().startswith(q) for q in ["what", "how", "tell", "give", "can you", "check", "ano", "kamusta", "paki"]):
                return city_candidate

        return None

    def get_weather_summary(self, city_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Public helper to get weather data for internal use by GoodMorningSkill or Routines."""
        if city_name:
            geo = self._geocode_city(city_name)
            if geo:
                lat, lon, name, country = geo
                return self.fetch_weather_data(lat, lon, name, country)

        lat, lon, name, country = self._get_local_location()
        return self.fetch_weather_data(lat, lon, name, country)

    # ─── Main Execution ───────────────────────────────────────────────────────

    def execute(self, text: str) -> str:
        """Process weather query, fetch real-time atmospheric data, and speak response."""
        clean = (text or "").strip()
        lowered = clean.lower()

        # Check if user is configuring their location
        set_loc_match = re.search(
            r"\b(?:set|change|update|save|remember)?\s*(?:my\s+)?(?:location|city|home\s+city)\s+(?:to|is|as|sa)\s+([A-Za-z\s,\.\-]{2,35})",
            clean,
            re.IGNORECASE
        )
        if set_loc_match:
            new_city = set_loc_match.group(1).strip().rstrip(".!?,")
            geo = self._geocode_city(new_city)
            if geo:
                lat, lon, loc_name, country = geo
                from services.settings.settings_service import SettingsService
                try:
                    SettingsService().set_user_location(loc_name)
                except Exception as e:
                    print(f"[WeatherSkill] Error setting location: {e}")

                if self.ui_bridge and hasattr(self.ui_bridge, "add_activity"):
                    self.ui_bridge.add_activity("system", f"Location set to {loc_name}, {country}.")

                return f"Location updated to {loc_name}, {country}, sir. I will now use this for all your local weather forecasts."

        target_city = self._extract_target_location(text)
        is_local = target_city is None

        if target_city:
            geo = self._geocode_city(target_city)
            if not geo:
                return f"I couldn't find atmospheric telemetry for '{target_city}', sir. Please check the city name and try again."
            lat, lon, loc_name, country = geo
        else:
            lat, lon, loc_name, country = self._get_local_location()

        w_data = self.fetch_weather_data(lat, lon, loc_name, country)
        if not w_data:
            return f"I am unable to retrieve the live weather telemetry for {loc_name} at this moment, sir. Please verify your internet connection."

        temp = w_data["temperature_c"]
        feels_like = w_data["feels_like_c"]
        cond = w_data["condition"]
        cond_phrase = w_data["condition_phrase"]
        humidity = w_data["humidity"]
        wind = w_data["wind_kmh"]
        rain_prob = w_data["rain_probability"]
        high = w_data["high_c"]
        low = w_data["low_c"]
        emoji = w_data["emoji"]

        # Check if user specifically asked about rain
        lowered = text.lower()
        asking_about_rain = any(k in lowered for k in ["rain", "ulan", "raining", "will it rain", "is it going to rain", "uulan"])

        if asking_about_rain:
            if rain_prob >= 60 or "rain" in cond.lower() or "drizzle" in cond.lower() or "thunderstorm" in cond.lower():
                spoken_response = (
                    f"Yes, sir. There is a high chance of precipitation in {loc_name} today at {rain_prob} percent, "
                    f"with current conditions showing {cond_phrase} and a temperature of {temp} degrees Celsius. "
                    f"I recommend keeping an umbrella nearby."
                )
            elif rain_prob >= 30:
                spoken_response = (
                    f"There is a moderate {rain_prob} percent chance of rain in {loc_name} today, sir. "
                    f"Current conditions are {cond_phrase} at {temp} degrees Celsius."
                )
            else:
                spoken_response = (
                    f"Rain is unlikely in {loc_name} today, sir. The precipitation probability is only {rain_prob} percent, "
                    f"with {cond_phrase} and a pleasant temperature of {temp} degrees Celsius."
                )
        else:
            # General comprehensive weather report
            loc_label = f"in {loc_name}" if not is_local else f"here in {loc_name}"
            spoken_response = (
                f"Currently {loc_label}, it is {temp} degrees Celsius with {cond_phrase}. "
                f"It feels like {feels_like} degrees with {humidity} percent humidity and winds at {wind} kilometers per hour. "
                f"Today's high is expected to reach {high} degrees with a {rain_prob} percent chance of rain."
            )

        # Post structured weather card to desktop UI activity panel
        if self.ui_bridge and hasattr(self.ui_bridge, "add_activity"):
            summary_card = (
                f"{emoji} **Weather Report — {loc_name}**\n"
                f"🌡️ **Temp:** {temp}°C (Feels like {feels_like}°C) | **High/Low:** {high}°C / {low}°C\n"
                f"☁️ **Condition:** {cond} | 💧 **Humidity:** {humidity}% | 🌧️ **Rain Chance:** {rain_prob}%\n"
                f"💨 **Wind:** {wind} km/h"
            )
            self.ui_bridge.add_activity("assistant", summary_card)

        return spoken_response
