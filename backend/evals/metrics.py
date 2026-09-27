"""Scoring for the labeled eval set.

Verdict mapping: eligible/likely_eligible -> positive, not_eligible -> negative,
need_more_info -> abstain, scheme absent from the answer -> absent.

Scoring policy per labeled (case, scheme) pair:
- gold eligible:     positive=correct, negative=FN, abstain=abstain, absent=FN
- gold not_eligible: negative=correct, positive=FP, abstain=abstain,
                     absent=correct (the system never asserted the entitlement)
- gold need_info:    abstain=correct, positive=FP (overclaim), negative=FN, absent=abstain
"""

from dataclasses import dataclass
from typing import Literal

Pred = Literal["positive", "negative", "abstain", "absent"]
Outcome = Literal["correct", "fp", "fn", "abstain"]

VERDICT_TO_PRED: dict[str, Pred] = {
    "eligible": "positive",
    "likely_eligible": "positive",
    "not_eligible": "negative",
    "need_more_info": "abstain",
}


@dataclass(frozen=True)
class PairOutcome:
    case_id: str
    scheme_id: str
    gold: str
    pred: Pred
    outcome: Outcome


def _score_pair(gold: str, pred: Pred) -> Outcome:
    if gold == "eligible":
        return {"positive": "correct", "negative": "fn", "abstain": "abstain", "absent": "fn"}[pred]
    if gold == "not_eligible":
        outcomes: dict[Pred, Outcome] = {
            "positive": "fp",
            "negative": "correct",
            "abstain": "abstain",
            "absent": "correct",
        }
        return outcomes[pred]
    return {"positive": "fp", "negative": "fn", "abstain": "correct", "absent": "abstain"}[pred]


def score_case(
    case_id: str, gold: dict[str, list[str]], predicted_verdicts: dict[str, str]
) -> list[PairOutcome]:
    outcomes = []
    for gold_label, scheme_ids in gold.items():
        # dataset keys: eligible / not_eligible / need_info
        label = {"eligible": "eligible", "not_eligible": "not_eligible", "need_info": "need_info"}[
            gold_label
        ]
        for scheme_id in scheme_ids:
            verdict = predicted_verdicts.get(scheme_id)
            pred: Pred = VERDICT_TO_PRED.get(verdict, "absent") if verdict else "absent"
            outcomes.append(
                PairOutcome(case_id, scheme_id, label, pred, _score_pair(label, pred))
            )
    return outcomes


def summarize(outcomes: list[PairOutcome]) -> dict[str, float | int]:
    total = len(outcomes)
    kinds = ("correct", "fp", "fn", "abstain")
    counts = {k: sum(1 for o in outcomes if o.outcome == k) for k in kinds}
    return {
        "pairs": total,
        "accuracy": round(counts["correct"] / total, 4) if total else 0.0,
        "false_positives": counts["fp"],
        "false_negatives": counts["fn"],
        "abstained": counts["abstain"],
    }


def retrieval_metrics(relevant: set[str], retrieved: set[str]) -> tuple[float, float]:
    if not retrieved or not relevant:
        return (0.0, 0.0)
    hit = len(relevant & retrieved)
    return (hit / len(retrieved), hit / len(relevant))
