"""Eval runner: python -m evals.run_eval --phase llm

Runs every dataset case through the pipeline and reports:
retrieval precision/recall, faithfulness (pre- and post-verifier),
and eligibility accuracy with FP/FN split. Results land in evals/results/.
All LLM calls are disk-cached, so re-runs are free and deterministic.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.agent.graph import run_assessment
from evals.judge import faithfulness
from evals.metrics import PairOutcome, retrieval_metrics, score_case, summarize

DATASET = Path(__file__).parent / "dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
CASE_DELAY_SECONDS = 5.0  # stay well inside free-tier rate limits


def load_cases(dataset: Path) -> list[dict]:
    lines = dataset.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def run(phase: str, dataset: Path = DATASET) -> dict:
    cases = load_cases(dataset)
    all_outcomes: list[PairOutcome] = []
    precisions: list[float] = []
    recalls: list[float] = []
    pre_supported = pre_total = post_supported = post_total = 0
    per_case: list[dict] = []

    engine = {"llm": "llm", "rules": "rules"}[phase]
    errored: list[str] = []
    judge_failures: list[str] = []
    for i, case in enumerate(cases):
        try:
            state = run_assessment(case["message"], engine=engine)
        except Exception as exc:  # noqa: BLE001 — rate-limit weather: wait out, retry once
            name = type(exc).__name__
            print(f"[{i + 1}/{len(cases)}] {case['case_id']}: ERROR {name}; retrying in 60s")
            time.sleep(60)
            try:
                state = run_assessment(case["message"], engine=engine)
            except Exception as exc2:  # noqa: BLE001
                print(f"[{i + 1}/{len(cases)}] {case['case_id']}: SKIPPED ({type(exc2).__name__})")
                errored.append(case["case_id"])
                continue
        chunks = {c.chunk_id: c.text for c in state.get("retrieved", [])}

        if state["status"] == "need_info":
            predicted: dict[str, str] = {}
        else:
            predicted = {r.scheme_id: r.verdict for r in state.get("results", [])}

        outcomes = score_case(case["case_id"], case["gold"], predicted)
        all_outcomes.extend(outcomes)

        relevant = {s for ids in case["gold"].values() for s in ids}
        retrieved = {c.scheme_id for c in state.get("retrieved", [])}
        if relevant and retrieved:
            p, r = retrieval_metrics(relevant, retrieved)
            precisions.append(p)
            recalls.append(r)

        # Faithfulness: raw LLM claims (pre-verifier) vs shipped claims (post-verifier).
        # Excerpt = the retrieved chunk when the citation points at one; for rule
        # citations the quote itself is the (human-verified) official clause.
        pre_claims = [
            (
                reason.text,
                "\n".join(
                    chunks[c.chunk_id] for c in reason.citations if c.chunk_id in chunks
                )
                or None,
            )
            for a in state.get("assessments", [])
            for reason in a.reasons
        ]
        post_claims = [
            (
                reason.text,
                "\n".join(
                    chunks.get(c.chunk_id, c.quote) for c in reason.citations
                )
                or None,
            )
            for r in state.get("results", [])
            for reason in r.reasons
        ]
        try:
            s, t = faithfulness(pre_claims)
            pre_supported, pre_total = pre_supported + s, pre_total + t
            s, t = faithfulness(post_claims)
            post_supported, post_total = post_supported + s, post_total + t
        except Exception as exc:  # noqa: BLE001 — judge rate-limited: keep outcomes,
            # exclude this case's claims from faithfulness aggregates.
            judge_failures.append(case["case_id"])
            print(f"    judge unavailable for {case['case_id']} ({type(exc).__name__})")

        per_case.append(
            {
                "case_id": case["case_id"],
                "status": state["status"],
                "predicted": predicted,
                "outcomes": [o.__dict__ for o in outcomes],
            }
        )
        print(f"[{i + 1}/{len(cases)}] {case['case_id']}: {[o.outcome for o in outcomes]}")
        time.sleep(CASE_DELAY_SECONDS)

    summary = {
        "phase": phase,
        "dataset": dataset.name,
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "cases": len(cases),
        "errored_cases": errored,
        "judge_unavailable_cases": judge_failures,
        "eligibility": summarize(all_outcomes),
        "retrieval": {
            "precision": round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
            "recall": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        },
        "faithfulness": {
            "pre_verifier": round(pre_supported / pre_total, 4) if pre_total else None,
            "post_verifier": round(post_supported / post_total, 4) if post_total else None,
            "pre_claims": pre_total,
            "post_claims": post_total,
        },
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    tag = "" if dataset == DATASET else f"{dataset.stem}-"
    out = RESULTS_DIR / f"{tag}{phase}-{datetime.now(UTC):%Y%m%d-%H%M}.json"
    payload = json.dumps({"summary": summary, "per_case": per_case}, indent=1)
    out.write_text(payload, encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"saved -> {out}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["llm", "rules"], default="llm")
    parser.add_argument(
        "--dataset", type=Path, default=DATASET, help="cases file (e.g. evals/heldout.jsonl)"
    )
    args = parser.parse_args()
    run(args.phase, args.dataset)
