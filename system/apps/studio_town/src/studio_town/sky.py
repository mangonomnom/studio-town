"""Where you are, what the weather is doing, and whether it's night: the town's sky.

Location comes from what the foodie map already learned from your browser (a city you set
here wins over it). Weather is from Open-Meteo (free, no key), cached for 15 minutes; the
raw responses are kept in DATA_DIR/sky/ so the card can always be traced back to its source.
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

FOODIE_LOCATION = Path("data/.apps/foodie-map/location.json")
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
PLACE_URL = "https://nominatim.openstreetmap.org/reverse"
WEATHER_TTL = 15 * 60
UA = "studio-town/1.0 (personal workspace app)"

# WMO weather codes -> (words, icon)
CODES = [((0,), "clear", "sun"), ((1, 2), "a few clouds", "partly"), ((3,), "cloudy", "cloud"), ((45, 48), "foggy", "fog"),
         ((51, 53, 55, 56, 57), "drizzly", "rain"), ((61, 63, 65, 66, 67, 80, 81, 82), "rainy", "rain"),
         ((71, 73, 75, 77, 85, 86), "snowy", "snow"), ((95, 96, 99), "stormy", "storm")]


def _get(url: str, params: dict) -> dict:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _read(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


class Sky:
    def __init__(self, data_dir: Path, timezone_name: str):
        self.dir = data_dir / "sky"
        self.tz = timezone_name

    def location(self) -> dict | None:
        chosen = _read(self.dir / "location.json")
        if chosen:
            return chosen
        found = _read(FOODIE_LOCATION)
        if found and "lat" in found:
            return {"lat": found["lat"], "lng": found["lng"], "source": "foodie map"}
        return None

    def place_name(self, loc: dict) -> str:
        cache = _read(self.dir / "place.json") or {}
        key = f"{loc['lat']:.2f},{loc['lng']:.2f}"
        if cache.get("key") == key:
            return cache["name"]
        try:
            raw = _get(PLACE_URL, {"lat": loc["lat"], "lon": loc["lng"], "format": "json", "zoom": 10})
            name = (raw.get("address") or {}).get("city") or raw.get("name") or ""
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / "place.json").write_text(json.dumps({"key": key, "name": name, "raw": raw}, indent=2))
            return name
        except Exception:
            log.warning("could not look up the place name", exc_info=True)
            return cache.get("name", "")

    def weather(self, loc: dict) -> dict | None:
        path = self.dir / "weather.json"
        cached = _read(path)
        if cached and time.time() - cached.get("fetched", 0) < WEATHER_TTL and cached.get("key") == [loc["lat"], loc["lng"]]:
            return cached["raw"]
        try:
            raw = _get(WEATHER_URL, {"latitude": loc["lat"], "longitude": loc["lng"], "timezone": self.tz,
                                     "current": "temperature_2m,weather_code,is_day", "daily": "sunrise,sunset",
                                     "temperature_unit": "fahrenheit", "forecast_days": 1})
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"fetched": time.time(), "key": [loc["lat"], loc["lng"]], "raw": raw}, indent=2))
            return raw
        except Exception:
            log.warning("could not fetch the weather", exc_info=True)
            return cached["raw"] if cached else None

    def now(self, local_now: datetime) -> dict:
        """Everything the page needs: date, time, weather words, icon, night or not, and when that flips."""
        state = {"night": not (7 <= local_now.hour < 19), "temp": None, "words": "", "icon": None, "place": "",
                 "sunrise": None, "sunset": None}
        loc = self.location()
        if not loc:
            return state
        state["place"] = self.place_name(loc)
        raw = self.weather(loc)
        if not raw:
            return state
        cur = raw.get("current") or {}
        daily = raw.get("daily") or {}
        code = cur.get("weather_code")
        for codes, words, icon in CODES:
            if code in codes:
                state["words"], state["icon"] = words, icon
        if cur.get("temperature_2m") is not None:
            state["temp"] = round(cur["temperature_2m"])
        sunrise = (daily.get("sunrise") or [None])[0]
        sunset = (daily.get("sunset") or [None])[0]
        state["sunrise"], state["sunset"] = sunrise, sunset
        if sunrise and sunset:
            stamp = local_now.strftime("%Y-%m-%dT%H:%M")
            state["night"] = not (sunrise <= stamp < sunset)
        return state
