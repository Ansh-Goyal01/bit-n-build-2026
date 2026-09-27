"""The Groq path repairs invalid structured output once instead of dying.

A disk-cached invalid completion would otherwise fail deterministically on
every retry (same key, same bad text) — the eval permanently loses the case.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel, ValidationError

from app.llm.router import generate_structured_resilient


class Toy(BaseModel):
    color: str


BAD = '{"colour": "red"}'  # wrong field name -> validation error
GOOD = '{"color": "red"}'


def test_groq_validation_failure_triggers_one_repair_retry():
    with (
        patch("app.llm.router.settings") as mock_settings,
        patch("app.llm.router.groq_client") as mock_groq,
    ):
        mock_settings.primary_llm = "groq"
        mock_groq.complete.side_effect = [BAD, GOOD]
        result = generate_structured_resilient("prompt", Toy)
    assert result.color == "red"
    assert mock_groq.complete.call_count == 2
    # the repair prompt must carry the validation error back to the model
    repair_prompt = mock_groq.complete.call_args_list[1].args[0]
    assert "failed validation" in repair_prompt


def test_groq_repair_failure_propagates():
    with (
        patch("app.llm.router.settings") as mock_settings,
        patch("app.llm.router.groq_client") as mock_groq,
    ):
        mock_settings.primary_llm = "groq"
        mock_groq.complete.side_effect = [BAD, BAD]
        with pytest.raises(ValidationError):
            generate_structured_resilient("prompt", Toy)
    assert mock_groq.complete.call_count == 2


def test_groq_valid_first_try_makes_one_call():
    with (
        patch("app.llm.router.settings") as mock_settings,
        patch("app.llm.router.groq_client") as mock_groq,
    ):
        mock_settings.primary_llm = "groq"
        mock_groq.complete.side_effect = [GOOD]
        result = generate_structured_resilient("prompt", Toy)
    assert result.color == "red"
    assert mock_groq.complete.call_count == 1
