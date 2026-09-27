"""The proceed/ask decision is deterministic policy, not LLM whim."""

from unittest.mock import patch

from app.agent.nodes import build_profile
from app.agent.state import ProfileExtraction, UserProfile


def run_with_extraction(profile: UserProfile, says_enough: bool) -> str:
    extraction = ProfileExtraction(
        profile=profile, is_enough_to_assess=says_enough, clarifying_question="More?"
    )
    with patch("app.agent.nodes.generate_structured_resilient", return_value=extraction):
        return build_profile({"message": "x", "prior_profile": None})["status"]


def test_three_decisive_facts_override_model_hesitation():
    profile = UserProfile(age=40, has_bank_account=True, pays_income_tax=False)
    assert run_with_extraction(profile, says_enough=False) == "ok"


def test_location_and_gender_do_not_count_as_decisive():
    # gender="male" keeps this focused on the fact-counting policy: a woman would
    # now decisively reach MSSC (a gender-only scheme) and correctly proceed —
    # covered by test_gender_alone_reaches_mssc_entitlement below.
    profile = UserProfile(marital_status="widowed", gender="male", state="Bihar")
    assert run_with_extraction(profile, says_enough=False) == "need_info"


def test_gender_alone_reaches_mssc_entitlement():
    """Mahila Samman Savings Certificate is open to any woman — so stating only
    gender=female decisively reaches an entitlement, and abstaining would hide
    it. The gate proceeds (rules-informed), not the fact count."""
    profile = UserProfile(gender="female")
    assert run_with_extraction(profile, says_enough=False) == "ok"


def test_model_yes_is_respected_even_when_sparse():
    profile = UserProfile(age=62, occupation="farmer")
    assert run_with_extraction(profile, says_enough=True) == "ok"


def test_decisive_entitlement_overrides_sparse_fact_count():
    """daughter-9-boundary class: only two decisive facts, but the rules engine
    already reaches a full 'eligible' for Sukanya Samriddhi — abstaining here
    would hide an entitlement the person can act on today."""
    profile = UserProfile(gender="female", has_bank_account=True, daughter_age=9)
    assert run_with_extraction(profile, says_enough=False) == "ok"


def test_sparse_profile_without_entitlement_still_asks():
    """One decisive fact and no scheme decisively satisfied — keep asking.
    (occupation alone, not age: any stated age >=10 now reaches PMJDY, which is
    genuinely near-universal, so age would correctly proceed instead.)"""
    profile = UserProfile(occupation="teacher")
    assert run_with_extraction(profile, says_enough=False) == "need_info"
