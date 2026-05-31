"""Discord announcement monitor — Layer 2F. Optional.

Requires DISCORD_BOT_TOKEN and the bot to be a member of the target servers.
Configure servers in config/sources.yaml under `discord_servers`.
"""
from __future__ import annotations
import logging
import datetime as dt
import requests
from ..settings import env, SOURCES
from ..types import RawChunk

log = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


def fetch_discord() -> list[RawChunk]:
    token = env("DISCORD_BOT_TOKEN")
    servers = SOURCES.get("discord_servers") or []
    if not token or not servers:
        log.info("Discord monitor disabled (no token or no servers configured)")
        return []

    headers = {"Authorization": f"Bot {token}"}
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=24)
    out: list[RawChunk] = []

    for server in servers:
        for channel_id in server.get("channel_ids", []):
            try:
                r = requests.get(
                    f"{DISCORD_API}/channels/{channel_id}/messages",
                    headers=headers,
                    params={"limit": 50},
                    timeout=20,
                )
                if r.status_code != 200:
                    log.warning("Discord channel %s -> %s", channel_id, r.status_code)
                    continue
                for msg in r.json():
                    ts = msg.get("timestamp", "")
                    try:
                        msg_dt = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                        if msg_dt < cutoff:
                            continue
                    except Exception:
                        pass
                    content = msg.get("content", "")
                    if not content:
                        continue
                    out.append(RawChunk(
                        source_url=f"https://discord.com/channels/{server.get('guild_id')}/{channel_id}/{msg['id']}",
                        source_type="community",
                        text=content[:4000],
                        meta={"discord_server": server.get("name"), "channel": channel_id},
                    ))
            except Exception as e:
                log.warning("Discord fetch failed: %s", e)
    log.info("Discord chunks: %d", len(out))
    return out
