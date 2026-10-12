import requests
import json
import urllib.parse
import time

# In-Memory 10-Minute Bounded Caches (LRU/FIFO Eviction max 100 items)
_WEATHER_CACHE = {}  # {loc_key: (timestamp, data)}
_KNOWLEDGE_CACHE = {} # {query_key: (timestamp, data)}
CACHE_TTL = 600  # 10 minutes
MAX_CACHE_ENTRIES = 100

def _cache_set(cache_dict: dict, key: str, value: tuple):
    if len(cache_dict) >= MAX_CACHE_ENTRIES:
        oldest_key = next(iter(cache_dict))
        cache_dict.pop(oldest_key, None)
    cache_dict[key] = value


def get_weather(location: str = "") -> dict:
    """
    Fetches atmospheric weather metrics with in-memory 10-minute caching
    and bounded timeouts to avoid rate limits or network stalls.
    """
    loc_clean = location.strip()
    cache_key = loc_clean.lower()
    now = time.time()

    # Check cache
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_data = _WEATHER_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    loc_encoded = urllib.parse.quote(loc_clean) if loc_clean else ""
    url = f"https://wttr.in/{loc_encoded}?format=j1"

    try:
        res = requests.get(url, timeout=3.0, headers={"User-Agent": "curl/8.0"})
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current_condition", [{}])[0]
            nearest = data.get("nearest_area", [{}])[0]

            temp_c = curr.get("temp_C", "N/A")
            feels_c = curr.get("FeelsLikeC", temp_c)
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
            humidity = curr.get("humidity", "N/A")
            wind_kmph = curr.get("windspeedKmph", "N/A")
            area_name = nearest.get("areaName", [{}])[0].get("value", loc_clean or "Local Area")

            summary = f"Atmospheric scan for {area_name}: {desc}, {temp_c}°C (feels like {feels_c}°C). Humidity at {humidity}%, winds at {wind_kmph} km/h, Sir."
            result = {
                "success": True,
                "location": area_name,
                "temp_c": temp_c,
                "feels_like_c": feels_c,
                "condition": desc,
                "humidity": humidity,
                "wind_kmph": wind_kmph,
                "summary": summary
            }
            _cache_set(_WEATHER_CACHE, cache_key, (now, result))
            return result
    except Exception:
        pass

    # Compact plain-text fallback
    try:
        compact_url = f"https://wttr.in/{loc_encoded}?format=%C+%t+%w+%h"
        res2 = requests.get(compact_url, timeout=2.5, headers={"User-Agent": "curl/8.0"})
        if res2.status_code == 200 and res2.text.strip():
            raw = res2.text.strip()
            result = {
                "success": True,
                "location": loc_clean or "Local Coordinates",
                "summary": f"Current weather reading: {raw}, Sir."
            }
            _cache_set(_WEATHER_CACHE, cache_key, (now, result))
            return result
    except Exception as e:
        return {"success": False, "error": str(e), "summary": "Atmospheric telemetry link unavailable, Sir."}

    return {"success": False, "summary": "Atmospheric telemetry link offline, Sir."}

def lookup_encyclopedia_abstract(query: str) -> dict:
    """
    Retrieves direct encyclopedic/Wikipedia abstracts using the DuckDuckGo Instant Answer API.
    Honestly scoped as an encyclopedia abstract lookup with 10-minute caching.
    """
    clean_q = query.strip()
    if not clean_q:
        return {"success": False, "answer": "", "summary": ""}

    cache_key = clean_q.lower()
    now = time.time()
    if cache_key in _KNOWLEDGE_CACHE:
        cached_time, cached_data = _KNOWLEDGE_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json&no_html=1&skip_disambig=1"
    try:
        res = requests.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            abstract = data.get("AbstractText", "").strip()
            heading = data.get("Heading", clean_q)
            source = data.get("AbstractSource", "Encyclopedia")

            if abstract:
                result = {
                    "success": True,
                    "heading": heading,
                    "source": source,
                    "summary": f"According to {source}: {abstract}"
                }
                _cache_set(_KNOWLEDGE_CACHE, cache_key, (now, result))
                return result

            # Check related topics
            related = data.get("RelatedTopics", [])
            if related and isinstance(related[0], dict) and related[0].get("Text"):
                first_rel = related[0].get("Text").strip()
                result = {
                    "success": True,
                    "heading": heading,
                    "source": source,
                    "summary": f"Knowledge base reports: {first_rel}"
                }
                _cache_set(_KNOWLEDGE_CACHE, cache_key, (now, result))
                return result
    except Exception as e:
        return {"success": False, "error": str(e), "summary": ""}

    result = {
        "success": False,
        "summary": f"No direct encyclopedia abstract found for '{clean_q}'. (Note: Searches direct factual summaries, not generic web pages), Sir."
    }
    _cache_set(_KNOWLEDGE_CACHE, cache_key, (now, result))
    return result

# Backward compatibility alias
search_instant_knowledge = lookup_encyclopedia_abstract
