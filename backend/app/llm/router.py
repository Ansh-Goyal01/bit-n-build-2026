"""Resilient structured generation: Gemini primary, Groq fallback.

The free Gemini tier intermittently returns 503 (high demand) or degenerate
empty outputs. Any failure — transport, parsing, or semantic (via `validate`) —
falls back to Groq (settings.groq_model, gpt-oss-120b by default) with the JSON
schema embedded in the prompt.
"""

import json
import logging
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.config import settings
from app.llm import gemini, groq_client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

GROQ_JSON_SUFFIX = """

Respond with a single JSON object (no prose, no markdown fences) that conforms
exactly to this JSON schema:
{schema}
"""


def generate_structured_resilient(
    prompt: str,
    schema: type[T],
    validate: Callable[[T], None] | None = None,
) -> T:
    """Structured output from Gemini, falling back to Groq. `validate` may raise
    to reject a semantically-bad result and trigger the fallback."""
    if settings.primary_llm == "gemini":
        try:
            result = gemini.generate_structured(prompt, schema)
            if validate is not None:
                validate(result)
            return result
        except Exception as exc:  # noqa: BLE001 — any primary failure triggers fallback
            logger.warning("gemini failed (%s: %s); falling back to groq", type(exc).__name__, exc)

    full_prompt = prompt + GROQ_JSON_SUFFIX.format(schema=json.dumps(schema.model_json_schema()))
    text = groq_client.complete(full_prompt, json_mode=True)
    try:
        result = schema.model_validate_json(text)
        if validate is not None:
            validate(result)
        return result
    except Exception as exc:  # noqa: BLE001 — one repair pass, then let it propagate
        # Completions are disk-cached by prompt: without a repair pass, an invalid
        # output would fail deterministically on every retry (same key, same text).
        # Feeding the error back changes the cache key and usually fixes the output.
        logger.warning("groq output failed validation (%s); one repair retry", type(exc).__name__)
        repair_prompt = (
            f"{full_prompt}\n\nYour previous JSON response failed validation with this "
            f"error:\n{exc}\n\nReturn a corrected JSON object that fixes exactly this."
        )
        text = groq_client.complete(repair_prompt, json_mode=True)
        result = schema.model_validate_json(text)
        if validate is not None:
            validate(result)
        return result
