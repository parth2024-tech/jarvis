"""Layer 6 — Live URL HEAD verification."""
from __future__ import annotations
import logging
from urllib.parse import urlparse
import requests

log = logging.getLogger(__name__)
TIMEOUT = 5
UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-deal-agent/1.0)"}


def verify_url(claim_url: str | None, website_url: str | None) -> dict:
    if not claim_url:
        return {"status": "missing", "code": None, "redirects_to": None, "domain_match": False}
    try:
        r = requests.head(claim_url, allow_redirects=True, timeout=TIMEOUT, headers=UA)
        code = r.status_code
        final = r.url
        redirect = final if final != claim_url else None
    except requests.RequestException:
        try:
            r = requests.get(claim_url, allow_redirects=True, timeout=TIMEOUT, headers=UA, stream=True)
            code = r.status_code
            final = r.url
            redirect = final if final != claim_url else None
            r.close()
        except Exception:
            return {"status": "dead", "code": None, "redirects_to": None, "domain_match": False}

    domain_match = True
    if website_url:
        try:
            d_claim = urlparse(final).netloc.lower().lstrip("www.")
            d_site = urlparse(website_url).netloc.lower().lstrip("www.")
            # match if either fully contains the other root
            root_claim = ".".join(d_claim.split(".")[-2:])
            root_site = ".".join(d_site.split(".")[-2:])
            domain_match = root_claim == root_site
        except Exception:
            domain_match = False

    if code == 404:
        status = "dead"
    elif code in (301, 302, 303, 307, 308) or redirect:
        status = "redirect"
    elif 200 <= code < 300:
        status = "alive"
    else:
        status = f"http_{code}"

    return {"status": status, "code": code, "redirects_to": redirect, "domain_match": domain_match}


def verify_all(deals: list[dict]) -> list[dict]:
    for d in deals:
        d["url_check"] = verify_url(d.get("claim_url"), d.get("website_url"))
    alive = sum(1 for d in deals if d["url_check"]["status"] == "alive")
    log.info("URL verify: %d/%d alive", alive, len(deals))
    return deals
