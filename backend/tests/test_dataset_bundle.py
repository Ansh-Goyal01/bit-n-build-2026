"""Integrity tests for the published dataset bundle (dataset/adhikaar-eligibility-v1).

These enforce the "auditable" claim: the manifest hashes must match the files on
disk, the declared counts must match the real rows, and every rule/persona must
satisfy the structural contract the datasheet promises. If someone edits a data
file without rebuilding, the hash check fails loudly.
"""

import hashlib
import json
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[2] / "dataset" / "adhikaar-eligibility-v1"
MANIFEST = BUNDLE / "manifest.json"

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(), reason="dataset bundle not built (run scripts/build_dataset.py)"
)


def _rows(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (BUNDLE / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_hashes_match_files_on_disk() -> None:
    for fname, meta in _manifest()["files"].items():
        path = BUNDLE / fname
        assert path.exists(), f"manifest lists {fname} but it is missing"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == meta["sha256"], f"{fname} changed since last build — rebuild the bundle"


def test_manifest_counts_match_actual_rows() -> None:
    counts = _manifest()["counts"]
    assert counts["rules"] == len(_rows("rules.jsonl"))
    assert counts["schemes"] == len(_rows("schemes.jsonl"))
    personas = _rows("personas.jsonl")
    assert counts["personas"] == len(personas)
    assert counts["personas_train"] == sum(1 for p in personas if p["split"] == "train")
    assert counts["personas_heldout"] == sum(1 for p in personas if p["split"] == "heldout")


def test_every_rule_is_clause_cited() -> None:
    for rule in _rows("rules.jsonl"):
        assert rule["kind"] in ("require", "exclude")
        assert rule["clause"].strip(), f"{rule['rule_id']} has no clause text"
        assert rule["source_url"].startswith("http"), f"{rule['rule_id']} has no source url"
        assert rule["when"], f"{rule['rule_id']} has no condition"


def test_persona_gold_only_references_known_schemes() -> None:
    scheme_ids = {s["scheme_id"] for s in _rows("schemes.jsonl")}
    for persona in _rows("personas.jsonl"):
        assert persona["split"] in ("train", "heldout")
        for verdict, ids in persona["gold"].items():
            assert verdict in ("eligible", "not_eligible", "need_info")
            unknown = set(ids) - scheme_ids
            assert not unknown, f"{persona['case_id']} references unknown schemes {unknown}"


def test_license_is_cc_by_4() -> None:
    assert _manifest()["license"] == "CC-BY-4.0"
    assert "CC BY 4.0" in (BUNDLE / "LICENSE").read_text(encoding="utf-8")
