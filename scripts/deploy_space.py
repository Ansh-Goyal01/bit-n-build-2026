"""Publish the repository to the Hugging Face Space.

A Docker Space is configured through YAML front matter at the top of its
README.md. GitHub renders that same front matter as a table above the title,
which we do not want on the public repo — so the Space header is generated
here and only ever exists on the branch that gets pushed to Hugging Face.
README.md on `main` stays clean.

Usage:  python -X utf8 scripts/deploy_space.py [--remote hf] [--dry-run]

First time only, point the remote at your Space:
    git remote add hf https://huggingface.co/spaces/<username>/adhikaar
When git prompts for a password, paste a Hugging Face *write* access token
(Settings -> Access Tokens), not your account password.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TEMP_BRANCH = "hf-space-deploy"

# Space configuration. `sdk: docker` makes Spaces build the root Dockerfile;
# `app_port` must match the port uvicorn binds in that Dockerfile's CMD.
SPACE_HEADER = """---
title: Adhikaar
emoji: 📜
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: A verifiable public-benefit reasoning engine for Indian welfare schemes.
---

"""


def git(*args: str, capture: bool = False) -> str:
    """Run a git command in the repo root, raising on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=True,
    )
    return (result.stdout or "").strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="hf", help="git remote for the Space (default: hf)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build the Space branch and stop before pushing, so you can inspect it",
    )
    args = parser.parse_args()

    if git("status", "--porcelain", capture=True):
        print("Working tree has uncommitted changes — commit or stash them first.")
        return 1

    remotes = git("remote", capture=True).split()
    if args.remote not in remotes:
        print(
            f"No git remote named '{args.remote}'. Add your Space first:\n"
            f"  git remote add {args.remote} "
            f"https://huggingface.co/spaces/<username>/adhikaar"
        )
        return 1

    original = git("rev-parse", "--abbrev-ref", "HEAD", capture=True)
    original_readme = README.read_text(encoding="utf-8")

    if original_readme.startswith("---"):
        print("README.md already carries front matter — expected a clean one on this branch.")
        return 1

    try:
        git("checkout", "-B", TEMP_BRANCH)
        README.write_text(SPACE_HEADER + original_readme, encoding="utf-8", newline="")
        git("add", "README.md")
        git("commit", "-m", "chore: Hugging Face Space configuration header (generated)")

        if args.dry_run:
            print(f"Dry run: built '{TEMP_BRANCH}'. Inspect it, then delete with:")
            print(f"  git checkout {original} && git branch -D {TEMP_BRANCH}")
            return 0

        # Space history is generated, so it is replaced wholesale each deploy.
        git("push", "--force", args.remote, f"{TEMP_BRANCH}:main")
        print(f"Pushed to '{args.remote}'. Watch the build in your Space's Logs tab.")
        return 0
    finally:
        if not args.dry_run:
            git("checkout", original)
            git("branch", "-D", TEMP_BRANCH)
            README.write_text(original_readme, encoding="utf-8", newline="")


if __name__ == "__main__":
    sys.exit(main())
