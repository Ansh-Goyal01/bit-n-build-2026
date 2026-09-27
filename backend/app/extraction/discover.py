"""Enumerate Central-level schemes on myScheme for the scaling pipeline.

Pages the portal's public search API with the level=Central facet and — because
slug search is known to surface state variants of centrally-sponsored schemes
(see NOTES 2026-07-10) — re-checks `level == "Central"` on every item. The
result is archived to data/raw/central-schemes-index.json with a fetch date so
scheme selection is reproducible.
"""

import json
import time
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel

from app.config import settings
from app.ingestion.fetch import SEARCH_URL, _get

PAGE_SIZE = 50
REQUEST_DELAY_SECONDS = 0.8
INDEX_PATH_NAME = "central-schemes-index.json"


class DiscoveredScheme(BaseModel):
    slug: str
    name: str
    short_title: str = ""
    categories: list[str] = []
    ministry: str = ""
    brief: str = ""
    close_date: str = ""
    tags: list[str] = []


def discover_central_schemes(client: httpx.Client) -> list[DiscoveredScheme]:
    facet = json.dumps([{"identifier": "level", "value": "Central"}])
    found: dict[str, DiscoveredScheme] = {}
    start = 0
    while True:
        result = _get(
            client,
            SEARCH_URL,
            {
                "lang": "en",
                "q": facet,
                "keyword": "",
                "sort": "",
                "from": str(start),
                "size": str(PAGE_SIZE),
            },
        )
        hits = result.get("data", {}).get("hits", {})
        items = hits.get("items", [])
        if not items:
            break
        for item in items:
            fields = item.get("fields", {})
            # Defensive re-check: the state-variant trap.
            if fields.get("level") != "Central" or not fields.get("slug"):
                continue
            scheme = DiscoveredScheme(
                slug=fields["slug"],
                name=fields.get("schemeName", ""),
                short_title=fields.get("schemeShortTitle", "") or "",
                categories=fields.get("schemeCategory", []) or [],
                ministry=fields.get("nodalMinistryName", "") or "",
                brief=fields.get("briefDescription", "") or "",
                close_date=fields.get("schemeCloseDate", "") or "",
                tags=fields.get("tags", []) or [],
            )
            found.setdefault(scheme.slug, scheme)
        total = hits.get("page", {}).get("total", 0)
        start += PAGE_SIZE
        if start >= total:
            break
        time.sleep(REQUEST_DELAY_SECONDS)
    return list(found.values())


def run_discovery() -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        schemes = discover_central_schemes(client)
    out = settings.raw_dir / INDEX_PATH_NAME
    out.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(UTC).strftime("%Y-%m-%d"),
                "count": len(schemes),
                "schemes": [s.model_dump() for s in schemes],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"{len(schemes)} central schemes -> {out}")


if __name__ == "__main__":
    run_discovery()
