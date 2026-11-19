#!/usr/bin/env python3
"""Small stdlib HTTP helpers shared by the scrapers, incl. a Jina Reader fallback for sites
that block datacenter IPs (ITviec returns 403 to GitHub Actions)."""
import json
import time
import urllib.error
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.8",
}
JINA_DELAY_SECONDS = 3.5  # Jina free tier: ~20 requests/minute without an API key
_last_jina_call = [0.0]


def http_get(url, headers=None, data=None, timeout=25, retries=1):
    """GET (or POST when data is given). Returns (status, text); status 0 on network error."""
    body = json.dumps(data).encode() if data is not None else None
    hdrs = {**HEADERS, **(headers or {})}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs, data=body)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404) or attempt == retries:
                return e.code, ""
        except Exception:
            if attempt == retries:
                return 0, ""
        time.sleep(5)
    return 0, ""


def jina_get(url, as_html=False):
    """Fetch a page through Jina Reader (works when the site blocks GitHub Actions IPs)."""
    wait = JINA_DELAY_SECONDS - (time.time() - _last_jina_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_jina_call[0] = time.time()
    headers = {"X-Return-Format": "html"} if as_html else {}
    status, text = http_get("https://r.jina.ai/" + url, headers=headers, timeout=60)
    if status != 200 or "Attention Required! | Cloudflare" in text[:500]:
        return None
    return text
