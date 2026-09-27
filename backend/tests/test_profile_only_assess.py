"""Profile-only submissions (guided wizard): no message, no extraction LLM call."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.agent.nodes import build_profile
from app.api.schemas import AssessRequest


def test_blank_message_with_rich_profile_skips_extraction_and_assesses() -> None:
    prior = {"age": 45, "occupation": "farmer", "annual_family_income_inr": 80000}
    with patch("app.agent.nodes.generate_structured_resilient") as llm:
        result = build_profile({"message": "   ", "prior_profile": prior})
    llm.assert_not_called()
    assert result["status"] == "ok"
    assert result["profile"].age == 45


def test_blank_message_with_thin_profile_still_asks() -> None:
    with patch("app.agent.nodes.generate_structured_resilient") as llm:
        result = build_profile({"message": "", "prior_profile": {"state": "Bihar"}})
    llm.assert_not_called()
    assert result["status"] == "need_info"
    assert result["question"]


def test_request_requires_message_or_profile() -> None:
    with pytest.raises(ValidationError):
        AssessRequest(message="   ")
    assert AssessRequest(profile={"age": 30}).message == ""
    assert AssessRequest(message="I am a farmer").profile is None
