"""Layer 7 — LLM Pass 2: source-grounded confidence + status."""
from __future__ import annotations
import json
import logging
import re
from ..settings import env, load_prompt

log = logging.getLogger(__name__)
SYSTEM = load_prompt("verification_system.txt")

CLAUDE_MODEL = "claude-sonnet-4-5"
OPENAI_MODEL = "gpt-4o-mini"


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _build_user_msg(deal: dict) -> str:
    return json.dumps({
        "candidate": {k: v for k, v in deal.items() if k != "url_check"},
        "url_check": deal.get("url_check"),
    }, indent=2)


def _claude(msg: str) -> dict | None:
    key = env("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": msg}],
        )
        return json.loads(_strip_fences(resp.content[0].text))
    except Exception as e:
        log.warning("Claude verify failed: %s", e)
        return None


def _openai(msg: str) -> dict | None:
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
                {"role": "user", "content": msg},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(_strip_fences(resp.choices[0].message.content))
    except Exception as e:
        log.warning("OpenAI verify failed: %s", e)
        return None


def verify_deals(deals: list[dict]) -> list[dict]:
    for d in deals:
        msg = _build_user_msg(d)
        result = _claude(msg) or _openai(msg) or {
            "confidence_score": 3,
            "verification_status": "UNVERIFIED",
            "reasoning": "LLM unavailable",
        }
        d["confidence_score"] = result.get("confidence_score", 3)
        d["verification_status"] = result.get("verification_status", "UNVERIFIED")
        d["verification_reasoning"] = result.get("reasoning", "")
    counts = {}
    for d in deals:
        counts[d["verification_status"]] = counts.get(d["verification_status"], 0) + 1
    log.info("Pass 2 status counts: %s", counts)
    return deals
