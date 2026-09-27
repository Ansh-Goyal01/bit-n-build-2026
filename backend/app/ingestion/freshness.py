"""R7 scheme-freshness monitor: diff live myScheme content against the committed corpus.

The 111 human-verified rules were audited against the text in data/corpus/.
myScheme can change that text at any time without notice, which would silently
invalidate the audit. This module re-fetches each scheme, runs the fresh bundle
through the exact same cleaning as the committed corpus (corpus_doc_from_bundle),
and diffs the cleaned sections — so volatile API metadata never fires an alert,
only meaning-bearing text changes do.

Changed schemes land in a dated JSON report under data/freshness/ for human
review; schemes with live rules (checkable) are the highest-priority flags.

Run: python -m app.ingestion.freshness [--limit N]
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.config import DATA_DIR, settings
from app.ingestion.corpus import corpus_doc_from_bundle
from app.ingestion.fetch import REQUEST_DELAY_SECONDS, fetch_scheme_bundle
from app.ingestion.models import CorpusDoc
from app.ingestion.schemes import SCHEME_SOURCES

# Sections that rules are encoded from; a change here can invalidate verdicts.
REVIEW_CRITICAL_SECTIONS = frozenset({"eligibility", "exclusions", "benefits", "documents"})

RULES_DIR = Path(__file__).resolve().parents[1] / "rules" / "schemes"
FRESHNESS_DIR = DATA_DIR / "freshness"


class SectionChange(BaseModel):
    """One section whose cleaned text differs from the committed corpus."""

    section: str
    change: str  # "added" | "removed" | "modified"
    review_critical: bool


class SchemeDiff(BaseModel):
    """Freshness result for one scheme (only persisted when something changed)."""

    scheme_id: str
    short_name: str
    checkable: bool  # scheme has live rules in rules/schemes/
    changes: list[SectionChange]
    references_changed: bool
    needs_review: bool  # any review-critical section changed


class FreshnessReport(BaseModel):
    """One full monitor run across the catalog."""

    generated_at: str
    schemes_checked: int
    fetch_failures: list[str]
    changed: list[SchemeDiff]

    @property
    def needs_review_count(self) -> int:
        return sum(1 for diff in self.changed if diff.needs_review)


def diff_scheme_sections(old: dict[str, str], new: dict[str, str]) -> list[SectionChange]:
    """Diff cleaned section texts; returns one SectionChange per differing section."""
    changes: list[SectionChange] = []
    for section in sorted(set(old) | set(new)):
        if section not in new:
            kind = "removed"
        elif section not in old:
            kind = "added"
        elif old[section] != new[section]:
            kind = "modified"
        else:
            continue
        changes.append(
            SectionChange(
                section=section,
                change=kind,
                review_critical=section in REVIEW_CRITICAL_SECTIONS,
            )
        )
    return changes


def build_scheme_diff(old_doc: CorpusDoc, new_doc: CorpusDoc, checkable: bool) -> SchemeDiff:
    """Compare committed vs freshly-fetched corpus docs for one scheme."""
    changes = diff_scheme_sections(old_doc.sections, new_doc.sections)
    old_refs = sorted((ref.title, ref.url) for ref in old_doc.references)
    new_refs = sorted((ref.title, ref.url) for ref in new_doc.references)
    return SchemeDiff(
        scheme_id=old_doc.scheme_id,
        short_name=old_doc.short_name,
        checkable=checkable,
        changes=changes,
        references_changed=old_refs != new_refs,
        needs_review=any(change.review_critical for change in changes),
    )


def live_rule_scheme_ids(rules_dir: Path = RULES_DIR) -> set[str]:
    """Scheme ids with live (signed-off) rules — the checkable set."""
    return {path.stem for path in rules_dir.glob("*.yaml")}


def run_freshness_check(limit: int | None = None) -> FreshnessReport:
    """Re-fetch every myScheme-sourced scheme and diff it against the committed corpus."""
    checkable_ids = live_rule_scheme_ids()
    failures: list[str] = []
    changed: list[SchemeDiff] = []
    checked = 0

    sources = SCHEME_SOURCES[:limit] if limit else SCHEME_SOURCES
    with httpx.Client() as client:
        for source in sources:
            corpus_path = settings.corpus_dir / f"{source.slug}.json"
            if not corpus_path.exists():
                print(f"SKIP    {source.slug}: no committed corpus doc")
                continue
            old_doc = CorpusDoc.model_validate_json(corpus_path.read_text(encoding="utf-8"))
            try:
                bundle = fetch_scheme_bundle(client, source)
            except Exception as exc:  # noqa: BLE001 — record and continue the batch
                failures.append(source.slug)
                print(f"FAIL    {source.slug}: {type(exc).__name__}: {exc}")
                continue
            new_doc = corpus_doc_from_bundle(bundle)
            checked += 1
            diff = build_scheme_diff(old_doc, new_doc, checkable=source.slug in checkable_ids)
            if diff.changes or diff.references_changed:
                changed.append(diff)
                flag = "REVIEW" if diff.needs_review else "info"
                sections = ", ".join(f"{c.section}({c.change})" for c in diff.changes) or "refs"
                print(f"CHANGED {source.slug} [{flag}]: {sections}")
            else:
                print(f"OK      {source.slug}")
            time.sleep(REQUEST_DELAY_SECONDS)

    return FreshnessReport(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        schemes_checked=checked,
        fetch_failures=failures,
        changed=changed,
    )


def write_report(report: FreshnessReport) -> Path:
    """Persist the run to data/freshness/report-YYYY-MM-DD.json."""
    FRESHNESS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FRESHNESS_DIR / f"report-{report.generated_at[:10]}.json"
    out_path.write_text(json.dumps(report.model_dump(), indent=1), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff live myScheme content vs committed corpus")
    parser.add_argument("--limit", type=int, default=None, help="only check the first N schemes")
    args = parser.parse_args()

    report = run_freshness_check(limit=args.limit)
    out_path = write_report(report)

    print(
        f"\nChecked {report.schemes_checked} schemes: "
        f"{len(report.changed)} changed, {report.needs_review_count} need review, "
        f"{len(report.fetch_failures)} fetch failures"
    )
    print(f"Report: {out_path}")
    # Non-zero exit when human review is needed, so CI/cron can alert on it.
    return 1 if report.needs_review_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
