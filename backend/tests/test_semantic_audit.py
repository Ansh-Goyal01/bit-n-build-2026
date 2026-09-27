"""Condition-semantics audit — pure logic tests (no LLM calls)."""

import pytest

from app.extraction.semantic_audit import (
    RuleAuditFinding,
    SchemeAuditResponse,
    _validate_response,
    flagged_rows,
    md_escape,
    render_condition,
)
from app.rules.engine import Condition, Rule


def _rule(rule_id: str, when: Condition) -> Rule:
    return Rule(
        id=rule_id,
        kind="require",
        when=when,
        clause="clause",
        source_url="https://example.gov",
        ask="?",
    )


def test_render_condition_leaf():
    cond = Condition(field="age", op="gte", value=18)
    assert render_condition(cond) == "age gte 18"


def test_render_condition_any_of_alternatives():
    cond = Condition(
        any=[
            Condition(field="social_category", op="eq", value="sc"),
            Condition(field="social_category", op="eq", value="st"),
        ]
    )
    assert render_condition(cond) == (
        "ANY OF [social_category eq 'sc'; social_category eq 'st']"
    )


def test_render_condition_nested_all_inside_any():
    cond = Condition(
        any=[
            Condition(field="has_bpl_card", op="eq", value=True),
            Condition(
                all=[
                    Condition(field="age", op="gte", value=18),
                    Condition(field="age", op="lte", value=40),
                ]
            ),
        ]
    )
    assert render_condition(cond) == (
        "ANY OF [has_bpl_card eq True; ALL OF [age gte 18; age lte 40]]"
    )


def test_validate_response_accepts_exact_rule_ids():
    rules = [_rule("a", Condition(field="age", op="gte", value=18))]
    response = SchemeAuditResponse(
        findings=[RuleAuditFinding(rule_id="a", verdict="faithful", reason="ok")]
    )
    _validate_response(response, rules)  # no raise


def test_validate_response_rejects_missing_or_extra_rules():
    rules = [_rule("a", Condition(field="age", op="gte", value=18))]
    response = SchemeAuditResponse(
        findings=[RuleAuditFinding(rule_id="b", verdict="faithful", reason="ok")]
    )
    with pytest.raises(ValueError, match="rule_id mismatch"):
        _validate_response(response, rules)


def test_validate_response_rejects_reasonless_mismatch():
    rules = [_rule("a", Condition(field="age", op="gte", value=18))]
    response = SchemeAuditResponse(
        findings=[
            RuleAuditFinding(
                rule_id="a", verdict="mismatch", mismatch_type="field-binding", reason="  "
            )
        ]
    )
    with pytest.raises(ValueError, match="needs a reason"):
        _validate_response(response, rules)


def test_flagged_rows_orders_false_entitlement_first():
    artifact = {
        "schemes": {
            "s-denial": [
                {
                    "rule_id": "r1",
                    "verdict": "mismatch",
                    "mismatch_type": "field-binding",
                    "failure_direction": "false_denial",
                    "reason": "fails closed",
                },
                {"rule_id": "r2", "verdict": "faithful", "mismatch_type": None,
                 "failure_direction": None, "reason": "ok"},
            ],
            "a-entitlement": [
                {
                    "rule_id": "r3",
                    "verdict": "mismatch",
                    "mismatch_type": "require-exclude-direction",
                    "failure_direction": "false_entitlement",
                    "reason": "fails open",
                },
            ],
        }
    }
    rows = flagged_rows(artifact)
    assert [r["rule_id"] for r in rows] == ["r3", "r1"]
    assert rows[0]["failure_direction"] == "false_entitlement"


def test_md_escape_neutralizes_table_pipes_and_newlines():
    assert md_escape("a | b\nc") == "a \\| b c"


def test_flagged_rows_empty_when_all_faithful():
    artifact = {
        "schemes": {
            "s": [
                {"rule_id": "r", "verdict": "faithful", "mismatch_type": None,
                 "failure_direction": None, "reason": "ok"}
            ]
        }
    }
    assert flagged_rows(artifact) == []
