"""Extraction output is normalized at the schema boundary, never trusted raw.

LLM extractors intermittently return 'BPL' as a social category or capitalized
enum values; a raw Literal would hard-fail the whole request (and, with disk-
cached completions, fail it deterministically forever). Invalid values mean
"not stated" (None) — the three-valued engine then asks instead of guessing.
"""

from app.agent.state import UserProfile


def test_valid_categories_are_lowercased():
    assert UserProfile(social_category="SC").social_category == "sc"
    assert UserProfile(gender="Female").gender == "female"
    assert UserProfile(marital_status="Widowed").marital_status == "widowed"
    assert UserProfile(area="Rural").area == "rural"
    assert UserProfile(house_type="Kutcha").house_type == "kutcha"


def test_bpl_is_not_a_social_category():
    profile = UserProfile(social_category="BPL", has_bpl_card=True)
    assert profile.social_category is None
    assert profile.has_bpl_card is True


def test_unknown_enum_values_mean_not_stated():
    assert UserProfile(marital_status="separated").marital_status is None
    assert UserProfile(area="semi-urban").area is None


def test_none_and_valid_values_pass_through():
    assert UserProfile().social_category is None
    assert UserProfile(social_category="obc").social_category == "obc"
