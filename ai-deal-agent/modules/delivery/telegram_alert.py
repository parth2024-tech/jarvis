"""Layer 10 — instant Telegram alert for high-value verified deals."""
from __future__ import annotations
import logging
import requests
from ..settings import env, HIGH_VALUE_THRESHOLD

log = logging.getLogger(__name__)


def _send(text: str):
    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("Telegram not configured; skipping")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=15,
        )
        if r.status_code != 200:
            log.warning("Telegram %s: %s", r.status_code, r.text)
    except Exception as e:
        log.exception("Telegram send failed: %s", e)


def alert_high_value(deal: dict):
    if (deal.get("value_usd") or 0) < HIGH_VALUE_THRESHOLD:
        return
    if deal.get("verification_status") != "VERIFIED":
        return
    msg = (
        f"🚨 <b>HIGH VALUE DEAL FOUND</b>\n\n"
        f"<b>Tool:</b> {deal.get('tool_name','')}\n"
        f"<b>Value:</b> {deal.get('discounted_value') or '$' + str(deal.get('value_usd'))}\n"
        f"<b>Eligibility:</b> {deal.get('eligibility') or '—'}\n"
        f"<b>Expires:</b> {deal.get('expiry_date') or 'ongoing'}\n"
        f"<b>Claim:</b> {deal.get('claim_url') or '—'}\n"
        f"<b>Source:</b> {deal.get('source_type','')} ({deal.get('source_url','')})\n"
        f"<b>Confidence:</b> {deal.get('confidence_score','?')}/10"
    )
    _send(msg)


def alert_failure(reason: str):
    _send(f"⚠️ <b>AI Deal Agent FAILED</b>\n\n{reason}")
