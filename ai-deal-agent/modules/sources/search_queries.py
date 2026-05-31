"""Brave Search (primary) + Tavily (secondary) — Layer 2C."""
from __future__ import annotations
import datetime as dt
import logging
import requests
from ..settings import env, QUERY_TEMPLATES
from ..types import RawChunk

log = logging.getLogger(__name__)


def _render_queries() -> list[str]:
    now = dt.datetime.utcnow()
    month = now.strftime("%B")
    year = str(now.year)
    return [q.format(month=month, year=year) for q in QUERY_TEMPLATES.get("queries", [])]


def _brave(query: str, key: str) -> list[RawChunk]:
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 10},
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        out = []
        for item in (r.json().get("web", {}).get("results") or []):
            text = f"{item.get('title','')}\n{item.get('description','')}\n{item.get('url','')}"
            out.append(RawChunk(
                source_url=item.get("url", ""),
                source_type="search",
                text=text,
                meta={"query": query, "engine": "brave"},
            ))
        return out
    except Exception as e:
        log.warning("Brave failed: %s", e)
        return []


def _tavily(query: str, key: str) -> list[RawChunk]:
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": 10, "search_depth": "basic"},
            timeout=25,
        )
        if r.status_code != 200:
            return []
        out = []
        for item in r.json().get("results", []):
            text = f"{item.get('title','')}\n{item.get('content','')}\n{item.get('url','')}"
            out.append(RawChunk(
                source_url=item.get("url", ""),
                source_type="search",
                text=text,
                meta={"query": query, "engine": "tavily"},
            ))
        return out
    except Exception as e:
        log.warning("Tavily failed: %s", e)
        return []


def run_searches() -> list[RawChunk]:
    brave_key = env("BRAVE_SEARCH_API_KEY")
    tavily_key = env("TAVILY_API_KEY")
    queries = _render_queries()
    chunks: list[RawChunk] = []
    for q in queries:
        if brave_key:
            chunks.extend(_brave(q, brave_key))
        if tavily_key:
            chunks.extend(_tavily(q, tavily_key))
    log.info("Search results: %d", len(chunks))
    return chunks
