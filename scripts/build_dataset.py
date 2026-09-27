"""Build the public Adhikaar Eligibility Dataset from the internal rule repo + eval set.

This is a pure *projection* of artifacts that already live in the repo — it invents
no facts. It flattens the versioned YAML rule files, merges the labeled persona sets,
copies the reproducible eval headline numbers, and writes a hash-pinned manifest so
anyone can verify the bundle is exactly what this repo produced.

Run: python scripts/build_dataset.py
Output: dataset/adhikaar-eligibility-v1/{rules,schemes,personas}.jsonl + schema/manifest/eval_report

The static docs (DATASHEET.md, README.md, LICENSE) are authored by hand and are NOT
regenerated here; the manifest records their hashes so they stay honest across rebuilds.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "backend" / "app" / "rules" / "schemes"
EVALS_DIR = ROOT / "backend" / "evals"
CORPUS_DIR = ROOT / "data" / "corpus"
RESULTS_DIR = EVALS_DIR / "results"

DATASET_VERSION = "v1"
OUT_DIR = ROOT / "dataset" / f"adhikaar-eligibility-{DATASET_VERSION}"

# Data files this script regenerates (hashed into the manifest).
DERIVED_FILES = (
    "rules.jsonl", "schemes.jsonl", "personas.jsonl", "eval_report.json", "schema.json",
)
# Hand-authored companions — hashed so a silent edit shows up in the manifest diff.
STATIC_FILES = ("DATASHEET.md", "README.md", "LICENSE")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _scheme_names() -> dict[str, dict[str, str]]:
    """scheme_id -> {short_name, name} from the committed corpus docs, when present."""
    names: dict[str, dict[str, str]] = {}
    for path in sorted(CORPUS_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sid = doc.get("scheme_id")
        if sid:
            names[sid] = {"short_name": doc.get("short_name", ""), "name": doc.get("name", "")}
    return names


def build_rules_and_schemes() -> tuple[list[dict], list[dict]]:
    """Flatten every verified scheme file into one row per rule + one row per scheme."""
    names = _scheme_names()
    rule_rows: list[dict] = []
    scheme_rows: list[dict] = []

    for path in sorted(RULES_DIR.glob("*.yaml")):
        scheme = yaml.safe_load(path.read_text(encoding="utf-8"))
        sid = scheme["scheme_id"]
        meta = names.get(sid, {"short_name": "", "name": ""})
        rules = scheme.get("rules", [])

        for rule in rules:
            rule_rows.append(
                {
                    "scheme_id": sid,
                    "scheme_version": scheme["version"],
                    "rule_id": rule["id"],
                    "kind": rule["kind"],                       # require | exclude
                    "when": rule["when"],                       # machine-readable condition tree
                    "clause": rule["clause"],                   # verbatim official text
                    "source_url": rule["source_url"],           # exact government source
                    "ask": rule["ask"],                         # plain-language question
                    "self_declared": rule.get("self_declared", False),
                    "review_status": rule.get("review_status", "encoded"),
                }
            )

        scheme_rows.append(
            {
                "scheme_id": sid,
                "short_name": meta["short_name"],
                "name": meta["name"],
                "version": scheme["version"],
                "n_rules": len(rules),
                "n_require": sum(1 for r in rules if r["kind"] == "require"),
                "n_exclude": sum(1 for r in rules if r["kind"] == "exclude"),
                "simplifications": scheme.get("simplifications", []),
            }
        )

    return rule_rows, scheme_rows


def build_personas() -> list[dict]:
    """Merge the labeled persona sets, tagging each with its dev-time split."""
    rows: list[dict] = []
    for fname, split in (("dataset.jsonl", "train"), ("heldout.jsonl", "heldout")):
        path = EVALS_DIR / fname
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "split": split,      # heldout was withheld during rule development
                    "message": case["message"],
                    "gold": case["gold"],  # {eligible, not_eligible, need_info}
                }
            )
    return rows


def _latest_result(prefix: str) -> dict | None:
    """Newest evals/results/<prefix>-*.json summary, or None if absent."""
    matches = sorted(RESULTS_DIR.glob(f"{prefix}-*.json"))
    if not matches:
        return None
    payload = json.loads(matches[-1].read_text(encoding="utf-8"))
    summary = payload["summary"]
    return {
        "source_file": matches[-1].name,
        "cases": summary["cases"],
        "eligibility": summary["eligibility"],
        "faithfulness": summary["faithfulness"],
    }


def build_eval_report() -> dict:
    """The reproducible headline: deterministic rules engine vs LLM baseline."""
    return {
        "note": (
            "The rules engine is deterministic (no LLM in the verdict path): same input, "
            "same output. Reproduce the rules rows offline with "
            "`python -m evals.run_eval --phase rules`. Faithfulness (post_verifier) and the "
            "llm baseline require an LLM judge/runner and are reported as measured."
        ),
        "labeled_pairs": {
            "main_set": _latest_result("rules"),
            "main_set_llm_baseline": _latest_result("llm"),
            "heldout_set": _latest_result("heldout-rules"),
        },
    }


def build_schema() -> dict:
    """Lightweight, human-readable field docs for each file (not full JSON Schema)."""
    return {
        "rules.jsonl": {
            "scheme_id": "stable scheme identifier",
            "scheme_version": "date-versioned rule file this rule came from",
            "rule_id": "unique within the scheme",
            "kind": "'require' (must hold) or 'exclude' (must not hold)",
            "when": "machine-readable condition tree over typed profile fields "
            "(leaf: field/op/value; combinators: any/all)",
            "clause": "verbatim or tightly-quoted official scheme text this rule encodes",
            "source_url": "exact government source the clause was read from",
            "ask": "plain-language question that resolves the fact when unknown",
            "self_declared": "true if the state verifies this fact "
            "(softens 'eligible' to 'likely_eligible')",
            "review_status": "'encoded' (machine-encoded + unit-tested) or "
            "'verified' (human-certified against source)",
        },
        "schemes.jsonl": {
            "scheme_id": "stable scheme identifier",
            "short_name": "abbreviation (e.g. PM-JAY)",
            "name": "full scheme name",
            "version": "date-versioned rule file",
            "n_rules / n_require / n_exclude": "rule counts",
            "simplifications": "honest omissions — criteria in the official text not yet encoded",
        },
        "personas.jsonl": {
            "case_id": "unique persona id",
            "split": "'train' or 'heldout' (heldout withheld during rule development)",
            "message": "free-text household description, as a user would phrase it",
            "gold": "hand-labeled verdicts: "
            "{eligible, not_eligible, need_info} -> [scheme_id, ...]",
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rule_rows, scheme_rows = build_rules_and_schemes()
    persona_rows = build_personas()

    _write_jsonl(OUT_DIR / "rules.jsonl", rule_rows)
    _write_jsonl(OUT_DIR / "schemes.jsonl", scheme_rows)
    _write_jsonl(OUT_DIR / "personas.jsonl", persona_rows)
    (OUT_DIR / "eval_report.json").write_text(
        json.dumps(build_eval_report(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "schema.json").write_text(
        json.dumps(build_schema(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Manifest: counts + content hashes so the bundle is independently verifiable.
    files: dict[str, dict[str, Any]] = {}
    for fname in DERIVED_FILES + STATIC_FILES:
        path = OUT_DIR / fname
        if path.exists():  # static docs may not exist on the very first run
            files[fname] = {"sha256": _sha256(path), "bytes": path.stat().st_size}

    manifest = {
        "dataset": "adhikaar-eligibility",
        "version": DATASET_VERSION,
        "license": "CC-BY-4.0",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_commit": _git_commit(),
        "counts": {
            "schemes": len(scheme_rows),
            "rules": len(rule_rows),
            "personas": len(persona_rows),
            "personas_train": sum(1 for p in persona_rows if p["split"] == "train"),
            "personas_heldout": sum(1 for p in persona_rows if p["split"] == "heldout"),
        },
        "files": files,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Built {OUT_DIR.relative_to(ROOT)}")
    for key, val in manifest["counts"].items():
        print(f"  {key:20} {val}")
    missing = [f for f in STATIC_FILES if not (OUT_DIR / f).exists()]
    if missing:
        print(f"  NOTE: static docs not yet present: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
