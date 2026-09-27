"""Every rule in the repository is exercised in all three logic states, plus
hand-written boundary tests for the verdict composition."""

from collections import defaultdict
from typing import get_args

import pytest

from app.agent.state import UserProfile
from app.agent.states import INDIAN_STATES
from app.rules.engine import Condition, Rule, evaluate_scheme
from app.rules.loader import load_all_rules

ALL_SCHEMES = load_all_rules()
ALL_RULES = [
    (scheme_id, rule) for scheme_id, scheme in ALL_SCHEMES.items() for rule in scheme.rules
]

# Valid-but-different values for known Literal-typed fields, keyed by the rule's
# target value. Any value not listed here (free-text fields, or a Literal value
# we haven't seen yet) falls back to a guaranteed-different sentinel string —
# the exact alternate doesn't matter for a not-satisfied probe, only that it differs.
ALT_LITERAL = {
    "widowed": "single",
    "female": "male",
    "male": "female",
    "other": "female",
    "rural": "urban",
    "kutcha": "pucca",
    "sc": "obc",
    "obc": "sc",
    "st": "sc",
    "minority": "general",
    "general": "sc",
}


def _literal_members(field: str) -> tuple:
    """Allowed values of a Literal-typed profile field, else (). `state` is a
    closed set too — its validator turns unknown names into None — so it
    uses the canonical state list."""
    if field == "state":
        return INDIAN_STATES
    for arg in get_args(UserProfile.model_fields[field].annotation):
        members = get_args(arg)
        if members:
            return members
    return ()


def _alternate(field: str, avoid: set) -> str:
    """A valid value for `field` that is not in `avoid`. For a Literal field
    that means a real member outside the set (so it evaluates False, not
    unknown); for free-text a guaranteed-different sentinel."""
    for member in _literal_members(field):
        if member not in avoid:
            return member
    # ALT_LITERAL covers the common single-value case; sentinel otherwise.
    single = next(iter(avoid))
    return ALT_LITERAL.get(single, f"not-{single}")


def _different_value(field: str, value: bool | int | str) -> bool | int | str:
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return _alternate(field, {value})
    return value + 1


def _leaf_updates(condition: Condition, satisfy: bool) -> dict:
    field, value = condition.field, condition.value
    match condition.op:
        case "eq":
            return {field: value if satisfy else _different_value(field, value)}
        case "ne":
            # holds (True) means actual != value: satisfy -> anything else,
            # not-satisfy -> exactly value. ne/None is untestable (can never
            # reach "failed" — see NOTES 2026-07-13) and must not reach here.
            if value is None:
                raise AssertionError("ne with value=None has no failing state — fix the rule, not this helper")
            return {field: _different_value(field, value) if satisfy else value}
        case "gte":
            return {field: value if satisfy else value - 1}
        case "lte":
            return {field: value if satisfy else value + 1}
        case "lt":
            return {field: value - 1 if satisfy else value}
        case "gt":
            return {field: value + 1 if satisfy else value}
    raise AssertionError(f"unhandled op {condition.op}")


def _collect_leaves(condition: Condition) -> list[Condition]:
    if condition.any is not None or condition.all is not None:
        return [
            leaf
            for child in (condition.any or condition.all)
            for leaf in _collect_leaves(child)
        ]
    return [condition]


def _fail_any(leaves: list[Condition]) -> dict:
    """One value per field that makes every leaf false. Same-field eq leaves
    (an OR over one field, e.g. disability categories) need a single value
    outside the whole set, not the per-leaf alternate."""
    eq_by_field: dict[str, set] = defaultdict(set)
    updates: dict = {}
    for leaf in leaves:
        if leaf.field is not None and leaf.op == "eq" and isinstance(leaf.value, str):
            eq_by_field[leaf.field].add(leaf.value)
        else:
            updates.update(_leaf_updates(leaf, False))
    for field, avoid in eq_by_field.items():
        updates[field] = _alternate(field, avoid)
    return updates


def _satisfy_updates(condition: Condition) -> dict:
    if condition.any is not None:
        return _satisfy_updates(condition.any[0])
    if condition.all is not None:
        updates: dict = {}
        for child in condition.all:
            updates.update(_satisfy_updates(child))
        return updates
    return _leaf_updates(condition, True)


def _falsify_updates(condition: Condition) -> dict:
    if condition.any is not None:
        # Every leaf false makes any combinator tree false, whatever its shape
        # (nested any/all included — e.g. pm-daksh's income rule).
        return _fail_any(_collect_leaves(condition))
    if condition.all is not None:
        # One child false is enough; keep the rest satisfied so the test
        # isolates the "at least one requirement fails" path.
        updates = _satisfy_updates(condition)
        updates.update(_falsify_updates(condition.all[0]))
        return updates
    return _leaf_updates(condition, False)


def profile_for(condition: Condition, satisfy: bool) -> UserProfile:
    if satisfy:
        return UserProfile(**_satisfy_updates(condition))
    return UserProfile(**_falsify_updates(condition))


@pytest.mark.parametrize(
    ("scheme_id", "rule"), ALL_RULES, ids=[f"{s}:{r.id}" for s, r in ALL_RULES]
)
def test_rule_three_states(scheme_id: str, rule: Rule):
    scheme = ALL_SCHEMES[scheme_id]

    def status_of(profile: UserProfile) -> str:
        verdict = evaluate_scheme(scheme, profile)
        return next(f.status for f in verdict.findings if f.rule_id == rule.id)

    holds = status_of(profile_for(rule.when, satisfy=True))
    fails = status_of(profile_for(rule.when, satisfy=False))
    unknown = status_of(UserProfile())

    if rule.kind == "require":
        assert (holds, fails) == ("met", "failed")
    else:
        assert (holds, fails) == ("excluded", "met")
    assert unknown == "unknown"


# --- verdict composition & boundaries ---


def verdict(scheme_id: str, **facts) -> str:
    return evaluate_scheme(ALL_SCHEMES[scheme_id], UserProfile(**facts)).verdict


def test_no_scheme_is_eligible_for_an_empty_profile():
    """Core safety invariant: with nothing stated, no scheme may assert an
    entitlement. Every scheme must resolve to need_more_info or not_eligible."""
    empty = UserProfile()
    leaked = [
        sid
        for sid, scheme in ALL_SCHEMES.items()
        if evaluate_scheme(scheme, empty).verdict in ("eligible", "likely_eligible")
    ]
    assert not leaked, f"schemes eligible for empty profile: {leaked}"


def test_every_scheme_has_at_least_one_require_rule():
    """No all-exclusion scheme (which would be a universal 'yes')."""
    missing = [
        sid
        for sid, scheme in ALL_SCHEMES.items()
        if not any(rule.kind == "require" for rule in scheme.rules)
    ]
    assert not missing, f"schemes with no require rule: {missing}"


def test_nfbs_needs_both_breadwinner_death_and_bpl():
    assert verdict("nfbs", bereavement_event=True, has_bpl_card=True) == "likely_eligible"
    assert verdict("nfbs", bereavement_event=False, has_bpl_card=True) == "not_eligible"
    assert verdict("nfbs", bereavement_event=True) == "need_more_info"  # BPL unknown
    assert verdict("nfbs") == "need_more_info"


def test_vdcspds_needs_age_and_a_national_trust_act_category():
    assert verdict("vdcspds", age=15, disability_type="autism") == "eligible"
    assert verdict("vdcspds", age=15, disability_type="cerebral_palsy") == "eligible"
    # "other" is a certified disability outside the four NT-Act categories.
    assert verdict("vdcspds", age=15, disability_type="other") == "not_eligible"
    assert verdict("vdcspds", age=8, disability_type="autism") == "not_eligible"
    assert verdict("vdcspds", age=15) == "need_more_info"  # category unknown


def test_ignwps_age_window_boundaries():
    base = {"marital_status": "widowed", "gender": "female", "has_bpl_card": True}
    assert verdict("ignwps", age=39, **base) == "not_eligible"
    assert verdict("ignwps", age=40, **base) == "likely_eligible"  # BPL is self-declared
    assert verdict("ignwps", age=79, **base) == "likely_eligible"
    assert verdict("ignwps", age=80, **base) == "not_eligible"


def test_pmjjby_upper_boundary_catches_the_llm_false_positive():
    # The documented Phase-1 failure: LLM said "eligible" for a 62-year-old.
    assert verdict("pmjjby", age=62, has_bank_account=True) == "not_eligible"
    assert verdict("pmjjby", age=50, has_bank_account=True) == "eligible"
    assert verdict("pmjjby", age=51, has_bank_account=True) == "not_eligible"


def test_pm_kisan_taxpayer_exclusion_beats_landholding():
    assert (
        verdict(
            "pm-kisan",
            is_farmer_with_land=True,
            pays_income_tax=True,
            family_member_in_govt_service=False,
            receives_govt_pension_over_10k=False,
        )
        == "not_eligible"
    )


def test_pm_kisan_all_clear_is_eligible():
    assert (
        verdict(
            "pm-kisan",
            is_farmer_with_land=True,
            pays_income_tax=False,
            family_member_in_govt_service=False,
            receives_govt_pension_over_10k=False,
            holds_constitutional_or_political_post=False,
            is_practicing_registered_professional=False,
        )
        == "eligible"
    )


def test_conditional_verdicts_carry_concrete_confirmation_steps():
    """'Likely eligible' must always tell the person exactly what to confirm
    and where — every decisive self-declared rule ships a verify_hint."""
    verdict = evaluate_scheme(
        ALL_SCHEMES["nsap-ignoaps"], UserProfile(age=65, has_bpl_card=True)
    )
    assert verdict.verdict == "likely_eligible"
    assert verdict.confirmations, "conditional verdict without a confirmation step"
    assert "BPL list" in verdict.confirmations[0]
    assert "Gram Panchayat" in verdict.confirmations[0]


def test_every_self_declared_rule_has_a_verify_hint():
    missing = [
        f"{scheme_id}:{rule.id}"
        for scheme_id, rule in ALL_RULES
        if rule.self_declared and not rule.verify_hint.strip()
    ]
    assert not missing, f"self_declared rules without verify_hint: {missing}"


def test_pm_kisan_practicing_professional_family_is_excluded():
    assert (
        verdict(
            "pm-kisan",
            is_farmer_with_land=True,
            is_practicing_registered_professional=True,
        )
        == "not_eligible"
    )


def test_pm_kisan_political_post_family_is_excluded():
    assert (
        verdict(
            "pm-kisan",
            is_farmer_with_land=True,
            holds_constitutional_or_political_post=True,
        )
        == "not_eligible"
    )


def test_apy_taxpayer_excluded_despite_age_and_account():
    assert verdict("apy", age=30, has_bank_account=True, pays_income_tax=True) == "not_eligible"
    assert verdict("apy", age=30, has_bank_account=True, pays_income_tax=False) == "eligible"


def test_sukanya_samriddhi_under_ten_only():
    assert verdict("sukanya-samriddhi", daughter_age=9) == "eligible"
    assert verdict("sukanya-samriddhi", daughter_age=10) == "not_eligible"


def test_pmuy_male_applicant_not_eligible():
    assert verdict("pmuy", gender="male", age=30, has_bpl_card=True, has_lpg_connection=False) == "not_eligible"


def test_pmegp_low_income_adult_is_not_denied():
    """Regression for the removed viii-standard rule: it bound the clause's
    PROJECT COST to family income and flattened its conditional into an income
    floor, denying everyone under ₹5 lakh. Low income must never deny PMEGP."""
    assert verdict("pmegp", age=45, occupation="farmer", annual_family_income_inr=80000) == "eligible"
    assert verdict("pmegp", age=17, occupation="farmer", annual_family_income_inr=80000) == "not_eligible"


def test_missing_fact_yields_need_more_info_with_ask():
    result = evaluate_scheme(
        ALL_SCHEMES["nsap-ignoaps"], UserProfile(age=65)  # BPL status unknown
    )
    assert result.verdict == "need_more_info"
    assert any("BPL" in ask for ask in result.unknown_asks)


def test_bpl_pass_softens_to_likely_eligible():
    assert verdict("nsap-ignoaps", age=65, has_bpl_card=True) == "likely_eligible"
