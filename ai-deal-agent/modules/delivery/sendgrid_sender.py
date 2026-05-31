"""Layer 10 — SendGrid dispatch with CSV attachments."""
from __future__ import annotations
import base64
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from ..settings import env

log = logging.getLogger(__name__)


def send_email(subject: str, html: str, csv_active: str = "", csv_watchlist: str = ""):
    api_key = env("SENDGRID_API_KEY", required=True)
    to_addr = env("EMAIL_TO", required=True)
    from_addr = env("EMAIL_FROM", required=True)

    msg = Mail(from_email=from_addr, to_emails=to_addr, subject=subject, html_content=html)

    for content, name in [(csv_active, "deals_active.csv"), (csv_watchlist, "watchlist.csv")]:
        if not content:
            continue
        att = Attachment(
            FileContent(base64.b64encode(content.encode()).decode()),
            FileName(name),
            FileType("text/csv"),
            Disposition("attachment"),
        )
        msg.add_attachment(att)

    try:
        client = SendGridAPIClient(api_key)
        resp = client.send(msg)
        log.info("SendGrid status: %s", resp.status_code)
    except Exception as e:
        log.exception("SendGrid failed: %s", e)
        raise
