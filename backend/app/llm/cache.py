"""Disk cache for LLM calls — re-runs and eval batches never burn free-tier quota."""

import hashlib
import json
from typing import Any

from diskcache import Cache

from app.config import settings

_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        _cache = Cache(str(settings.cache_dir / "llm"))
    return _cache


def cache_key(provider: str, model: str, payload: dict[str, Any]) -> str:
    blob = json.dumps({"provider": provider, "model": model, **payload}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
