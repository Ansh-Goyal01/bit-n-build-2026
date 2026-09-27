"""R1 — near-miss suggestions. A scheme is a *near miss* when exactly one
rule blocks it and, with that single blocker resolved, the person would be
eligible (or likely eligible). Deterministic — computed by the rules engine,
never an LLM."""

from types import SimpleNamespace
from unittest.mock import patch

from app.agent.rules_nodes import rules_assess_and_compose
from app.agent.state import UserProfile
from app.rules.engine import (
    Condition,
    Rule,
    SchemeRules,
    evaluate_scheme,
    find_near_miss,
)


def _require(rule_id: str, condition: Condition, **kwargs) -> Rule:
    return Rule(
        id=rule_id,
        kind="require",
        when=condition,
        clause=f"official clause for {rule_id}",
        source_url="https://example.gov.in/guidelines",
        ask=f"ask about {rule_id}?",
        **kwargs,
    )


def _exclude(rule_id: str, condition: Condition, **kwargs) -> Rule:
    return Rule(
        id=rule_id,
        kind="exclude",
        when=condition,
        clause=f"official exclusion for {rule_id}",
        source_url="https://example.gov.in/guidelines",
        ask=f"ask about {rule_id}?",
        **kwargs,
    )


def _scheme(*rules: Rule) -> SchemeRules:
    return SchemeRules(scheme_id="test-scheme", version="1", rules=list(rules))


AGE_18_PLUS = Condition(field="age", op="gte", value=18)
INCOME_CAP = Condition(field="annual_family_income_inr", op="lte", value=250_000)


def _near_miss_for(scheme: SchemeRules, profile: UserProfile):
    return find_near_miss(scheme, evaluate_scheme(scheme, profile), profile)


class TestSingleBlocker:
    def test_single_failed_require_is_a_near_miss(self):
        scheme = _scheme(_require("min-age", AGE_18_PLUS), _require("income-cap", INCOME_CAP))
        profile = UserProfile(age=45, annual_family_income_inr=400_000)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert near.rule_id == "income-cap"
        assert near.kind == "require"
        assert near.unlocked_verdict == "eligible"
        assert [(c.field, c.op, c.value) for c in near.conditions] == [
            ("annual_family_income_inr", "lte", 250_000)
        ]

    def test_single_triggered_exclude_is_a_near_miss(self):
        scheme = _scheme(
            _require("min-age", AGE_18_PLUS),
            _exclude("no-income-tax", Condition(field="pays_income_tax", op="eq", value=True)),
        )
        profile = UserProfile(age=30, pays_income_tax=True)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert near.rule_id == "no-income-tax"
        assert near.kind == "exclude"
        assert near.unlocked_verdict == "eligible"
        assert [(c.field, c.op, c.value) for c in near.conditions] == [
            ("pays_income_tax", "eq", True)
        ]

    def test_unlock_softens_to_likely_when_rest_is_self_declared(self):
        scheme = _scheme(
            _require(
                "bpl",
                Condition(field="has_bpl_card", op="eq", value=True),
                self_declared=True,
                verify_hint="Check the BPL list at your gram panchayat.",
            ),
            _require("income-cap", INCOME_CAP),
        )
        profile = UserProfile(has_bpl_card=True, annual_family_income_inr=400_000)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert near.rule_id == "income-cap"
        assert near.unlocked_verdict == "likely_eligible"


class TestNotANearMiss:
    def test_two_failed_rules_is_not_a_near_miss(self):
        scheme = _scheme(_require("min-age", AGE_18_PLUS), _require("income-cap", INCOME_CAP))
        profile = UserProfile(age=12, annual_family_income_inr=400_000)

        assert _near_miss_for(scheme, profile) is None

    def test_blocker_plus_unknown_is_not_a_near_miss(self):
        # Removing the blocker still leaves need_more_info — not a clean unlock.
        scheme = _scheme(_require("min-age", AGE_18_PLUS), _require("income-cap", INCOME_CAP))
        profile = UserProfile(annual_family_income_inr=400_000)  # age unknown

        assert _near_miss_for(scheme, profile) is None

    def test_eligible_scheme_has_no_near_miss(self):
        scheme = _scheme(_require("min-age", AGE_18_PLUS))
        profile = UserProfile(age=30)

        assert _near_miss_for(scheme, profile) is None

    def test_need_more_info_scheme_has_no_near_miss(self):
        scheme = _scheme(_require("min-age", AGE_18_PLUS))
        profile = UserProfile()

        assert _near_miss_for(scheme, profile) is None


class TestConditionExtraction:
    def test_failed_any_lists_every_failing_alternative(self):
        cond = Condition(
            any=[
                Condition(field="social_category", op="eq", value="sc"),
                Condition(field="social_category", op="eq", value="st"),
            ]
        )
        scheme = _scheme(_require("category", cond))
        profile = UserProfile(social_category="general")

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert [(c.field, c.value) for c in near.conditions] == [
            ("social_category", "sc"),
            ("social_category", "st"),
        ]

    def test_failed_all_lists_only_the_failing_leaves(self):
        cond = Condition(all=[AGE_18_PLUS, INCOME_CAP])
        scheme = _scheme(_require("combined", cond))
        profile = UserProfile(age=45, annual_family_income_inr=400_000)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert [(c.field, c.op) for c in near.conditions] == [
            ("annual_family_income_inr", "lte")
        ]

    def test_triggered_exclude_lists_the_leaves_that_hold(self):
        cond = Condition(
            any=[
                Condition(field="pays_income_tax", op="eq", value=True),
                Condition(field="receives_govt_pension_over_10k", op="eq", value=True),
            ]
        )
        scheme = _scheme(_exclude("exclude-taxpayer-or-pensioner", cond))
        profile = UserProfile(pays_income_tax=False, receives_govt_pension_over_10k=True)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert [(c.field, c.value) for c in near.conditions] == [
            ("receives_govt_pension_over_10k", True)
        ]

    def test_near_miss_carries_clause_source_and_ask(self):
        scheme = _scheme(_require("income-cap", INCOME_CAP))
        profile = UserProfile(annual_family_income_inr=400_000)

        near = _near_miss_for(scheme, profile)

        assert near is not None
        assert near.clause == "official clause for income-cap"
        assert near.source_url == "https://example.gov.in/guidelines"
        assert near.ask == "ask about income-cap?"


class TestPipelineWiring:
    def test_compose_attaches_near_miss_to_not_eligible_result(self):
        scheme = _scheme(_require("income-cap", INCOME_CAP))
        doc = SimpleNamespace(
            name="Test Scheme", short_name="TS", sections={}, page_url="", references=[]
        )
        state = {
            "profile": UserProfile(annual_family_income_inr=400_000),
            "retrieved": [],
        }
        with (
            patch(
                "app.agent.rules_nodes.load_all_rules",
                return_value={"test-scheme": scheme},
            ),
            patch(
                "app.agent.rules_nodes.corpus_by_id",
                return_value={"test-scheme": doc},
            ),
            patch("app.agent.rules_nodes._llm_summaries", return_value={}),
        ):
            out = rules_assess_and_compose(state)

        (result,) = out["results"]
        assert result.verdict == "not_eligible"
        assert result.near_miss is not None
        assert result.near_miss.rule_id == "income-cap"
        assert result.near_miss.unlocked_verdict == "eligible"
