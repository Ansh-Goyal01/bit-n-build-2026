"""Language-parity check: the VERDICT must be byte-identical across languages.

The engine is language-agnostic by construction (translation only at the
edges), so this is a regression tripwire, not an experiment: for each parity
profile the (scheme_id, verdict) vector for lang=hi (or any target) must equal
the lang=en run exactly. Also records translated-summary samples so a human
can spot-check translation faithfulness.

Runs against a live API (default http://localhost:8000):
    python -X utf8 evals/run_language_parity.py [lang ...]

Writes evals/results/language-parity-<lang>-<stamp>.json.
"""

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = "http://localhost:8000/api/assess"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Spans verdict types: entitled bundle, widow/BPL conditionals, student,
# excluded taxpayer, and a thin profile that must stay need_info.
PARITY_PROFILES: list[dict] = [
    {
        "age": 45, "gender": "female", "marital_status": "widowed", "area": "rural",
        "occupation": "farmer", "annual_family_income_inr": 80000,
        "is_farmer_with_land": "yes", "cultivates_crops": "yes",
        "has_land_ownership_or_tenure_docs": "yes", "pays_income_tax": "no",
        "holds_constitutional_or_political_post": "no",
        "is_practicing_registered_professional": "no", "has_bpl_card": "yes",
        "house_type": "kutcha", "has_lpg_connection": "no",
        "owns_motorized_vehicle": "no", "has_bank_account": "yes",
        "family_member_in_govt_service": "no", "receives_govt_pension_over_10k": "no",
        "bereavement_event": "yes", "is_pmjay_priority_category": "yes",
        "daughter_age": 6, "is_pregnant": "no", "single_girl_child": "no",
        "social_category": "general",
    },
    {
        "age": 20, "gender": "female", "occupation": "student", "is_student": "yes",
        "is_post_matric_student": "yes", "social_category": "sc",
        "annual_family_income_inr": 200000, "has_bank_account": "yes",
        "pays_income_tax": "no",
    },
    {
        "age": 35, "gender": "male", "occupation": "salaried",
        "annual_family_income_inr": 1500000, "pays_income_tax": "yes",
        "has_bank_account": "yes", "area": "urban",
    },
    {
        "age": 68, "gender": "male", "has_bpl_card": "yes", "area": "rural",
        "occupation": "retired", "has_bank_account": "yes", "pays_income_tax": "no",
    },
    {"age": 30, "occupation": "street vendor", "is_street_vendor": "yes",
     "has_vending_certificate_or_lor": "yes", "area": "urban",
     "annual_family_income_inr": 90000},
]


def call(profile: dict, lang: str) -> dict:
    body = json.dumps(
        {"message": "", "profile": profile, "engine": "rules", "lang": lang}
    ).encode()
    request = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    # First-run translation of a 30-scheme report is slow on free-tier quota;
    # every batch is disk-cached, so retries resume where the last run stopped.
    return json.loads(urllib.request.urlopen(request, timeout=900).read())


def verdict_vector(response: dict) -> list[tuple[str, str]]:
    return sorted((r["scheme_id"], r["verdict"]) for r in response.get("results", []))


def main() -> None:
    langs = sys.argv[1:] or ["hi"]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    for lang in langs:
        mismatches = []
        samples = []
        for i, profile in enumerate(PARITY_PROFILES):
            en = call(profile, "en")
            other = call(profile, lang)
            en_vector, other_vector = verdict_vector(en), verdict_vector(other)
            identical = en_vector == other_vector
            if not identical:
                mismatches.append({"profile_index": i, "en": en_vector, lang: other_vector})
            first = next(iter(other.get("results", [])), None)
            samples.append(
                {
                    "profile_index": i,
                    "verdicts_identical": identical,
                    "n_results": len(other.get("results", [])),
                    "status": other["status"],
                    "sample_scheme": first["scheme_id"] if first else None,
                    "sample_summary_en": en["results"][0]["summary"] if en.get("results") else en.get("question"),
                    f"sample_summary_{lang}": first["summary"] if first else other.get("question"),
                }
            )
            print(f"[{lang}] profile {i}: verdicts identical = {identical} "
                  f"({len(other.get('results', []))} results)")

        artifact = {
            "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "lang": lang,
            "profiles": len(PARITY_PROFILES),
            "verdict_parity": not mismatches,
            "mismatches": mismatches,
            "samples": samples,
        }
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / f"language-parity-{lang}-{stamp}.json"
        out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[{lang}] parity: {'PASS' if not mismatches else 'FAIL'} -> {out}")
        if mismatches:
            sys.exit(1)


if __name__ == "__main__":
    main()
