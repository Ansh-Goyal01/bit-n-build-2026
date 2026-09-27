"""Extraction pipeline: drafts are validated against the closed field
vocabulary and quarantined in rules/proposed/ — never in the live rules dir."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.extraction.propose import (
    PROPOSED_DIR,
    ConditionDraft,
    ExtractionOutput,
    RuleDraft,
    SchemeProposal,
    compose_or_groups,
    profile_rule_fields,
    propose_rules,
    validate_draft,
    vocabulary_field_names,
    write_proposal,
)
from app.ingestion.models import CorpusDoc
from app.rules.engine import Condition, Rule


def _require(rule_id: str, field: str, op: str, value) -> Rule:
    return Rule(
        id=rule_id,
        kind="require",
        when=Condition(field=field, op=op, value=value),
        clause=f"clause for {rule_id}",
        source_url="https://example.gov.in",
        ask="?",
        review_status="proposed",
    )


def test_same_field_eq_requires_merge_into_one_any_of():
    """The pm-daksh bug: SC AND OBC AND EWS (impossible) → OR of the three."""
    rules = [
        _require("sc", "social_category", "eq", "sc"),
        _require("obc", "social_category", "eq", "obc"),
        _require("ews", "social_category", "eq", "general"),
    ]
    composed = compose_or_groups(rules)
    assert len(composed) == 1
    merged = composed[0]
    assert merged.when.any is not None
    assert {leaf.value for leaf in merged.when.any} == {"sc", "obc", "general"}
    assert "AUTO-COMPOSED" in merged.notes_for_reviewer


def test_age_range_gte_plus_lte_is_not_merged():
    """Different ops on one field are a RANGE (AND), never an OR."""
    rules = [
        _require("age-min", "age", "gte", 18),
        _require("age-max", "age", "lte", 40),
    ]
    composed = compose_or_groups(rules)
    assert len(composed) == 2
    assert all(r.when.any is None for r in composed)


def test_income_bands_same_op_merge_to_any_of():
    """EWS/LIG/MIG income caps are alternative bands, not additive."""
    rules = [
        _require("ews", "annual_family_income_inr", "lte", 300000),
        _require("lig", "annual_family_income_inr", "lte", 600000),
    ]
    composed = compose_or_groups(rules)
    assert len(composed) == 1
    assert {leaf.value for leaf in composed[0].when.any} == {300000, 600000}


def test_single_require_is_untouched():
    rules = [_require("solo", "age", "gte", 18)]
    composed = compose_or_groups(rules)
    assert len(composed) == 1
    assert composed[0].id == "solo"
    assert composed[0].when.any is None


def test_excludes_are_not_merged():
    """Only require rules compose; excludes each disqualify independently."""
    excl = [
        Rule(
            id=f"ex{i}", kind="exclude",
            when=Condition(field="occupation", op="eq", value=v),
            clause="c", source_url="https://x.gov.in", ask="?", review_status="proposed",
        )
        for i, v in enumerate(["meat", "crops"])
    ]
    composed = compose_or_groups(excl)
    assert len(composed) == 2


def test_compose_preserves_non_mergeable_ordering():
    rules = [
        _require("a", "social_category", "eq", "sc"),
        _require("b", "age", "gte", 18),
        _require("c", "social_category", "eq", "obc"),
    ]
    composed = compose_or_groups(rules)
    # the two social_category rules merge; age stays as its own rule
    ids_and_fields = [(r.when.field, bool(r.when.any)) for r in composed]
    assert ("age", False) in ids_and_fields
    assert any(r.when.any and r.when.any[0].field == "social_category" for r in composed)


def test_prompt_vocabulary_matches_the_profile_schema_exactly():
    """If someone adds a profile field, the extractor prompt must learn it —
    and the prompt must never promise a field the engine can't test."""
    assert vocabulary_field_names() == profile_rule_fields()


def test_valid_draft_promotes_to_engine_rule_with_proposed_status():
    draft = RuleDraft(
        id="age-at-least-18",
        kind="require",
        when=ConditionDraft(field="age", op="gte", value=18),
        clause="The minimum age of joining is 18 years.",
        ask="What is your age?",
    )
    rule = validate_draft(draft, "https://www.myscheme.gov.in/schemes/x")
    assert rule.review_status == "proposed"
    assert rule.when.field == "age"


def test_list_valued_leaf_expands_to_any_of():
    """Models sometimes collapse 'SC or ST' into one leaf with a list value
    instead of an any_of of two leaves — expand rather than reject it."""
    draft = RuleDraft(
        id="sc-or-st",
        kind="require",
        when=ConditionDraft(field="social_category", op="eq", value=["sc", "st"]),
        clause="The applicant must belong to SC or ST category.",
        ask="Do you belong to SC or ST?",
    )
    rule = validate_draft(draft, "https://example.gov.in")
    assert rule.when.any is not None
    assert {c.value for c in rule.when.any} == {"sc", "st"}


def test_unknown_field_draft_is_rejected():
    draft = RuleDraft(
        id="owns-livestock",
        kind="require",
        when=ConditionDraft(field="owns_livestock", op="eq", value=True),
        clause="The applicant should own livestock.",
        ask="Do you own livestock?",
    )
    with pytest.raises(ValidationError):
        validate_draft(draft, "https://example.gov.in")


def _doc() -> CorpusDoc:
    return CorpusDoc(
        scheme_id="test-scheme",
        short_name="TS",
        name="Test Scheme",
        category="test",
        level="Central",
        ministry="Ministry of Testing",
        page_url="https://www.myscheme.gov.in/schemes/test-scheme",
        references=[],
        fetched_at="2026-07-13",
        sections={"eligibility": "The applicant must be at least 18 years of age."},
    )


def test_propose_rules_splits_valid_and_invalid_drafts():
    output = ExtractionOutput(
        rules=[
            RuleDraft(
                id="age-at-least-18",
                kind="require",
                when=ConditionDraft(field="age", op="gte", value=18),
                clause="The applicant must be at least 18 years of age.",
                ask="What is your age?",
            ),
            RuleDraft(
                id="bad-field",
                kind="require",
                when=ConditionDraft(field="not_a_field", op="eq", value=True),
                clause="Nonsense.",
                ask="?",
            ),
        ]
    )
    with patch("app.extraction.propose.generate_structured_resilient", return_value=output):
        proposal = propose_rules(_doc())
    assert [r.id for r in proposal.rules] == ["age-at-least-18"]
    assert proposal.rules[0].source_url == "https://www.myscheme.gov.in/schemes/test-scheme"
    assert len(proposal.rejected_drafts) == 1
    assert proposal.rejected_drafts[0]["draft"]["id"] == "bad-field"


def test_write_proposal_lands_in_proposed_dir_only(tmp_path, monkeypatch):
    monkeypatch.setattr("app.extraction.propose.PROPOSED_DIR", tmp_path / "proposed")
    proposal = SchemeProposal(
        scheme_id="test-scheme",
        scheme_name="Test Scheme",
        extracted_at="2026-07-13",
        source_url="https://example.gov.in",
        rules=[],
        rejected_drafts=[],
        blocked_rules=[],
        simplifications=["Enrollment windows are not modeled."],
    )
    out = write_proposal(proposal)
    assert out.parent.name == "proposed"
    assert "awaiting-human-review" in out.read_text(encoding="utf-8")
    # the engine's live directory is untouched by construction
    assert "schemes" not in str(out.parent)


def test_proposed_dir_is_not_the_live_rules_dir():
    from app.rules.loader import SCHEMES_DIR

    assert PROPOSED_DIR != SCHEMES_DIR
    assert PROPOSED_DIR.name == "proposed"
