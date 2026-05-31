"""Layer 9 — HTML email + CSV builder."""
from __future__ import annotations
import csv
import datetime as dt
import io
import logging
from html import escape
from ..settings import env, load_prompt, REGION

log = logging.getLogger(__name__)


def _expiring_soon(deals: list[dict], hours: int = 48) -> list[dict]:
    if not deals:
        return []
    cutoff = dt.date.today() + dt.timedelta(hours=hours) / dt.timedelta(days=1)
    cutoff_date = dt.date.today() + dt.timedelta(days=2)
    out = []
    for d in deals:
        e = d.get("expiry_date")
        if not e:
            continue
        try:
            ed = dt.date.fromisoformat(str(e))
            if dt.date.today() <= ed <= cutoff_date:
                out.append(d)
        except Exception:
            continue
    return out


def _row(d: dict) -> str:
    val = d.get("discounted_value") or (f"${d['value_usd']:.0f}" if d.get("value_usd") else "—")
    expiry = d.get("expiry_date") or "ongoing"
    return f"""
      <tr>
        <td style="padding:8px;border-bottom:1px solid #eee"><strong>{escape(d.get('tool_name') or '')}</strong></td>
        <td style="padding:8px;border-bottom:1px solid #eee">{escape(str(val))}</td>
        <td style="padding:8px;border-bottom:1px solid #eee">{escape(d.get('eligibility') or '—')}</td>
        <td style="padding:8px;border-bottom:1px solid #eee">{escape(str(expiry))}</td>
        <td style="padding:8px;border-bottom:1px solid #eee"><a href="{escape(d.get('claim_url') or '#')}">Claim</a></td>
      </tr>"""


def _table(title: str, deals: list[dict]) -> str:
    if not deals:
        return ""
    rows = "".join(_row(d) for d in sorted(deals, key=lambda x: -(x.get("value_usd") or 0)))
    return f"""
    <h2 style="font-size:18px;margin-top:24px">{escape(title)}</h2>
    <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">
      <thead>
        <tr style="background:#f5f5f5">
          <th style="padding:8px;text-align:left">Tool</th>
          <th style="padding:8px;text-align:left">Value</th>
          <th style="padding:8px;text-align:left">Eligibility</th>
          <th style="padding:8px;text-align:left">Expiry</th>
          <th style="padding:8px;text-align:left">Link</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def build_subject(buckets: dict) -> str:
    new_deals = buckets.get("new", [])
    top = max(new_deals, key=lambda x: (x.get("value_usd") or 0), default=None)
    expiring = _expiring_soon(new_deals + buckets.get("updated", []))
    prefix = "🚨 " if expiring else "🔓 "
    if top:
        val = top.get("discounted_value") or (f"${top['value_usd']:.0f}" if top.get("value_usd") else "")
        return f"{prefix}{val} {top.get('tool_name','')} + {len(new_deals)} new AI deals today"[:70]
    if buckets.get("updated"):
        return f"{prefix}{len(buckets['updated'])} AI deals updated today"[:70]
    return f"{prefix}Daily AI deals digest — {dt.date.today().isoformat()}"[:70]


def build_csv(deals: list[dict]) -> str:
    if not deals:
        return ""
    buf = io.StringIO()
    fields = ["tool_name", "plan_name", "discount_type", "value_usd", "discounted_value",
              "eligibility", "claim_url", "website_url", "expiry_date",
              "verification_status", "confidence_score", "source_type", "source_url",
              "region", "first_seen", "last_confirmed"]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for d in deals:
        w.writerow(d)
    return buf.getvalue()


def build_html(buckets: dict, active_deals: list[dict], watchlist: list[dict]) -> str:
    new_deals = sorted(buckets.get("new", []), key=lambda x: -(x.get("value_usd") or 0))
    updated = buckets.get("updated", [])
    expiring = _expiring_soon(active_deals)

    alert_bar = ""
    if expiring:
        alert_bar = f"""
        <div style="background:#dc2626;color:#fff;padding:14px;border-radius:8px;margin-bottom:20px;font-family:Arial,sans-serif">
          🚨 <strong>{len(expiring)} deal(s) expiring within 48 hours!</strong>
        </div>"""

    top_pick_html = ""
    if new_deals:
        top = new_deals[0]
        val = top.get("discounted_value") or (f"${top['value_usd']:.0f}" if top.get("value_usd") else "")
        top_pick_html = f"""
        <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);color:#fff;padding:24px;border-radius:12px;margin-bottom:24px;font-family:Arial,sans-serif">
          <div style="opacity:.8;font-size:12px;text-transform:uppercase;letter-spacing:1px">Today's #1 Pick</div>
          <div style="font-size:24px;font-weight:bold;margin-top:6px">{escape(top.get('tool_name',''))}</div>
          <div style="font-size:32px;font-weight:bold;margin-top:4px">{escape(str(val))}</div>
          <div style="margin-top:8px;opacity:.9">{escape(top.get('eligibility') or '')}</div>
          <a href="{escape(top.get('claim_url') or '#')}" style="display:inline-block;margin-top:14px;background:#fff;color:#0ea5e9;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold">Claim now →</a>
        </div>"""

    updated_html = ""
    if updated:
        diff_rows = "".join(
            f"<li><strong>{escape(d.get('tool_name',''))}</strong>: Was: <em>{escape(str(d.get('prev_value') or '—'))}</em> → Now: <strong>{escape(str(d.get('discounted_value') or '—'))}</strong></li>"
            for d in updated
        )
        updated_html = f"<h2 style='margin-top:24px'>Updated Deals</h2><ul>{diff_rows}</ul>"

    regional = [d for d in active_deals if d.get("region") in (REGION, "global")][:5]

    return f"""<!doctype html>
<html><body style="background:#fafafa;padding:20px;font-family:Arial,sans-serif;color:#111">
  <div style="max-width:720px;margin:0 auto;background:#fff;padding:28px;border-radius:12px">
    <h1 style="margin:0 0 4px 0">AI Deals Digest</h1>
    <div style="color:#666;font-size:13px;margin-bottom:20px">{dt.date.today().isoformat()}</div>
    {alert_bar}
    {top_pick_html}
    {_table('New This Morning', new_deals)}
    {updated_html}
    {_table(f'Regional Spotlight ({REGION})', regional)}
    {_table('Watchlist — Worth manual check', watchlist[:10])}
    {_table('Top 5 Evergreen', active_deals[:5])}
    <p style="color:#999;font-size:12px;margin-top:32px">Generated by your AI Deal Agent. Full active + watchlist CSVs attached.</p>
  </div>
</body></html>"""
