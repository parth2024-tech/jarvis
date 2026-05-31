"""Layer 8 cont. — NEW / UPDATED / EXPIRED / RETURNED classification."""
from __future__ import annotations
import datetime as dt
import logging
import re
from . import database as db

log = logging.getLogger(__name__)
EXPIRY_MISSES = 3


def _parse_value_usd(deal: dict) -> float | None:
    v = deal.get("normal_monthly_cost_usd")
    if isinstance(v, (int, float)):
        return float(v)
    val_str = deal.get("discounted_price_or_value") or ""
    m = re.search(r"\$\s?([\d,]+(?:\.\d+)?)", val_str)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def _parse_expiry(deal: dict) -> str | None:
    e = deal.get("expiry_date_or_ongoing")
    if not e or e == "ongoing":
        return None
    try:
        dt.date.fromisoformat(e)
        return e
    except Exception:
        return None


def _detect_region(deal: dict) -> str:
    blob = " ".join(str(deal.get(k, "")) for k in ("eligibility_requirement", "raw_snippet")).lower()
    if any(s in blob for s in ("india", "indian", " in ", "inr", "₹")):
        return "IN"
    if any(s in blob for s in ("eu only", "european union", "eea")):
        return "EU"
    if "us only" in blob or "united states" in blob:
        return "US"
    return "global"


def _normalize(deal: dict) -> dict:
    return {
        "tool_name": (deal.get("tool_name") or "").strip(),
        "plan_name": (deal.get("premium_plan_name") or "default").strip(),
        "discount_type": deal.get("discount_type"),
        "value_usd": _parse_value_usd(deal),
        "discounted_value": deal.get("discounted_price_or_value"),
        "eligibility": deal.get("eligibility_requirement"),
        "claim_url": deal.get("claim_url"),
        "website_url": deal.get("website_url"),
        "expiry_date": _parse_expiry(deal),
        "verification_status": deal.get("verification_status"),
        "confidence_score": deal.get("confidence_score"),
        "source_type": deal.get("source_type"),
        "source_url": deal.get("source_url"),
        "raw_snippet": deal.get("raw_snippet"),
        "region": _detect_region(deal),
    }


def classify_and_persist(verified_deals: list[dict]) -> dict:
    """Returns {'new':[...], 'updated':[...], 'unchanged':[...], 'expired':[...]}."""
    existing = {(d["tool_name"], d.get("plan_name") or "default"): d for d in db.fetch_all_deals()}
    seen_keys: set = set()
    now = dt.datetime.utcnow().isoformat()
    buckets = {"new": [], "updated": [], "unchanged": [], "expired": [], "returned": []}

    for raw in verified_deals:
        if raw.get("verification_status") not in ("VERIFIED", "LIKELY_VALID"):
            continue
        norm = _normalize(raw)
        if not norm["tool_name"]:
            continue
        key = (norm["tool_name"], norm["plan_name"])
        seen_keys.add(key)
        prior = existing.get(key)

        if prior is None:
            payload = {**norm, "status": "NEW", "first_seen": now, "last_confirmed": now,
                       "last_updated": now, "consecutive_misses": 0, "is_active": True}
            saved = db.upsert_deal(payload)
            buckets["new"].append(saved)
            continue

        prev_value = prior.get("discounted_value")
        prev_expiry = prior.get("expiry_date")
        changed = (prev_value != norm["discounted_value"]) or (str(prev_expiry) != str(norm["expiry_date"]))
        was_inactive = not prior.get("is_active", True)

        update = {**norm, "last_confirmed": now, "consecutive_misses": 0, "is_active": True}
        if was_inactive:
            update["status"] = "RETURNED"
        elif changed:
            update["status"] = "UPDATED"
            update["prev_value"] = prev_value
            update["last_updated"] = now
        else:
            update["status"] = "UNCHANGED"

        db.update_deal(prior["id"], update)
        record = {**prior, **update}
        if was_inactive:
            buckets["returned"].append(record)
        elif changed:
            buckets["updated"].append(record)
        else:
            buckets["unchanged"].append(record)

    # Sweep for missing deals -> expire
    for key, prior in existing.items():
        if key in seen_keys or not prior.get("is_active", True):
            continue
        misses = (prior.get("consecutive_misses") or 0) + 1
        fields = {"consecutive_misses": misses}
        if misses >= EXPIRY_MISSES:
            fields["is_active"] = False
            fields["status"] = "EXPIRED"
            buckets["expired"].append({**prior, **fields})
        db.update_deal(prior["id"], fields)

    log.info("Classify: %s", {k: len(v) for k, v in buckets.items()})
    return buckets
