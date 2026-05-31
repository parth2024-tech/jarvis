"""Layer 8 — Supabase Postgres connection + run tracking."""
from __future__ import annotations
import datetime as dt
import logging
from supabase import create_client, Client
from ..settings import env

log = logging.getLogger(__name__)

_client: Client | None = None


def db() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            env("SUPABASE_URL", required=True),
            env("SUPABASE_KEY", required=True),
        )
    return _client


def start_run() -> str:
    r = db().table("agent_runs").insert({"status": "running"}).execute()
    return r.data[0]["id"]


def finish_run(run_id: str, **fields):
    fields["finished_at"] = dt.datetime.utcnow().isoformat()
    db().table("agent_runs").update(fields).eq("id", run_id).execute()


def last_successful_run() -> dict | None:
    r = (
        db().table("agent_runs")
        .select("*")
        .eq("status", "success")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None


def fetch_all_deals() -> list[dict]:
    r = db().table("deals").select("*").execute()
    return r.data or []


def fetch_active_deals() -> list[dict]:
    r = db().table("deals").select("*").eq("is_active", True).order("value_usd", desc=True).execute()
    return r.data or []


def upsert_deal(deal: dict) -> dict:
    """Insert or update by (tool_name, plan_name)."""
    r = db().table("deals").upsert(deal, on_conflict="tool_name,plan_name").execute()
    return r.data[0] if r.data else deal


def update_deal(deal_id: str, fields: dict):
    db().table("deals").update(fields).eq("id", deal_id).execute()
