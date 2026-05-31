"""Newsletter + company blog RSS — Layer 2E."""
from __future__ import annotations
import logging
import feedparser
from ..settings import SOURCES
from ..types import RawChunk

log = logging.getLogger(__name__)

KEYWORDS = (
    "free", "credit", "credits", "grant", "discount", "student",
    "startup", "pro plan", "beta", "launch", "offer", "limited",
)


def fetch_rss() -> list[RawChunk]:
    out: list[RawChunk] = []
    for url in SOURCES.get("rss_feeds", []):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                text = f"{entry.get('title','')}\n{entry.get('summary','')}"
                low = text.lower()
                if not any(k in low for k in KEYWORDS):
                    continue
                out.append(RawChunk(
                    source_url=entry.get("link", url),
                    source_type="newsletter",
                    text=text[:5000],
                    meta={"feed": url, "published": entry.get("published", "")},
                ))
        except Exception as e:
            log.warning("RSS fail %s: %s", url, e)
    log.info("RSS items kept: %d", len(out))
    return out
