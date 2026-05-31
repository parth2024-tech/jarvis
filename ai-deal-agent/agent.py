"""Main orchestrator — runs all 10 layers in sequence."""
from __future__ import annotations
import logging
import sys
import traceback

from modules.sources import official_pages, search_queries, rss_feeds, community, discord_monitor
from modules.processing import deduplicator, extractor, url_verifier, verifier
from modules.storage import database as db, change_detector
from modules.delivery import email_builder, sendgrid_sender, telegram_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("agent")


def main() -> int:
    run_id = None
    try:
        run_id = db.start_run()
        log.info("=== Run started: %s ===", run_id)

        # LAYER 2 — gather
        chunks = []
        chunks += official_pages.scrape_official_pages()
        chunks += official_pages.scrape_partner_perks()
        chunks += search_queries.run_searches()
        chunks += rss_feeds.fetch_rss()
        chunks += community.fetch_community()
        chunks += discord_monitor.fetch_discord()
        log.info("Total raw chunks: %d", len(chunks))

        # LAYER 4 — dedup
        chunks = deduplicator.deduplicate(chunks)

        # LAYER 5 — extract
        candidates = extractor.extract_all(chunks)

        # LAYER 6 — live URL check
        candidates = url_verifier.verify_all(candidates)

        # LAYER 7 — verify w/ LLM
        verified = verifier.verify_deals(candidates)

        # LAYER 8 — persist + classify
        buckets = change_detector.classify_and_persist(verified)

        # LAYER 10a — instant Telegram for high-value NEW deals
        for d in buckets["new"]:
            try:
                telegram_alert.alert_high_value(d)
            except Exception:
                log.exception("Telegram alert failed for %s", d.get("tool_name"))

        # LAYER 9 — email
        active = db.fetch_active_deals()
        watchlist = [c for c in verified if c.get("verification_status") == "UNVERIFIED"]
        subject = email_builder.build_subject(buckets)
        html = email_builder.build_html(buckets, active, watchlist)
        csv_active = email_builder.build_csv(active)
        csv_watch = email_builder.build_csv(watchlist)

        # LAYER 10b — email dispatch
        try:
            sendgrid_sender.send_email(subject, html, csv_active, csv_watch)
        except Exception as e:
            log.exception("Email dispatch failed")
            telegram_alert.alert_failure(f"Email send failed: {e}")

        db.finish_run(
            run_id,
            status="success",
            sources_scanned=len(chunks),
            candidates_extracted=len(candidates),
            deals_verified=len([d for d in verified if d.get("verification_status") in ("VERIFIED", "LIKELY_VALID")]),
        )
        log.info("=== Run finished ok ===")
        return 0

    except Exception as e:
        tb = traceback.format_exc()
        log.error("Run failed:\n%s", tb)
        if run_id:
            try:
                db.finish_run(run_id, status="failed", errors=[{"error": str(e), "traceback": tb[:2000]}])
            except Exception:
                pass
        try:
            telegram_alert.alert_failure(f"Agent crashed: {e}")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
