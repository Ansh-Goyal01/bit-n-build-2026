"""Ingestion CLI: python -m app.ingestion [fetch|build|index|all]"""

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.ingestion")
    parser.add_argument("step", choices=["fetch", "build", "index", "all"], help="pipeline step")
    args = parser.parse_args()

    failures = 0
    if args.step in ("fetch", "all"):
        from app.ingestion.fetch import run_fetch

        failures += run_fetch()
    if args.step in ("build", "all"):
        from app.ingestion.corpus import build_corpus

        build_corpus()
    if args.step in ("index", "all"):
        from app.ingestion.index import build_index

        build_index()
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
