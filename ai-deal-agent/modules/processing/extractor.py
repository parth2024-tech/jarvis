"""Layer 5 — LLM Pass 1: candidate extraction (Claude primary, OpenAI fallback)."""
from __future__ import annotations
import json
import logging
import re
from ..settings import env, load_prompt
from ..types import RawChunk

log = logging.getLogger(__name__)
SYSTEM = load_prompt("extraction_system.txt")

CLAUDE_MODEL = "claude-sonnet-4-5"
OPENAI_MODEL = "gpt-4o-mini"


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _claude(text: str) -> list[dict] | None:
    key = env("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        raw = resp.content[0].text
        return json.loads(_strip_fences(raw))
    except Exception as e:
        log.warning("Claude extraction failed: %s", e)
        return None


def _openai(text: str) -> list[dict] | None:
    key = env("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(_strip_fences(raw))
        # support {"deals":[...]} or bare list
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
            return []
        return data
    except Exception as e:
        log.warning("OpenAI extraction failed: %s", e)
        return None


def extract_from_chunk(chunk: RawChunk) -> list[dict]:
    payload = f"SOURCE_URL: {chunk.source_url}\nSOURCE_TYPE: {chunk.source_type}\n\n{chunk.text}"
    deals = _claude(payload)
    if deals is None:
        deals = _openai(payload)
    if not deals:
        return []
    # stamp source info if LLM omitted
    for d in deals:
        d.setdefault("source_url", chunk.source_url)
        d.setdefault("source_type", chunk.source_type)
    return deals


def extract_all(chunks: list[RawChunk], max_chunks: int | None = None) -> list[dict]:
    out: list[dict] = []
    pool = chunks[:max_chunks] if max_chunks else chunks
    for i, c in enumerate(pool):
        log.info("Extracting %d/%d from %s", i + 1, len(pool), c.source_url)
        out.extend(extract_from_chunk(c))
    log.info("Pass 1 candidates: %d", len(out))
    return out
