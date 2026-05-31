"""Layer 4 — SHA-256 + fuzzy dedup before LLM."""
from __future__ import annotations
import hashlib
import logging
from urllib.parse import urlparse
from rapidfuzz import fuzz
from ..types import RawChunk

log = logging.getLogger(__name__)


def _hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8", errors="ignore")).hexdigest()


def _fingerprint(chunk: RawChunk) -> str:
    domain = urlparse(chunk.source_url).netloc.lower()
    head = chunk.text.strip()[:200].lower()
    return f"{domain}::{head}"


def deduplicate(chunks: list[RawChunk], fuzzy_threshold: int = 92) -> list[RawChunk]:
    seen_hashes: set[str] = set()
    fingerprints: list[str] = []
    out: list[RawChunk] = []

    for c in chunks:
        if not c.text or len(c.text.strip()) < 40:
            continue
        h = _hash(c.text)
        if h in seen_hashes:
            continue
        fp = _fingerprint(c)
        if any(fuzz.ratio(fp, prev) >= fuzzy_threshold for prev in fingerprints):
            continue
        seen_hashes.add(h)
        fingerprints.append(fp)
        out.append(c)

    log.info("Dedup: %d -> %d chunks", len(chunks), len(out))
    return out
