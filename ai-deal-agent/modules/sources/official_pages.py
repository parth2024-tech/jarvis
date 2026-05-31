"""Firecrawl-backed scraper for official program + partner pages (Layer 2A/2B + 3)."""
from __future__ import annotations
import logging
import time
import requests
from ..settings import env, SOURCES
from ..types import RawChunk

log = logging.getLogger(__name__)

FIRECRAWL_API = "https://api.firecrawl.dev/v2/scrape"


def _scrape_one(url: str, source_type: str) -> RawChunk | None:
    api_key = env("FIRECRAWL_API_KEY", required=True)
    try:
        r = requests.post(
            FIRECRAWL_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,
                "waitFor": 1500,
            },
            timeout=60,
        )
        if r.status_code != 200:
            log.warning("Firecrawl %s -> %s", url, r.status_code)
            return None
        data = r.json()
        md = (data.get("data") or {}).get("markdown") or data.get("markdown")
        if not md:
            return None
        return RawChunk(source_url=url, source_type=source_type, text=md[:20000])
    except Exception as e:
        log.exception("Firecrawl scrape failed for %s: %s", url, e)
        return None


def scrape_official_pages() -> list[RawChunk]:
    chunks: list[RawChunk] = []
    for url in SOURCES.get("official_pages", []):
        c = _scrape_one(url, "official")
        if c:
            chunks.append(c)
        time.sleep(1)
    log.info("Official pages scraped: %d", len(chunks))
    return chunks


def scrape_partner_perks() -> list[RawChunk]:
    chunks: list[RawChunk] = []
    for url in SOURCES.get("partner_perks", []):
        c = _scrape_one(url, "partner")
        if c:
            chunks.append(c)
        time.sleep(1)
    log.info("Partner pages scraped: %d", len(chunks))
    return chunks
