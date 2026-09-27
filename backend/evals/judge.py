"""Faithfulness judge — RAGAS-style claim-support checking.

Every reason the assessor produced is checked against the official text it cited,
by the Groq judge model (settings.groq_judge_model; set it to a different
family than the generator under test, e.g. qwen/qwen3.8-27b, to reduce
self-preference bias). Hallucination rate =
unsupported claims / total claims. Claims with no resolvable citation are
unsupported by definition.
"""

import json
import logging

from app.config import settings
from app.llm.groq_client import complete

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are verifying whether a claim about an Indian welfare scheme is supported
by an excerpt of official scheme text.

Claim:
{claim}

Official excerpt:
\"\"\"{excerpt}\"\"\"

Is every factual assertion in the claim directly supported by the excerpt (no outside
knowledge, no charitable inference)? Reply with JSON: {{"supported": true}} or {{"supported": false}}.
"""  # noqa: E501 — do not reflow: the prompt is a cache key shared across eval phases


def claim_supported(claim: str, excerpt: str) -> bool:
    text = complete(
        JUDGE_PROMPT.format(claim=claim, excerpt=excerpt),
        json_mode=True,
        model=settings.groq_judge_model,
    )
    try:
        return bool(json.loads(text).get("supported", False))
    except json.JSONDecodeError:
        logger.warning("judge returned non-JSON: %.80s", text)
        return False


def faithfulness(claims: list[tuple[str, str | None]]) -> tuple[int, int]:
    """claims: (claim_text, cited_excerpt or None). Returns (supported, total)."""
    supported = 0
    for claim, excerpt in claims:
        if excerpt and claim_supported(claim, excerpt):
            supported += 1
    return supported, len(claims)
