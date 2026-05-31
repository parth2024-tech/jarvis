"""Watchdog — runs in a separate workflow 1h after the main run.

If the last successful agent_runs.finished_at is older than 2 hours, alert via Telegram.
"""
from __future__ import annotations
import datetime as dt
import logging
import sys

from modules.storage import database as db
from modules.delivery import telegram_alert

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("watchdog")


def main() -> int:
    last = db.last_successful_run()
    if not last:
        telegram_alert.alert_failure("Watchdog: NO successful agent_runs ever recorded.")
        return 1
    finished = last.get("finished_at")
    try:
        ts = dt.datetime.fromisoformat(str(finished).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        telegram_alert.alert_failure(f"Watchdog: cannot parse last finished_at={finished}")
        return 1
    age = dt.datetime.utcnow() - ts
    log.info("Last successful run age: %s", age)
    if age > dt.timedelta(hours=2):
        telegram_alert.alert_failure(
            f"Watchdog: main agent has not completed successfully in {age}. "
            f"Last success at {finished}."
        )
        return 1
    log.info("Watchdog OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
