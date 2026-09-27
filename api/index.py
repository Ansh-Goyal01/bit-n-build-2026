"""Vercel entrypoint for the Adhikaar API.

Vercel auto-detects `api/index.py` and serves the top-level `app`. Keeping this
shim at the repository root (rather than pointing Vercel at `backend/`) means
`data/corpus` and `data/chroma` land inside the function bundle, and
`app.config.REPO_ROOT` resolves exactly as it does locally.

Everything platform-specific lives here so the application itself stays
host-agnostic: on Vercel the filesystem is read-only apart from `/tmp`, but
Chroma opens its SQLite store read-write and the LLM disk cache needs somewhere
to write. Both are redirected below, before `app.config.settings` is
constructed at import time.
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

if os.environ.get("VERCEL"):
    # The committed index ships read-only in the bundle; Chroma needs to open it
    # read-write, so it is copied once per cold start into the writable tmpfs.
    bundled_index = ROOT / "data" / "chroma"
    writable_index = Path("/tmp/chroma")
    if bundled_index.is_dir() and not writable_index.exists():
        shutil.copytree(bundled_index, writable_index)

    os.environ.setdefault("CHROMA_DIR", str(writable_index))
    os.environ.setdefault("CACHE_DIR", "/tmp/cache")
    os.environ.setdefault("FEEDBACK_DIR", "/tmp/feedback")

    # The Dockerfile pre-downloads the embedder and reranker at image-build time.
    # There is no equivalent build step here, so they are fetched on first cold
    # start and must land somewhere writable.
    os.environ.setdefault("FASTEMBED_CACHE_PATH", "/tmp/fastembed")
    os.environ.setdefault("HF_HOME", "/tmp/huggingface")

from app.api.main import app  # noqa: E402  (import must follow the env setup above)

__all__ = ["app"]
