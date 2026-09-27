"""Generate frontend/lib/data/schemes.json from the committed corpus + rules repository.

The Explore pages are statically generated from this file so they stay fast and
readable even when the free-tier backend is cold. Re-run after any corpus or
rules change:  python -X utf8 scripts/generate_scheme_data.py
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
RULES_DIR = ROOT / "backend" / "app" / "rules" / "schemes"
FRESHNESS_DIR = ROOT / "data" / "freshness"
BENEFIT_VALUES = ROOT / "data" / "benefit_values.yaml"
OUT = ROOT / "frontend" / "lib" / "data" / "schemes.json"
FRESHNESS_OUT = ROOT / "frontend" / "lib" / "data" / "freshness.json"

# Schemes deliberately outside Adhikaar's scope â€” the applicant is not an
# individual, so the eligibility check can never apply. Distinct from
# "coming soon" (a rules-pending state): this is a final, honest exclusion.
OUT_OF_SCOPE = {
    "hepsn": (
        "This grant is applied for by a college or institution, not by an "
        "individual â€” so a personal eligibility check doesn't apply."
    ),
}


def strip_markdown(text: str) -> str:
    """Corpus sections are markdown-ish; catalog snippets must be plain prose."""
    out = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)  # headings
    out = re.sub(r"^\s{0,3}>\s?", "", out, flags=re.MULTILINE)  # blockquotes
    # list markers â€” bullets tolerate a missing space after the marker ("-Cashlessâ€¦")
    out = re.sub(r"^\s*(?:[-*+]\s*|\d+\.\s+)", "", out, flags=re.MULTILINE)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)  # bold
    out = re.sub(r"\*([^*]+)\*", r"\1", out)  # italics
    out = re.sub(r"`([^`]+)`", r"\1", out)  # code
    out = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", out)  # links
    return out


def first_sentences(text: str, max_chars: int = 220) -> str:
    """A short, clean snippet for catalog cards."""
    flat = re.sub(r"\s+", " ", strip_markdown(text or "")).strip()
    # bullets glued to the previous sentence survive line-based stripping
    # ("â€¦per year.- Comprehensiveâ€¦") â€” a sentence break is what was meant
    flat = re.sub(r"\.\s*-\s+", ". ", flat)
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars]
    last_stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: last_stop + 1] if last_stop > 80 else cut.rsplit(" ", 1)[0] + "â€¦"


def load_rules(scheme_id: str) -> list[dict]:
    path = RULES_DIR / f"{scheme_id}.yaml"
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        {
            "id": rule["id"],
            "kind": rule["kind"],
            "clause": re.sub(r"\s+", " ", rule["clause"]).strip(),
            "source_url": rule["source_url"],
        }
        for rule in doc.get("rules", [])
    ]


def scheme_state(scheme_id: str) -> str | None:
    """The one state a state scheme serves, read from its own residence rule
    (a require rule `state eq <name>`) so the catalog badge and the engine
    can never disagree. None for central schemes."""
    path = RULES_DIR / f"{scheme_id}.yaml"
    if not path.exists():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for rule in doc.get("rules", []):
        when = rule.get("when", {})
        if rule["kind"] == "require" and when.get("field") == "state" and when.get("op") == "eq":
            return when["value"]
    return None


def load_benefit_values() -> dict[str, dict]:
    """R6 — verified benefit-value entries only. Pending entries never reach
    the frontend: same nothing-unverified-is-live invariant as rules."""
    if not BENEFIT_VALUES.exists():
        return {}
    doc = yaml.safe_load(BENEFIT_VALUES.read_text(encoding="utf-8")) or {}
    verified = {}
    for scheme_id, entry in (doc.get("schemes") or {}).items():
        if entry.get("review_status") == "verified":
            verified[scheme_id] = {
                "label": entry["label"],
                "amount_inr": entry["amount_inr"],
                "period": entry["period"],
            }
    return verified


def latest_freshness_summary() -> dict | None:
    """Condense the newest R7 monitor report (data/freshness/report-*.json) for
    the frontend: when the catalog was last diffed against live myScheme text,
    and which schemes drifted. Reports are date-named, so lexical max = newest."""
    reports = sorted(FRESHNESS_DIR.glob("report-*.json"))
    if not reports:
        return None
    report = json.loads(reports[-1].read_text(encoding="utf-8"))
    return {
        "generated_at": report["generated_at"],
        "schemes_checked": report["schemes_checked"],
        "fetch_failures": report["fetch_failures"],
        "changed": {
            diff["scheme_id"]: {
                "needs_review": diff["needs_review"],
                "sections": [
                    f'{change["section"]} ({change["change"]})' for change in diff["changes"]
                ],
            }
            for diff in report["changed"]
        },
    }


def main() -> None:
    benefit_values = load_benefit_values()
    schemes = []
    for path in sorted(CORPUS_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sections = doc.get("sections", {})
        schemes.append(
            {
                "scheme_id": doc["scheme_id"],
                "short_name": doc["short_name"],
                "name": doc["name"],
                "category": doc["category"],
                # myScheme labels state schemes "State" or "State/ UT".
                "level": "state" if doc.get("level", "").startswith("State") else "central",
                "state": scheme_state(doc["scheme_id"]),
                "ministry": doc["ministry"],
                "page_url": doc["page_url"],
                "references": doc.get("references", []),
                "fetched_at": doc.get("fetched_at"),
                "benefit_snippet": first_sentences(sections.get("benefits", "")),
                "sections": {
                    key: sections[key]
                    for key in (
                        "details",
                        "benefits",
                        "eligibility",
                        "exclusions",
                        "application",
                        "documents",
                    )
                    if sections.get(key)
                },
                "rules": load_rules(doc["scheme_id"]),
                "benefit_value": benefit_values.get(doc["scheme_id"]),
                "out_of_scope": doc["scheme_id"] in OUT_OF_SCOPE,
                "out_of_scope_reason": OUT_OF_SCOPE.get(doc["scheme_id"], ""),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(schemes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{len(schemes)} schemes -> {OUT}")

    freshness = latest_freshness_summary()
    FRESHNESS_OUT.write_text(
        json.dumps(freshness, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    label = freshness["generated_at"][:10] if freshness else "no report yet"
    print(f"freshness ({label}) -> {FRESHNESS_OUT}")


if __name__ == "__main__":
    main()
