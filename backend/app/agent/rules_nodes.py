"""Phase 2 nodes: the deterministic rules engine decides; the LLM only explains.

The engine evaluates every live scheme against the typed profile. Reasons cite the
rule's source clause (official text, human-verified at encoding time), so no
chunk-containment verification is needed — grounding holds by construction.
The LLM writes the one-line friendly summaries and can never change a verdict;
if it fails, deterministic template summaries ship instead.
"""

import logging
import os

from pydantic import BaseModel

from app.agent.nodes import corpus_by_id
from app.agent.state import (
    AgentState,
    ConfirmationStep,
    SchemeResult,
    Verdict,
    VerifiedCitation,
    VerifiedReason,
)
from app.ingestion.models import CorpusDoc
from app.llm.router import generate_structured_resilient
from app.rules.application import parse_application_modes, parse_document_items
from app.rules.doc_guides import guide_keys_for
from app.rules.engine import (
    Condition,
    RuleFinding,
    RuleVerdict,
    SchemeRules,
    evaluate_scheme,
    find_near_miss,
)
from app.rules.loader import load_all_rules

logger = logging.getLogger(__name__)

VERDICT_ORDER: dict[Verdict, int] = {
    "eligible": 0,
    "likely_eligible": 1,
    "need_more_info": 2,
    "not_eligible": 3,
}

TEMPLATE_SUMMARIES: dict[Verdict, str] = {
    "eligible": "Based on the official rules, you appear to qualify for this scheme.",
    "likely_eligible": (
        "You appear to qualify based on the official rules — one condition rests on a "
        "fact the authorities will verify."
    ),
    "need_more_info": "We need one or two more details to check this scheme for you.",
    "not_eligible": (
        "Based on the official rules, this scheme doesn't apply to your situation."
    ),
}


ENTITLED: frozenset[Verdict] = frozenset({"eligible", "likely_eligible"})


def _condition_fields(condition: Condition) -> set[str]:
    fields = {condition.field} if condition.field else set()
    for child in (condition.any or []) + (condition.all or []):
        fields |= _condition_fields(child)
    return fields


def _is_out_of_state(scheme: SchemeRules, verdict: RuleVerdict) -> bool:
    """True when a state-residence rule (a require rule that tests only `state`)
    failed — the person's known state is not one the scheme serves. Such a
    scheme is left out of results rather than listed as "not eligible"; the
    engine's verdict itself is unchanged."""
    state_rules = {
        rule.id
        for rule in scheme.rules
        if rule.kind == "require" and _condition_fields(rule.when) == {"state"}
    }
    return any(f.rule_id in state_rules and f.status == "failed" for f in verdict.findings)


def _confirmation_steps(verdict: RuleVerdict) -> list[ConfirmationStep]:
    """Same facts as RuleVerdict.confirmations, keyed by rule id so an
    operator annotation can point at one without touching the verdict."""
    if verdict.verdict != "likely_eligible":
        return []
    return [
        ConfirmationStep(rule_id=f.rule_id, text=f.verify_hint)
        for f in verdict.findings
        if f.self_declared and f.status == "met" and f.verify_hint
    ]


def _reason_text(finding: RuleFinding) -> str:
    label = finding.rule_id.replace("-", " ")
    if finding.kind == "exclude":
        label = label.removeprefix("exclude ")
        if finding.status == "excluded":
            return f"An official exclusion applies — {label}."
        return f"Exclusion checked — {label} does not apply to you."
    if finding.status == "met":
        return f"Requirement met — {label}."
    return f"Requirement not met — {label}."


def _finding_reasons(verdict: RuleVerdict) -> list[VerifiedReason]:
    if verdict.verdict == "not_eligible":
        relevant = [f for f in verdict.findings if f.status in ("failed", "excluded")]
    else:
        relevant = [f for f in verdict.findings if f.status == "met"]
    return [
        VerifiedReason(
            text=_reason_text(f),
            citations=[
                VerifiedCitation(
                    chunk_id=f"rule:{verdict.scheme_id}:{f.rule_id}",
                    quote=f.clause,
                    section="exclusions" if f.status == "excluded" else "eligibility",
                    source_url=f.source_url,
                )
            ],
        )
        for f in relevant
    ]


def _packet_sections(doc: CorpusDoc, verdict: Verdict) -> dict:
    """Application packet inputs — only for verdicts a person can act on."""
    if verdict not in ENTITLED:
        return {}
    return {
        "application_modes": parse_application_modes(doc.sections.get("application", "")),
        "document_items": parse_document_items(doc.sections.get("documents", "")),
    }


class SchemeExplanation(BaseModel):
    scheme_id: str
    summary: str


class SummaryBatch(BaseModel):
    summaries: list[SchemeExplanation]


EXPLAIN_PROMPT = """You explain welfare-scheme eligibility verdicts in one kind sentence each.

The deterministic rules engine has already decided each verdict by checking the person's
facts against official scheme rules — you MUST NOT change, soften, or second-guess any
verdict, and you must not introduce any fact or number that is not given below.

Person's facts: {profile}

Verdicts to explain (scheme, verdict, rule findings):
{verdict_block}

For each scheme_id, write `summary`: ONE warm, plain-language sentence addressed to the
person as "you", faithfully reflecting the verdict and its decisive findings.
"""


def _llm_summaries(state: AgentState, verdicts: list[RuleVerdict]) -> dict[str, str]:
    # Escape hatch for exhausted free-tier quotas: skip the LLM entirely and
    # ship the deterministic template summaries without waiting out the
    # provider retry ladder.
    if os.environ.get("ADHIKAAR_TEMPLATE_SUMMARIES") == "1":
        return {}
    explain = [v for v in verdicts if v.verdict != "not_eligible"]
    if not explain:
        return {}
    block = "\n".join(
        f"- {v.scheme_id}: {v.verdict}; "
        + "; ".join(f"{f.rule_id}={f.status}" for f in v.findings)
        for v in explain
    )
    wanted = {v.scheme_id for v in explain}
    try:
        batch = generate_structured_resilient(
            EXPLAIN_PROMPT.format(
                # notes carries user-influenced free text — keep it out of the
                # explainer prompt so injected wording can't reach summaries.
                profile=state["profile"].model_dump_json(
                    exclude_none=True, exclude={"notes"}
                ),
                verdict_block=block,
            ),
            SummaryBatch,
        )
        return {s.scheme_id: s.summary for s in batch.summaries if s.scheme_id in wanted}
    except Exception:  # noqa: BLE001 — templates are the safe fallback
        logger.warning("explainer failed; using template summaries")
        return {}


def rules_assess_and_compose(state: AgentState) -> AgentState:
    profile = state["profile"]
    corpus = corpus_by_id()
    retrieved_schemes = {c.scheme_id for c in state.get("retrieved", [])}

    all_rules = load_all_rules()
    verdicts = [
        evaluate_scheme(scheme_rules, profile) for scheme_rules in all_rules.values()
    ]
    # need_more_info is shown only for schemes retrieval found on-topic — otherwise a
    # sparse profile would bury the user in questions about irrelevant schemes.
    verdicts = [
        v
        for v in verdicts
        if v.verdict != "need_more_info" or v.scheme_id in retrieved_schemes
    ]
    # State schemes for a state the person doesn't live in are not "not eligible"
    # news worth showing — and must never surface a "move state" near-miss.
    verdicts = [v for v in verdicts if not _is_out_of_state(all_rules[v.scheme_id], v)]

    summaries = _llm_summaries(state, verdicts)
    # not_eligible always uses its template by design; any other verdict
    # without an LLM summary means the explainer was unavailable.
    simplified = any(
        v.verdict != "not_eligible" and v.scheme_id not in summaries for v in verdicts
    )

    results = []
    for verdict in verdicts:
        doc = corpus[verdict.scheme_id]
        results.append(
            SchemeResult(
                scheme_id=verdict.scheme_id,
                scheme_name=doc.name,
                short_name=doc.short_name,
                verdict=verdict.verdict,
                summary=summaries.get(verdict.scheme_id)
                or TEMPLATE_SUMMARIES[verdict.verdict],
                reasons=_finding_reasons(verdict),
                missing_info=(
                    verdict.unknown_asks if verdict.verdict == "need_more_info" else []
                ),
                confirm_before_applying=(
                    verdict.confirmations
                    if verdict.verdict == "likely_eligible"
                    else []
                ),
                documents=doc.sections.get("documents", ""),
                document_guide_keys=guide_keys_for(doc.sections.get("documents", "")),
                how_to_apply=doc.sections.get("application", ""),
                page_url=doc.page_url,
                references=[r.model_dump() for r in doc.references],
                dropped_claims=0,
                near_miss=find_near_miss(
                    all_rules[verdict.scheme_id], verdict, profile
                ),
                **_packet_sections(doc, verdict.verdict),
                confirmations=_confirmation_steps(verdict),
            )
        )
    results.sort(key=lambda r: VERDICT_ORDER[r.verdict])
    return {
        "results": results,
        "assessments": [],
        "status": "ok",
        "explanations_simplified": simplified,
    }
