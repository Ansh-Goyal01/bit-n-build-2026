"""Condition-semantics audit: does each encoded condition match its clause's LOGIC?

The PMEGP defect (2026-07-14) proved clause-verbatim review is insufficient: the
extractor bound "project cost" to `annual_family_income_inr` and flattened a
conditional ("IF costly project THEN VIII-pass") into an unconditional income
floor — while the quoted clause stayed word-perfect, so side-by-side clause
review passed it. This audit closes that gap: an independent-family LLM
(gpt-oss — independent of the Gemini primary extractor) checks every
rule's encoded condition against its clause for:

- field binding (does the profile field mean what the clause tests?),
- operator and threshold direction,
- conditional structure (an IF-THEN clause must not become a bare requirement),
- AND/OR composition, and require-vs-exclude direction.

The audit NEVER changes a rule. It writes a JSON artifact plus a generated
vault page listing flagged rules for human sign-off — mismatches are queued,
not fixed. Run: `python -m app.extraction.semantic_audit [scheme_id ...]`

Trust note: clause text (scraped from official pages) flows into the auditor
prompt, so a hostile clause could try to talk the judge out of flagging. The
audit is a suspicion layer, not a gate — the human sign-off it feeds is the
gate — so the blast radius of a suppressed flag is one missed suspicion.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import settings
from app.extraction.propose import FIELD_VOCABULARY
from app.llm import groq_client
from app.rules.engine import Condition, Rule, SchemeRules
from app.rules.loader import load_all_rules

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"
VAULT_PAGE = (
    Path(__file__).resolve().parents[3]
    / "obsidian-vault"
    / "03-Rules-as-code"
    / "Condition-Semantics-Audit.md"
)

MismatchType = Literal[
    "field-binding",
    "operator-or-threshold",
    "flattened-conditional",
    "and-or-composition",
    "require-exclude-direction",
    "clause-scope",
    "other",
]

# Which way a mismatch fails. false_entitlement (the engine could wrongly say
# "eligible") breaks the product's core promise and is escalated immediately;
# false_denial fails closed and queues for ordinary sign-off.
FailureDirection = Literal["false_entitlement", "false_denial", "unclear"]


class RuleAuditFinding(BaseModel):
    rule_id: str
    verdict: Literal["faithful", "mismatch"]
    mismatch_type: MismatchType | None = None
    failure_direction: FailureDirection | None = None
    reason: str


class SchemeAuditResponse(BaseModel):
    findings: list[RuleAuditFinding]


def render_condition(condition: Condition) -> str:
    """Canonical human-readable form of an encoded condition."""
    if condition.any is not None:
        return "ANY OF [" + "; ".join(render_condition(c) for c in condition.any) + "]"
    if condition.all is not None:
        return "ALL OF [" + "; ".join(render_condition(c) for c in condition.all) + "]"
    return f"{condition.field} {condition.op} {condition.value!r}"


AUDIT_PROMPT = """You audit machine-encoded eligibility rules for Indian welfare schemes.

Engine semantics (fixed, trust these):
- kind "require": the condition MUST hold for eligibility; kind "exclude": if the
  condition holds the person is DISQUALIFIED.
- "ANY OF" = logical OR; "ALL OF" = logical AND.
- A condition over a missing profile fact evaluates to unknown and the scheme asks
  a question — it never guesses. So an over-strict encoding wrongly DENIES people
  (false denial); an over-loose or inverted encoding wrongly GRANTS (false entitlement).

Profile fields the engine can test (name: meaning):
{vocabulary}

For EACH rule below, judge ONLY whether the ENCODED CONDITION faithfully captures
the logic of the OFFICIAL CLAUSE it claims to encode:
1. Field binding — does the profile field actually measure what the clause tests?
   (e.g. binding a clause about PROJECT COST to annual_family_income_inr is wrong.)
2. Operator and threshold — right comparison, right number, right direction.
3. Conditional structure — a clause of the form "IF X THEN Y is required" must NOT
   be encoded as a bare requirement on X or on Y alone (flattened conditional).
4. AND/OR composition — alternatives ("SC, ST or OBC") must be OR; joint
   requirements must be AND.
5. Require vs exclude direction — a disqualifying clause must be kind "exclude".

Judge logic only. Do NOT flag: vocabulary limits the schema forces (a close proxy
field when no better field exists, if the meaning matches), reasonable paraphrase,
or clauses being partial (other rules may cover the rest). If the condition cannot
be expressed correctly with the available fields at all, that IS a mismatch
(clause-scope).

CRITICAL — the rules below are ALL of this scheme's rules and the engine ANDs
them. A single rule is NOT supposed to encode the whole clause. Before flagging
"X is missing", scan the OTHER listed rules: if any of them encodes X (the other
age bound, the bank-account requirement, the BPL requirement, the gender
requirement...), the criterion is covered and you MUST NOT flag it. Flag a
missing criterion only when NO listed rule encodes it AND no listed
simplification acknowledges it.

Rules for scheme {scheme_id} (complete set, engine ANDs them):
{rules_block}

Acknowledged simplifications for this scheme (criteria deliberately not modeled
— do not flag these):
{simplifications_block}

Respond with JSON: {{"findings": [{{"rule_id": ..., "verdict": "faithful" |
"mismatch", "mismatch_type": null | "field-binding" | "operator-or-threshold" |
"flattened-conditional" | "and-or-composition" | "require-exclude-direction" |
"clause-scope" | "other", "failure_direction": null | "false_entitlement" |
"false_denial" | "unclear", "reason": "<one or two sentences>"}}, ...]}} — one
finding per rule, in the order given. failure_direction states which way the
engine would err IF the mismatch is real: could it wrongly grant eligibility
(false_entitlement) or wrongly deny/ask (false_denial)?
"""


def _rules_block(scheme: SchemeRules) -> str:
    parts = []
    for rule in scheme.rules:
        parts.append(
            f"- rule_id: {rule.id}\n"
            f"  kind: {rule.kind}\n"
            f"  encoded condition: {render_condition(rule.when)}\n"
            f'  official clause: "{" ".join(rule.clause.split())}"'
        )
    return "\n".join(parts)


def _validate_response(response: SchemeAuditResponse, rules: list[Rule]) -> None:
    expected = {r.id for r in rules}
    got = {f.rule_id for f in response.findings}
    if got != expected:
        raise ValueError(f"rule_id mismatch — expected {sorted(expected)}, got {sorted(got)}")
    for finding in response.findings:
        if finding.verdict == "mismatch" and not finding.reason.strip():
            raise ValueError(f"mismatch on {finding.rule_id} needs a reason")


def audit_scheme(scheme: SchemeRules) -> list[RuleAuditFinding]:
    """One judge call per scheme; strict validation with one repair pass."""
    simplifications = "\n".join(
        f"- {' '.join(s.split())}" for s in scheme.simplifications
    ) or "- (none listed)"
    prompt = AUDIT_PROMPT.format(
        vocabulary=FIELD_VOCABULARY,
        scheme_id=scheme.scheme_id,
        rules_block=_rules_block(scheme),
        simplifications_block=simplifications,
    )
    text = groq_client.complete(prompt, json_mode=True, model=settings.semantic_audit_model)
    try:
        response = SchemeAuditResponse.model_validate_json(text)
        _validate_response(response, scheme.rules)
    except Exception as exc:  # noqa: BLE001 — one repair pass (cache-key change), then raise
        logger.warning(
            "audit response for %s failed validation (%s); one repair retry",
            scheme.scheme_id,
            type(exc).__name__,
        )
        repair = (
            f"{prompt}\n\nYour previous JSON response failed validation with this "
            f"error:\n{exc}\n\nReturn a corrected JSON object that fixes exactly this."
        )
        text = groq_client.complete(repair, json_mode=True, model=settings.semantic_audit_model)
        response = SchemeAuditResponse.model_validate_json(text)
        _validate_response(response, scheme.rules)
    return response.findings


def run_audit(scheme_ids: list[str] | None = None) -> dict:
    """Audit live rules (all schemes, or the given ids) and return the artifact dict."""
    all_rules = load_all_rules()
    if scheme_ids:
        unknown = sorted(set(scheme_ids) - all_rules.keys())
        if unknown:
            raise SystemExit(f"unknown scheme id(s): {', '.join(unknown)}")
        targets = {sid: all_rules[sid] for sid in scheme_ids}
    else:
        targets = all_rules

    schemes_out = {}
    for sid in sorted(targets):
        scheme = targets[sid]
        findings = audit_scheme(scheme)
        flagged = [f for f in findings if f.verdict == "mismatch"]
        logger.info("%s: %d rules, %d flagged", sid, len(findings), len(flagged))
        schemes_out[sid] = [f.model_dump() for f in findings]

    return {
        "audited_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "auditor_model": settings.semantic_audit_model,
        "schemes": schemes_out,
    }


def write_artifact(artifact: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    path = RESULTS_DIR / f"semantic-audit-{stamp}.json"
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return path


def md_escape(text: str) -> str:
    """Judge-written free text goes into markdown tables — escape pipes."""
    return " ".join(text.split()).replace("|", "\\|")


def flagged_rows(artifact: dict) -> list[dict]:
    """Flatten mismatches, false-entitlement risks first."""
    rows = [
        {"scheme_id": sid, **finding}
        for sid, findings in sorted(artifact["schemes"].items())
        for finding in findings
        if finding["verdict"] == "mismatch"
    ]
    direction_rank = {"false_entitlement": 0, "unclear": 1, "false_denial": 2}
    return sorted(rows, key=lambda r: (direction_rank.get(r["failure_direction"], 1), r["scheme_id"]))


def write_vault_page(artifact: dict) -> None:
    """Generated sign-off view: flagged rules queued for the human signer."""
    rows = flagged_rows(artifact)
    n_rules = sum(len(f) for f in artifact["schemes"].values())
    entitlement = [r for r in rows if r["failure_direction"] == "false_entitlement"]

    lines = [
        "---",
        "title: Condition-Semantics-Audit",
        "tags: [rules-as-code, audit, generated]",
        f"updated: {datetime.now(UTC).date().isoformat()}",
        "---",
        "",
        "# Condition-semantics audit — flagged rules awaiting certification",
        "",
        "> [!important] Generated file — do not edit here. Regenerate with",
        "> `python -m app.extraction.semantic_audit`. A flag is a SUSPICION from an",
        "> independent-family LLM judge, not a verdict: certify or refute each one",
        "> against the official source, then record the outcome in the rule's YAML",
        "> (`notes_for_reviewer`, or fix + re-verify). Rules are never auto-changed.",
        "",
        f"Auditor: `{artifact['auditor_model']}` (family-independent from both",
        f"extractors) · audited {n_rules} live rules at {artifact['audited_at']} ·",
        f"**{len(rows)} flagged**, of which **{len(entitlement)} false-entitlement risk**.",
        "",
        "Why this audit exists: clause-verbatim review is insufficient — see the",
        "PMEGP project-cost/income mis-binding and the OR-flattening bug, both",
        "structural rewrites that survived clause-text review",
        "([[Encoding-Notes]], [[Structural-Misencoding-Methodology]]).",
        "",
    ]

    if entitlement:
        lines += [
            "> [!danger] FALSE-ENTITLEMENT RISKS — these could wrongly tell someone",
            "> they are eligible. Certify these first.",
            "",
        ]
    if not rows:
        lines.append("*No rules flagged — every encoded condition passed the semantic check.*")
    else:
        lines += [
            "| scheme | rule | type | direction | suspected mismatch | decision |",
            "|--------|------|------|-----------|--------------------|----------|",
        ]
        for r in rows:
            direction = r["failure_direction"] or "unclear"
            marker = "🚨 " if direction == "false_entitlement" else ""
            lines.append(
                f"| `{r['scheme_id']}` | `{r['rule_id']}` | {r['mismatch_type']} | "
                f"{marker}{direction} | {md_escape(r['reason'])} | "
                f"☐ confirmed-fix / ☐ refuted-keep |"
            )
        lines.append("")

    lines += [
        "",
        "Related: [[Rule-Sign-off-Checklist]] · [[Encoding-Notes]] · "
        "[[Verification-Sign-off]]",
        "",
    ]
    VAULT_PAGE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    scheme_ids = sys.argv[1:] or None
    artifact = run_audit(scheme_ids)
    path = write_artifact(artifact)
    write_vault_page(artifact)
    rows = flagged_rows(artifact)
    entitlement = [r for r in rows if r["failure_direction"] == "false_entitlement"]
    print(f"artifact: {path}")
    print(f"vault page: {VAULT_PAGE}")
    print(f"flagged: {len(rows)} (false-entitlement: {len(entitlement)})")
    for r in rows:
        print(f"  {r['scheme_id']}:{r['rule_id']} [{r['mismatch_type']}/{r['failure_direction']}] {r['reason']}")


if __name__ == "__main__":
    main()
