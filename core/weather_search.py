import requests
import json
import urllib.parse

def get_weather(location: str = "") -> dict:
    """
    Fetches real-time atmospheric weather metrics using wttr.in.
    """
    loc_encoded = urllib.parse.quote(location.strip()) if location else ""
    url = f"https://wttr.in/{loc_encoded}?format=j1"

    try:
        res = requests.get(url, timeout=4, headers={"User-Agent": "curl/8.0"})
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current_condition", [{}])[0]
            nearest = data.get("nearest_area", [{}])[0]
            
            temp_c = curr.get("temp_C", "N/A")
            feels_c = curr.get("FeelsLikeC", temp_c)
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
            humidity = curr.get("humidity", "N/A")
            wind_kmph = curr.get("windspeedKmph", "N/A")
            area_name = nearest.get("areaName", [{}])[0].get("value", location or "Local Area")

            summary = f"Atmospheric scan for {area_name}: {desc}, {temp_c}°C (feels like {feels_c}°C). Humidity at {humidity}%, winds at {wind_kmph} km/h, Sir."
            return {
                "success": True,
                "location": area_name,
                "temp_c": temp_c,
                "feels_like_c": feels_c,
                "condition": desc,
                "humidity": humidity,
                "wind_kmph": wind_kmph,
                "summary": summary
            }
    except Exception:
        pass

    # High-reliability fallback using compact plain-text format
    try:
        compact_url = f"https://wttr.in/{loc_encoded}?format=%C+%t+%w+%h"
        res2 = requests.get(compact_url, timeout=3, headers={"User-Agent": "curl/8.0"})
        if res2.status_code == 200 and res2.text.strip():
            raw = res2.text.strip()
            return {
                "success": True,
                "location": location or "Local Coordinates",
                "summary": f"Current weather reading: {raw}, Sir."
            }
    except Exception as e:
        return {"success": False, "error": str(e), "summary": "Atmospheric telemetry link unavailable, Sir."}

    return {"success": False, "summary": "Atmospheric telemetry link offline, Sir."}

def search_instant_knowledge(query: str) -> dict:
    """
    Retrieves concise factual summaries using the DuckDuckGo Instant Answer API.
    """
    clean_q = query.strip()
    if not clean_q:
        return {"success": False, "answer": ""}

    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json&no_html=1&skip_disambig=1"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            abstract = data.get("AbstractText", "")
            heading = data.get("Heading", clean_q)
            source = data.get("AbstractSource", "Knowledge Base")

            if abstract:
                return {
                    "success": True,
                    "heading": heading,
                    "source": source,
                    "summary": f"According to {source}: {abstract}"
                }
            
            # Check related topics if primary abstract is empty
            related = data.get("RelatedTopics", [])
            if related and isinstance(related[0], dict) and related[0].get("Text"):
                first_rel = related[0].get("Text")
                return {
                    "success": True,
                    "heading": heading,
                    "source": source,
                    "summary": f"Knowledge registry reports: {first_rel}"
                }
    except Exception as e:
        return {"success": False, "error": str(e), "summary": ""}

    return {"success": False, "summary": f"No direct encyclopedia abstract found for '{clean_q}', Sir."}
