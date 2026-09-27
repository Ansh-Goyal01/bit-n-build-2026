"""Extraction CLI: python -m app.extraction [scheme_id ...]

With no arguments, drafts rule proposals for every corpus scheme that has no
live rules yet (the review-queue set). Proposals land in app/rules/proposed/
— never in the live rules directory.
"""

import argparse

from app.extraction.propose import propose_rules, write_proposal
from app.ingestion.corpus import load_corpus
from app.rules.loader import load_all_rules


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.extraction")
    parser.add_argument("schemes", nargs="*", help="scheme ids (default: all without live rules)")
    args = parser.parse_args()

    corpus = {doc.scheme_id: doc for doc in load_corpus()}
    live = set(load_all_rules())
    targets = args.schemes or sorted(set(corpus) - live)

    failures = 0
    for scheme_id in targets:
        doc = corpus.get(scheme_id)
        if doc is None:
            print(f"SKIP  {scheme_id}: not in corpus")
            failures += 1
            continue
        try:
            proposal = propose_rules(doc)
        except Exception as exc:  # noqa: BLE001 — keep drafting the rest of the batch
            print(f"FAIL  {scheme_id}: {type(exc).__name__}: {exc}")
            failures += 1
            continue
        out = write_proposal(proposal)
        print(
            f"OK    {scheme_id}: {len(proposal.rules)} rules, "
            f"{len(proposal.blocked_rules)} blocked, "
            f"{len(proposal.rejected_drafts)} rejected -> {out.name}"
        )
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
