"""Deterministic eligibility engine — three-valued logic over typed facts.

Every rule is one clause of official scheme text made executable:
- `require` rules must hold; `exclude` rules must not.
- A rule over a missing fact evaluates to *unknown* — never guessed. Unknowns
  surface as questions, and a scheme with unknowns yields `need_more_info`.
- `self_declared` marks facts the state ultimately verifies (e.g. BPL lists):
  if such a rule is decisive, `eligible` is softened to `likely_eligible`.
"""

from typing import Literal

from pydantic import BaseModel, model_validator

from app.agent.state import NearMiss, NearMissCondition, Op, UserProfile, Verdict

RuleStatus = Literal["met", "failed", "excluded", "unknown"]


class Condition(BaseModel):
    """A leaf comparison on one profile field, or an any/all combinator."""

    field: str | None = None
    op: Op | None = None
    value: bool | int | str | None = None
    any: list["Condition"] | None = None
    all: list["Condition"] | None = None

    @model_validator(mode="after")
    def _exactly_one_form(self) -> "Condition":
        forms = sum([self.field is not None, self.any is not None, self.all is not None])
        if forms != 1:
            raise ValueError("condition must be exactly one of: leaf(field/op/value), any, all")
        if self.field is not None:
            if self.op is None:
                raise ValueError(f"leaf condition on {self.field!r} needs an op")
            if self.field not in UserProfile.model_fields:
                raise ValueError(f"unknown profile field {self.field!r}")
        return self


def _compare(actual: bool | int | str, op: Op, value: bool | int | str) -> bool:
    match op:
        case "eq":
            return actual == value
        case "ne":
            return actual != value
        case "gt":
            return actual > value
        case "gte":
            return actual >= value
        case "lt":
            return actual < value
        case "lte":
            return actual <= value


def evaluate_condition(condition: Condition, profile: UserProfile) -> bool | None:
    """Three-valued: True, False, or None (a needed fact is missing)."""
    if condition.any is not None:
        results = [evaluate_condition(c, profile) for c in condition.any]
        if any(r is True for r in results):
            return True
        return None if any(r is None for r in results) else False
    if condition.all is not None:
        results = [evaluate_condition(c, profile) for c in condition.all]
        if any(r is False for r in results):
            return False
        return None if any(r is None for r in results) else True

    actual = getattr(profile, condition.field)
    if actual is None:
        return None
    return _compare(actual, condition.op, condition.value)


class Rule(BaseModel):
    id: str
    kind: Literal["require", "exclude"]
    when: Condition
    clause: str  # the official text this rule encodes, verbatim or tightly quoted
    source_url: str
    ask: str  # plain-language question to resolve an unknown
    self_declared: bool = False
    # For self_declared rules: where/how the person can confirm the fact the
    # state will verify (office, portal, helpline). Shown on conditional
    # verdicts so "likely eligible" always comes with a concrete next step.
    verify_hint: str = ""
    # Human verification state, versioned with the rule itself:
    # proposed = LLM-drafted, lives only in rules/proposed/ (never loaded by
    # the engine); encoded = machine-encoded + unit-tested; verified = a human
    # read the rule beside its source clause and certified it. Only the signer
    # moves a rule forward.
    review_status: Literal["proposed", "encoded", "verified"] = "encoded"
    # Free-text flag for the human reviewer (e.g. auto-composed OR groups the
    # signer should confirm). Review metadata only; the engine ignores it.
    notes_for_reviewer: str = ""


class SchemeRules(BaseModel):
    scheme_id: str
    version: str
    rules: list[Rule]
    # Honest omissions: criteria in the official text that the rules do not yet
    # encode. Surfaced on the sign-off checklist and the site's limitations page.
    simplifications: list[str] = []


class RuleFinding(BaseModel):
    rule_id: str
    kind: Literal["require", "exclude"]
    status: RuleStatus
    clause: str
    source_url: str
    ask: str
    self_declared: bool
    verify_hint: str = ""


class RuleVerdict(BaseModel):
    scheme_id: str
    verdict: Verdict
    findings: list[RuleFinding]

    @property
    def unknown_asks(self) -> list[str]:
        return [f.ask for f in self.findings if f.status == "unknown"]

    @property
    def confirmations(self) -> list[str]:
        """For conditional verdicts: the self-declared facts this verdict rests
        on, phrased as concrete verification steps (where / how to confirm)."""
        return [
            finding.verify_hint
            for finding in self.findings
            if finding.self_declared and finding.status == "met" and finding.verify_hint
        ]


def _blocking_leaves(
    condition: Condition, profile: UserProfile, blocking: bool
) -> list[NearMissCondition]:
    """Leaves that decide the blocker. For a failed require (`blocking=False`)
    these are the leaves evaluating False — what the person doesn't satisfy.
    For a triggered exclude (`blocking=True`) the leaves evaluating True —
    what pulls them into the exclusion."""
    if condition.any is not None or condition.all is not None:
        return [
            leaf
            for child in (condition.any or condition.all or [])
            for leaf in _blocking_leaves(child, profile, blocking)
        ]
    if evaluate_condition(condition, profile) is blocking:
        return [
            NearMissCondition(field=condition.field, op=condition.op, value=condition.value)
        ]
    return []


def find_near_miss(
    scheme: SchemeRules, verdict: "RuleVerdict", profile: UserProfile
) -> NearMiss | None:
    """A near miss is a not_eligible verdict with exactly one failed/excluded
    rule where re-evaluating WITHOUT that rule yields eligible or
    likely_eligible — i.e. one blocker away, nothing else missing."""
    if verdict.verdict != "not_eligible":
        return None
    blockers = [f for f in verdict.findings if f.status in ("failed", "excluded")]
    if len(blockers) != 1:
        return None
    blocker = blockers[0]

    remaining = SchemeRules(
        scheme_id=scheme.scheme_id,
        version=scheme.version,
        rules=[r for r in scheme.rules if r.id != blocker.rule_id],
    )
    unlocked = evaluate_scheme(remaining, profile).verdict
    if unlocked not in ("eligible", "likely_eligible"):
        return None

    rule = next(r for r in scheme.rules if r.id == blocker.rule_id)
    return NearMiss(
        rule_id=rule.id,
        kind=rule.kind,
        clause=rule.clause,
        source_url=rule.source_url,
        ask=rule.ask,
        unlocked_verdict=unlocked,
        conditions=_blocking_leaves(rule.when, profile, blocking=rule.kind == "exclude"),
    )


def _rule_status(rule: Rule, profile: UserProfile) -> RuleStatus:
    holds = evaluate_condition(rule.when, profile)
    if holds is None:
        return "unknown"
    if rule.kind == "require":
        return "met" if holds else "failed"
    return "excluded" if holds else "met"


def evaluate_scheme(scheme: SchemeRules, profile: UserProfile) -> RuleVerdict:
    findings = [
        RuleFinding(
            rule_id=rule.id,
            kind=rule.kind,
            status=_rule_status(rule, profile),
            clause=rule.clause,
            source_url=rule.source_url,
            ask=rule.ask,
            self_declared=rule.self_declared,
            verify_hint=rule.verify_hint,
        )
        for rule in scheme.rules
    ]

    if any(f.status in ("failed", "excluded") for f in findings):
        verdict: Verdict = "not_eligible"
    elif any(f.status == "unknown" for f in findings):
        verdict = "need_more_info"
    elif any(f.self_declared for f in findings):
        verdict = "likely_eligible"
    else:
        verdict = "eligible"
    return RuleVerdict(scheme_id=scheme.scheme_id, verdict=verdict, findings=findings)
