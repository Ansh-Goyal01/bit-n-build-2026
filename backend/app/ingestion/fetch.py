"""Fetch official scheme content from the myScheme public API.

myScheme (myscheme.gov.in) is the Government of India's national scheme
discovery portal. Its CORS-open public API is what the portal's own frontend
calls; the x-api-key below is the public client key shipped in that frontend
bundle — it is not a secret of this project. We fetch each scheme once,
archive the raw responses under data/raw/, and commit the cleaned corpus, so
this script only re-runs when the corpus needs a refresh.
"""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.ingestion.schemes import SCHEME_SOURCES, SchemeSource

API_BASE = "https://api.myscheme.gov.in/schemes/v6/public"
SEARCH_URL = "https://api.myscheme.gov.in/search/v6/schemes"
PAGE_URL_TEMPLATE = "https://www.myscheme.gov.in/schemes/{slug}"

# Public client key from the myscheme.gov.in frontend bundle (see module docstring).
PUBLIC_API_KEY = os.environ.get("MYSCHEME_API_KEY", "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "x-api-key": PUBLIC_API_KEY,
}

REQUEST_DELAY_SECONDS = 0.8


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _get(client: httpx.Client, url: str, params: dict[str, str]) -> dict[str, Any]:
    response = client.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_scheme_bundle(client: httpx.Client, source: SchemeSource) -> dict[str, Any]:
    """Fetch scheme content + required documents + FAQs for one scheme."""
    scheme = _get(client, f"{API_BASE}/schemes", {"slug": source.slug, "lang": "en"})
    if not scheme.get("data"):
        raise ValueError(f"slug {source.slug!r} not found on myscheme.gov.in")
    scheme_uid = scheme["data"]["_id"]
    time.sleep(REQUEST_DELAY_SECONDS)
    documents = _get(client, f"{API_BASE}/schemes/{scheme_uid}/documents", {"lang": "en"})
    time.sleep(REQUEST_DELAY_SECONDS)
    faqs = _get(client, f"{API_BASE}/schemes/{scheme_uid}/faqs", {"lang": "en"})
    return {
        "slug": source.slug,
        "short_name": source.short_name,
        "category": source.category,
        "page_url": PAGE_URL_TEMPLATE.format(slug=source.slug),
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "scheme": scheme,
        "documents": documents,
        "faqs": faqs,
    }


def suggest_slugs(client: httpx.Client, query: str) -> list[str]:
    """Best-effort slug lookup via the portal's search API, for fixing bad slugs."""
    try:
        result = _get(
            client,
            SEARCH_URL,
            {"lang": "en", "q": "[]", "keyword": query, "sort": "", "from": "0", "size": "8"},
        )
    except Exception:  # noqa: BLE001 — suggestions are best-effort only
        return []
    hits = result.get("data", {}).get("hits", {})
    items = hits.get("items", []) if isinstance(hits, dict) else []
    slugs: list[str] = []
    for item in items:
        fields = item.get("fields", item)
        slug = fields.get("slug")
        name = fields.get("schemeName", "")
        if slug:
            slugs.append(f"{slug}  ({name})")
    return slugs


def run_fetch() -> int:
    """Fetch all registered schemes into data/raw/. Returns count of failures."""
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with httpx.Client() as client:
        for source in SCHEME_SOURCES:
            out_path = settings.raw_dir / f"{source.slug}.json"
            if out_path.exists():
                print(f"SKIP  {source.slug}: already fetched")
                continue
            try:
                bundle = fetch_scheme_bundle(client, source)
            except Exception as exc:  # noqa: BLE001 — report and continue the batch
                failures += 1
                print(f"FAIL  {source.slug}: {type(exc).__name__}: {exc}")
                suggestions = suggest_slugs(client, source.name)
                if suggestions:
                    print(f"      slug suggestions: {suggestions}")
                continue
            out_path.write_text(
                json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            name = bundle["scheme"]["data"]["en"]["basicDetails"]["schemeName"]
            print(f"OK    {source.slug}: {name}")
            time.sleep(REQUEST_DELAY_SECONDS)
    return failures


if __name__ == "__main__":
    raise SystemExit(run_fetch())
