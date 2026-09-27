"""Gemini client: JSON-schema structured output, disk-cached, retried."""

import logging
import time
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.llm.cache import cache_key, get_cache

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

THROTTLE_SECONDS = 6.5  # free tier allows 10 requests/minute

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(genai.errors.APIError),
)
def _generate(prompt: str, schema: type[BaseModel] | None, temperature: float) -> str:
    config = types.GenerateContentConfig(temperature=temperature)
    if schema is not None:
        config.response_mime_type = "application/json"
        config.response_schema = schema
    response = _get_client().models.generate_content(
        model=settings.gemini_model, contents=prompt, config=config
    )
    if response.text is None:
        raise ValueError(f"Gemini returned no text (finish: {response.candidates})")
    return response.text


def generate_structured(prompt: str, schema: type[T], temperature: float = 0.0) -> T:
    """Generate a response parsed into `schema`, served from disk cache when possible."""
    key = cache_key(
        "gemini",
        settings.gemini_model,
        {"prompt": prompt, "schema": schema.__name__, "temperature": temperature},
    )
    cache = get_cache()
    text = cache.get(key)
    if text is None:
        text = _generate(prompt, schema, temperature)
        cache.set(key, text)
        time.sleep(THROTTLE_SECONDS)
    else:
        logger.debug("gemini cache hit")
    return schema.model_validate_json(text)
