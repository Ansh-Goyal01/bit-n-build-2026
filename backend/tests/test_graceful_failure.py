"""When both LLMs fail, the rules-only path still returns every verdict and
application packet — only the one-line summaries fall back to templates, and
the response says so (explanations_simplified) so the UI can show it."""

from unittest.mock import patch

from app.agent.rules_nodes import TEMPLATE_SUMMARIES, rules_assess_and_compose
from app.agent.state import UserProfile

WIDOW = UserProfile(
    state="Uttar Pradesh",
    marital_status="widowed",
    gender="female",
    age=62,
    area="rural",
    annual_family_income_inr=40000,
    has_bpl_card=True,
    has_bank_account=True,
    receives_other_govt_pension=False,
)


def _run(llm_side_effect=None, llm_return=None) -> dict:
    with patch(
        "app.agent.rules_nodes.generate_structured_resilient",
        side_effect=llm_side_effect,
        return_value=llm_return,
    ):
        return rules_assess_and_compose({"profile": WIDOW, "retrieved": []})


def _llm_ok(prompt, schema):
    # Echo a summary for every scheme the explainer is asked about.
    ids = [line[2:].split(":")[0] for line in prompt.splitlines() if line.startswith("- ")]
    return schema(summaries=[{"scheme_id": i, "summary": f"LLM summary for {i}."} for i in ids])


def test_llm_outage_keeps_verdicts_and_packets_and_flags_simplified() -> None:
    healthy = _run(llm_side_effect=_llm_ok)
    outage = _run(llm_side_effect=RuntimeError("both providers down"))

    assert healthy["explanations_simplified"] is False
    assert outage["explanations_simplified"] is True

    def shape(state: dict) -> list:
        return [
            (r.scheme_id, r.verdict, r.application_modes, r.document_items, r.confirmations)
            for r in state["results"]
        ]

    assert shape(outage) == shape(healthy)
    assert any(r.application_modes for r in outage["results"])
    for result in outage["results"]:
        assert result.summary == TEMPLATE_SUMMARIES[result.verdict]
