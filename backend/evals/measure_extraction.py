"""Measure the rule extractor against hand-encoded gold rules (research eval).

Runs the LLM extractor on schemes that already have human-encoded rules and
scores the proposals at rule level:

- a proposed rule MATCHES a gold rule when kind and the canonical condition
  agree (field/op/value; gte 18 ≡ gt 17 for integers; any/all sets compared
  order-insensitively);
- precision = matched proposed / proposed, recall = matched gold / gold;
- mechanical edit-need proxies per matched rule: self_declared mismatch and
  clause-not-verbatim-in-source (whitespace-normalized containment).

Usage: python -m evals.measure_extraction apy ab-pmjay pmuy
Writes proposals + metrics to evals/results/extraction-*.json (measurement
artifacts only — nothing is written to the rules review queue).
"""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.extraction.propose import official_text, propose_rules
from app.ingestion.corpus import load_corpus
from app.rules.engine import Condition, Rule
from app.rules.loader import load_all_rules

RESULTS_DIR = Path(__file__).parent / "results"


def canonical(condition: Condition) -> tuple:
    """Order-insensitive, boundary-normalized condition signature."""
    if condition.any is not None:
        return ("any", frozenset(canonical(c) for c in condition.any))
    if condition.all is not None:
        return ("all", frozenset(canonical(c) for c in condition.all))
    op, value = condition.op, condition.value
    # integer boundary equivalence: gt N ≡ gte N+1, lt N ≡ lte N-1
    if isinstance(value, int) and not isinstance(value, bool):
        if op == "gt":
            op, value = "gte", value + 1
        elif op == "lt":
            op, value = "lte", value - 1
    if isinstance(value, str):
        value = value.strip().lower()
    return (condition.field, op, value)


def rule_signature(rule: Rule) -> tuple:
    return (rule.kind, canonical(rule.when))


def _normalize_text(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def measure_scheme(scheme_id: str) -> dict:
    corpus = {doc.scheme_id: doc for doc in load_corpus()}
    doc = corpus[scheme_id]
    gold = load_all_rules()[scheme_id]

    proposal = propose_rules(doc)

    gold_sigs = {rule_signature(r): r for r in gold.rules}
    matched: list[dict] = []
    unmatched_proposed: list[dict] = []
    source = _normalize_text(official_text(doc))

    seen_gold = set()
    for rule in proposal.rules:
        sig = rule_signature(rule)
        gold_rule = gold_sigs.get(sig)
        if gold_rule is not None and sig not in seen_gold:
            seen_gold.add(sig)
            matched.append(
                {
                    "proposed_id": rule.id,
                    "gold_id": gold_rule.id,
                    "self_declared_agrees": rule.self_declared == gold_rule.self_declared,
                    "clause_verbatim_in_source": _normalize_text(rule.clause) in source,
                }
            )
        else:
            unmatched_proposed.append(
                {
                    "id": rule.id,
                    "kind": rule.kind,
                    "condition": rule.when.model_dump(exclude_none=True),
                    "clause": rule.clause,
                }
            )

    missed_gold = [
        {"id": r.id, "kind": r.kind, "condition": r.when.model_dump(exclude_none=True)}
        for sig, r in gold_sigs.items()
        if sig not in seen_gold
    ]

    n_proposed = len(proposal.rules)
    n_gold = len(gold.rules)
    needs_edit = sum(
        1
        for m in matched
        if not (m["self_declared_agrees"] and m["clause_verbatim_in_source"])
    )
    return {
        "scheme_id": scheme_id,
        "gold_rules": n_gold,
        "proposed_rules": n_proposed,
        "matched": len(matched),
        "precision": round(len(matched) / n_proposed, 4) if n_proposed else 0.0,
        "recall": round(len(matched) / n_gold, 4) if n_gold else 0.0,
        "matched_needing_edit": needs_edit,
        "match_detail": matched,
        "unmatched_proposed": unmatched_proposed,
        "missed_gold": missed_gold,
        "blocked_rules": [b.model_dump() for b in proposal.blocked_rules],
        "rejected_drafts": proposal.rejected_drafts,
        "proposed_simplifications": proposal.simplifications,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("schemes", nargs="+", help="hand-encoded scheme ids to measure")
    args = parser.parse_args()

    reports = [measure_scheme(s) for s in args.schemes]
    total_gold = sum(r["gold_rules"] for r in reports)
    total_prop = sum(r["proposed_rules"] for r in reports)
    total_match = sum(r["matched"] for r in reports)
    summary = {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "schemes": [r["scheme_id"] for r in reports],
        "micro_precision": round(total_match / total_prop, 4) if total_prop else 0.0,
        "micro_recall": round(total_match / total_gold, 4) if total_gold else 0.0,
        "matched_needing_edit": sum(r["matched_needing_edit"] for r in reports),
        "total_matched": total_match,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"extraction-{datetime.now(UTC):%Y%m%d-%H%M}.json"
    out.write_text(
        json.dumps({"summary": summary, "per_scheme": reports}, indent=1),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=1))
    for r in reports:
        print(
            f"{r['scheme_id']:14s} P {r['precision']:.2f} R {r['recall']:.2f} "
            f"({r['matched']}/{r['proposed_rules']} proposed, {r['gold_rules']} gold, "
            f"{r['matched_needing_edit']} matched need edits)"
        )
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
