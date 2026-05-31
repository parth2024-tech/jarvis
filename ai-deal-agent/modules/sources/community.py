"""Reddit + HackerNews + ProductHunt + IndieHackers — Layer 2D."""
from __future__ import annotations
import logging
import requests
import feedparser
from ..settings import SOURCES
from ..types import RawChunk

log = logging.getLogger(__name__)

UA = {"User-Agent": "ai-deal-agent/1.0 (https://github.com/)"}


def _hackernews() -> list[RawChunk]:
    out: list[RawChunk] = []
    for q in SOURCES.get("hackernews_queries", []):
        try:
            r = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": q, "tags": "story", "numericFilters": "points>50"},
                timeout=20,
            )
            for hit in r.json().get("hits", []):
                text = f"{hit.get('title','')}\n{hit.get('url','')}\n{hit.get('story_text','') or ''}"
                out.append(RawChunk(
                    source_url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    source_type="community",
                    text=text[:5000],
                    meta={"hn_query": q, "points": hit.get("points")},
                ))
        except Exception as e:
            log.warning("HN failed: %s", e)
    return out


def _reddit() -> list[RawChunk]:
    out: list[RawChunk] = []
    for sub in SOURCES.get("reddit_subs", []):
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            feed = feedparser.parse(url, request_headers=UA)
            for entry in feed.entries[:15]:
                text = f"{entry.get('title','')}\n{entry.get('summary','')}"
                low = text.lower()
                if not any(k in low for k in ("free", "credit", "discount", "grant", "deal")):
                    continue
                out.append(RawChunk(
                    source_url=entry.get("link", url),
                    source_type="community",
                    text=text[:5000],
                    meta={"subreddit": sub},
                ))
        except Exception as e:
            log.warning("Reddit %s failed: %s", sub, e)
    return out


def _producthunt() -> list[RawChunk]:
    # ProductHunt RSS works without API token for daily launches
    out: list[RawChunk] = []
    for topic in SOURCES.get("producthunt_topics", []):
        url = f"https://www.producthunt.com/feed?category={topic}"
        try:
            feed = feedparser.parse(url, request_headers=UA)
            for entry in feed.entries[:20]:
                text = f"{entry.get('title','')}\n{entry.get('summary','')}"
                low = text.lower()
                if "free" not in low and "ai" not in low:
                    continue
                out.append(RawChunk(
                    source_url=entry.get("link", url),
                    source_type="community",
                    text=text[:3000],
                    meta={"producthunt_topic": topic},
                ))
        except Exception as e:
            log.warning("PH %s failed: %s", topic, e)
    return out


def fetch_community() -> list[RawChunk]:
    chunks = _hackernews() + _reddit() + _producthunt()
    log.info("Community chunks: %d", len(chunks))
    return chunks
