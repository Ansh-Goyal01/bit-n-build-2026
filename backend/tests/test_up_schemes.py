"""Uttar Pradesh state schemes: boundary values for every encoded threshold,
state-name normalisation, and the presentation rule that hides schemes for a
state the person doesn't live in (the engine's verdict itself is unchanged).

Every UP rule is also exercised in all three logic states by
test_rules.py::test_rule_three_states."""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agent.nodes import build_profile
from app.agent.rules_nodes import rules_assess_and_compose
from app.agent.state import ProfileExtraction, UserProfile
from app.agent.states import INDIAN_STATES, canonical_state
from app.rules.engine import evaluate_scheme
from app.rules.loader import load_all_rules

ALL_SCHEMES = load_all_rules()
UP_SCHEMES = ("upoaps", "wpup", "dpyup", "ksy", "mpss", "pmcup")
UP = "Uttar Pradesh"


def verdict(scheme_id: str, **facts) -> str:
    return evaluate_scheme(ALL_SCHEMES[scheme_id], UserProfile(**facts)).verdict


# --- every UP scheme is live, state-gated and human-verified ---


@pytest.mark.parametrize("scheme_id", UP_SCHEMES)
def test_up_scheme_requires_uttar_pradesh_as_a_self_declared_fact(scheme_id: str) -> None:
    scheme = ALL_SCHEMES[scheme_id]
    state_rules = [r for r in scheme.rules if r.when.field == "state"]
    assert len(state_rules) == 1
    rule = state_rules[0]
    assert (rule.kind, rule.when.op, rule.when.value) == ("require", "eq", UP)
    assert rule.self_declared and rule.verify_hint
    assert rule.when.value in INDIAN_STATES


@pytest.mark.parametrize("scheme_id", UP_SCHEMES)
def test_up_rules_are_human_verified(scheme_id: str) -> None:
    for rule in ALL_SCHEMES[scheme_id].rules:
        assert rule.review_status == "verified", rule.id
        assert rule.source_url == f"https://www.myscheme.gov.in/schemes/{scheme_id}"


# --- boundaries ---


def test_upoaps_age_and_income_edges_per_area() -> None:
    # has_bpl_card=False isolates the income path (an unknown card keeps it open).
    rural = {"state": UP, "area": "rural", "has_bpl_card": False}
    assert verdict("upoaps", age=59, annual_family_income_inr=40000, **rural) == "not_eligible"
    assert verdict("upoaps", age=60, annual_family_income_inr=46080, **rural) == "likely_eligible"
    assert verdict("upoaps", age=60, annual_family_income_inr=46081, **rural) == "not_eligible"
    urban = {"state": UP, "area": "urban", "age": 70, "has_bpl_card": False}
    assert verdict("upoaps", annual_family_income_inr=56460, **urban) == "likely_eligible"
    assert verdict("upoaps", annual_family_income_inr=56461, **urban) == "not_eligible"


def test_upoaps_bpl_card_is_an_alternative_to_the_income_limit() -> None:
    base = {"state": UP, "age": 65, "area": "urban", "annual_family_income_inr": 90000}
    assert verdict("upoaps", has_bpl_card=True, **base) == "likely_eligible"
    assert verdict("upoaps", has_bpl_card=False, **base) == "not_eligible"


def test_upoaps_unknown_area_with_income_under_both_caps_still_asks() -> None:
    # Area decides which cap applies — never assumed.
    assert verdict("upoaps", state=UP, age=65, annual_family_income_inr=40000) == "need_more_info"


WIDOW = {"state": UP, "marital_status": "widowed", "gender": "female"}


def test_wpup_age_and_income_edges() -> None:
    ok = {"annual_family_income_inr": 100000, "receives_other_govt_pension": False}
    assert verdict("wpup", age=17, **WIDOW, **ok) == "not_eligible"
    assert verdict("wpup", age=18, **WIDOW, **ok) == "likely_eligible"
    base = {"age": 45, "receives_other_govt_pension": False, **WIDOW}
    assert verdict("wpup", annual_family_income_inr=200000, **base) == "likely_eligible"
    assert verdict("wpup", annual_family_income_inr=200001, **base) == "not_eligible"


def test_wpup_other_government_pension_excludes() -> None:
    base = {"age": 45, "annual_family_income_inr": 50000, **WIDOW}
    assert verdict("wpup", receives_other_govt_pension=True, **base) == "not_eligible"
    assert verdict("wpup", **base) == "need_more_info"


def test_dpyup_disability_edge() -> None:
    base = {
        "state": UP,
        "age": 30,
        "area": "rural",
        "annual_family_income_inr": 30000,
        "receives_other_govt_pension": False,
    }
    assert verdict("dpyup", disability_percent=39, **base) == "not_eligible"
    assert verdict("dpyup", disability_percent=40, **base) == "likely_eligible"


def test_ksy_income_and_children_edges() -> None:
    base = {"state": UP, "daughter_age": 0}
    assert verdict("ksy", annual_family_income_inr=300000, number_of_children=2, **base) == "likely_eligible"
    assert verdict("ksy", annual_family_income_inr=300001, number_of_children=2, **base) == "not_eligible"
    assert verdict("ksy", annual_family_income_inr=200000, number_of_children=3, **base) == "not_eligible"


def test_mpss_income_edge_and_obc() -> None:
    base = {"state": UP, "is_post_matric_student": True, "social_category": "obc"}
    assert verdict("mpss", annual_family_income_inr=200000, **base) == "likely_eligible"
    assert verdict("mpss", annual_family_income_inr=200001, **base) == "not_eligible"
    sc = {**base, "social_category": "sc"}
    assert verdict("mpss", annual_family_income_inr=100000, **sc) == "not_eligible"


def test_pmcup_age_window_edges() -> None:
    base = {
        "state": UP,
        "social_category": "st",
        "is_student": True,
        "is_post_matric_student": False,
        "annual_family_income_inr": 250000,
    }
    assert verdict("pmcup", age=11, **base) == "not_eligible"
    assert verdict("pmcup", age=12, **base) == "likely_eligible"
    assert verdict("pmcup", age=20, **base) == "likely_eligible"
    assert verdict("pmcup", age=21, **base) == "not_eligible"


# --- state normalisation ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("UP", UP),
        ("U.P.", UP),
        ("uttar pradesh", UP),
        ("  Uttar   Pradesh ", UP),
        ("Orissa", "Odisha"),
        ("J&K", "Jammu and Kashmir"),
        ("Lucknow", None),
        ("", None),
    ],
)
def test_state_names_are_canonicalised(raw: str, expected: str | None) -> None:
    assert canonical_state(raw) == expected
    assert UserProfile(state=raw).state == expected


def test_backend_state_list_matches_the_wizard() -> None:
    wizard = Path(__file__).parents[2] / "frontend" / "lib" / "wizard.ts"
    block = re.search(r"INDIAN_STATES = \[(.*?)\] as const", wizard.read_text("utf-8"), re.S)
    assert block, "INDIAN_STATES not found in frontend/lib/wizard.ts"
    assert tuple(re.findall(r'"([^"]+)"', block.group(1))) == INDIAN_STATES


def test_extraction_normalises_state_and_keeps_new_fields() -> None:
    extraction = ProfileExtraction.model_validate(
        {
            "profile": {
                "state": "UP",
                "receives_other_govt_pension": False,
                "number_of_children": 2,
            },
            "is_enough_to_assess": True,
            "clarifying_question": "",
        }
    )
    with patch("app.agent.nodes.generate_structured_resilient", return_value=extraction):
        profile = build_profile({"message": "x", "prior_profile": None})["profile"]
    assert profile.state == UP
    assert profile.receives_other_govt_pension is False
    assert profile.number_of_children == 2


# --- presentation: out-of-state schemes are left out ---


def _result_ids(profile: UserProfile) -> set[str]:
    retrieved = [type("Chunk", (), {"scheme_id": s})() for s in UP_SCHEMES]
    with patch.dict("os.environ", {"ADHIKAAR_TEMPLATE_SUMMARIES": "1"}):
        out = rules_assess_and_compose({"profile": profile, "retrieved": retrieved})
    return {r.scheme_id for r in out["results"]}


WIDOW_FACTS = {
    "marital_status": "widowed",
    "gender": "female",
    "age": 62,
    "annual_family_income_inr": 40000,
    "area": "rural",
    "receives_other_govt_pension": False,
    "has_bpl_card": True,
}


def test_up_schemes_hidden_for_a_person_in_another_state() -> None:
    ids = _result_ids(UserProfile(state="Bihar", **WIDOW_FACTS))
    assert not ids & set(UP_SCHEMES)
    assert "ignwps" in ids  # central schemes are unaffected


def test_up_schemes_shown_for_a_person_in_uttar_pradesh() -> None:
    ids = _result_ids(UserProfile(state=UP, **WIDOW_FACTS))
    assert {"wpup", "upoaps"} <= ids


def test_unknown_state_keeps_retrieved_up_schemes_as_questions() -> None:
    profile = UserProfile(**WIDOW_FACTS)
    with patch.dict("os.environ", {"ADHIKAAR_TEMPLATE_SUMMARIES": "1"}):
        out = rules_assess_and_compose(
            {"profile": profile, "retrieved": [type("C", (), {"scheme_id": "wpup"})()]}
        )
    wpup = next(r for r in out["results"] if r.scheme_id == "wpup")
    assert wpup.verdict == "need_more_info"
    assert any("Uttar Pradesh" in ask for ask in wpup.missing_info)
