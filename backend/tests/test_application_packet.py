"""Application packet: official application/documents text split into lines,
never rewritten — and carried only on verdicts a person can act on."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.agent.rules_nodes import rules_assess_and_compose
from app.agent.state import (
    ApplicationMode,
    ApplicationStep,
    ConfirmationStep,
    DocumentItem,
    SchemeResult,
    UserProfile,
)
from app.api.schemas import AssessResponse
from app.i18n import translate as tr
from app.ingestion.corpus import load_corpus
from app.rules.application import parse_application_modes, parse_document_items
from app.rules.engine import Condition, Rule, SchemeRules

CORPUS = {doc.scheme_id: doc for doc in load_corpus()}


def _source_lines(markdown: str) -> list[str]:
    return markdown.splitlines()


# --- parsing: the source-text invariant, over the whole corpus ---


@pytest.mark.parametrize("scheme_id", sorted(CORPUS))
def test_every_step_is_a_substring_of_one_source_line(scheme_id: str) -> None:
    source = CORPUS[scheme_id].sections.get("application", "")
    for mode in parse_application_modes(source):
        for step in mode.steps:
            assert any(step.text in line for line in _source_lines(source)), step.text


@pytest.mark.parametrize("scheme_id", sorted(CORPUS))
def test_every_document_line_is_a_substring_of_one_source_line(scheme_id: str) -> None:
    source = CORPUS[scheme_id].sections.get("documents", "")
    for item in parse_document_items(source):
        assert any(item.text in line for line in _source_lines(source)), item.text


def test_step_prefixes_are_stripped_and_modes_detected() -> None:
    modes = parse_application_modes(CORPUS["pm-kisan"].sections["application"])
    assert [m.mode for m in modes] == ["online", "csc"]
    online = modes[0]
    assert online.steps[0].kind == "step"
    assert online.steps[0].text.startswith("Visit the [PM-KISAN Portal]")
    assert not any(s.text.startswith(("**Step", "Step ")) for s in online.steps)
    assert "https://pmkisan.gov.in/" in online.links
    # "> **Know Your Status:** …" is a note, not a numbered step.
    assert online.steps[-1].kind == "note"


def test_list_style_application_and_offline_mode() -> None:
    modes = parse_application_modes(CORPUS["ignwps"].sections["application"])
    assert [m.mode for m in modes] == ["online", "offline"]
    assert all(s.kind == "step" for s in modes[1].steps)
    assert modes[1].steps[0].text.startswith("Individuals can submit")


def test_missing_application_section_yields_no_modes() -> None:
    assert parse_application_modes("") == []
    assert parse_application_modes(CORPUS["nswf"].sections.get("application", "")) == []


def test_text_before_first_mode_heading_is_kept_as_other_mode() -> None:
    modes = parse_application_modes("Apply at the office.\n\n### Application mode: Online\n\n- Visit")
    assert [m.mode for m in modes] == ["other", "online"]
    assert modes[0].steps[0].text == "Apply at the office."


def test_documents_split_into_groups_items_and_guide_keys() -> None:
    items = parse_document_items(CORPUS["pm-svanidhi"].sections["documents"])
    kinds = [i.kind for i in items]
    assert kinds[0] == "group"
    assert kinds.count("item") == 13
    aadhaar = next(i for i in items if i.text == "Aadhaar Card")
    assert aadhaar.kind == "item" and aadhaar.guide_key == "aadhaar"
    assert next(i for i in items if i.text == "PAN Card").guide_key is None


def test_long_bold_sentence_is_a_note_not_a_group() -> None:
    items = parse_document_items(CORPUS["apy"].sections["documents"])
    assert [i.kind for i in items] == ["note"]


def test_no_documents_section_yields_empty_list() -> None:
    assert parse_document_items("") == []
    assert "documents" not in CORPUS["ignwps"].sections


# --- composition: packet fields ride only on actionable verdicts ---

AGE_60 = Condition(field="age", op="gte", value=60)
BPL = Condition(field="has_bpl_card", op="eq", value=True)


def _compose(profile: UserProfile, rules: list[Rule]) -> SchemeResult:
    scheme = SchemeRules(scheme_id="test-scheme", version="t", rules=rules)
    doc = SimpleNamespace(
        name="Test Scheme",
        short_name="TS",
        sections={
            "application": "### Application mode: Offline\n\n- Submit the form at the office.",
            "documents": "1. Aadhaar Card\n1. BPL Card",
        },
        page_url="https://example.gov.in",
        references=[],
    )
    with (
        patch("app.agent.rules_nodes.load_all_rules", return_value={"test-scheme": scheme}),
        patch("app.agent.rules_nodes.corpus_by_id", return_value={"test-scheme": doc}),
        patch("app.agent.rules_nodes._llm_summaries", return_value={}),
    ):
        # Retrieved, so a need_more_info verdict is kept rather than filtered out.
        state = {"profile": profile, "retrieved": [SimpleNamespace(scheme_id="test-scheme")]}
        (result,) = rules_assess_and_compose(state)["results"]
    return result


def _rule(rule_id: str, when: Condition, self_declared: bool = False) -> Rule:
    return Rule(
        id=rule_id,
        kind="require",
        when=when,
        clause="clause",
        source_url="https://example.gov.in",
        ask="ask?",
        self_declared=self_declared,
        verify_hint="Confirm at the Gram Panchayat office." if self_declared else "",
    )


def test_eligible_verdict_carries_packet_fields() -> None:
    result = _compose(UserProfile(age=65), [_rule("age", AGE_60)])
    assert result.verdict == "eligible"
    assert result.application_modes[0].mode == "offline"
    assert [i.guide_key for i in result.document_items] == ["aadhaar", "bpl_card"]
    assert result.confirmations == []


def test_likely_eligible_verdict_carries_rule_keyed_confirmations() -> None:
    result = _compose(
        UserProfile(age=65, has_bpl_card=True),
        [_rule("age", AGE_60), _rule("bpl", BPL, self_declared=True)],
    )
    assert result.verdict == "likely_eligible"
    assert result.confirmations == [
        ConfirmationStep(rule_id="bpl", text="Confirm at the Gram Panchayat office.")
    ]
    assert result.confirm_before_applying == ["Confirm at the Gram Panchayat office."]


@pytest.mark.parametrize("profile", [UserProfile(age=50), UserProfile()])
def test_non_actionable_verdicts_carry_no_packet(profile: UserProfile) -> None:
    result = _compose(profile, [_rule("age", AGE_60)])
    assert result.verdict in ("not_eligible", "need_more_info")
    assert result.application_modes == []
    assert result.document_items == []


# --- translation: packet prose translated, structure invariant ---


class _MemoryCache(dict):
    set = dict.__setitem__


class _Wrap:
    name = "wrap"

    def translate_batch(self, texts: list[str], target: str) -> list[str]:
        return [f"[{target}]{t}" for t in texts]


def test_packet_prose_is_translated_but_structure_is_not(monkeypatch) -> None:
    monkeypatch.setattr(tr, "_provider", _Wrap())
    cache = _MemoryCache()
    monkeypatch.setattr(tr, "get_cache", lambda: cache)
    result = SchemeResult(
        scheme_id="s",
        scheme_name="Scheme",
        short_name="S",
        verdict="likely_eligible",
        summary="sum",
        reasons=[],
        missing_info=[],
        application_modes=[
            ApplicationMode(
                mode="online",
                steps=[ApplicationStep(kind="step", text="Visit the portal.")],
                links=["https://portal.gov.in"],
            )
        ],
        document_items=[DocumentItem(kind="item", text="Aadhaar Card", guide_key="aadhaar")],
        confirmations=[ConfirmationStep(rule_id="bpl", text="Confirm your BPL status.")],
    )
    response = AssessResponse(status="ok", profile=UserProfile(), results=[result])

    (out,) = tr.translate_response(response, "hi").results

    assert out.verdict == "likely_eligible"
    mode = out.application_modes[0]
    assert (mode.mode, mode.links) == ("online", ["https://portal.gov.in"])
    assert mode.steps[0].text == "[hi]Visit the portal."
    assert out.document_items[0].text == "[hi]Aadhaar Card"
    assert out.document_items[0].guide_key == "aadhaar"
    assert out.confirmations[0].rule_id == "bpl"
    assert out.confirmations[0].text == "[hi]Confirm your BPL status."
