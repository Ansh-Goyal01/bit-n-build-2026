"""Translation at the edges — the engine never sees a language, only facts.

The deterministic rules engine reasons over structured English-canonical facts;
a verdict can never depend on the user's language. Translation happens ONLY:

- inbound: free-text user input → English, before extraction;
- outbound: report/explanation PROSE → the user's language, after the verdict.

Canonical values are never translated: verdict enums, scheme names/short names,
amounts, dates, thresholds, URLs, citations (verbatim official text), and
references. If prose contains them, the provider is instructed to copy them
through unchanged.

Providers are swappable via settings.translation_provider:

- "llm" (default): the existing Gemini→Groq structured plumbing. Zero new
  dependencies, free-tier, and — like every path here — disk-cached, so each
  (text, language) pair is translated exactly once, deterministically.
- "indictrans2": AI4Bharat IndicTrans2 running locally (fully offline, 22
  languages). Heavy optional deps (~1GB model); install
  `transformers` + `IndicTransToolkit` and set TRANSLATION_PROVIDER=indictrans2.
- "bhashini": the government Bhashini/ULCA API (free, needs a registered key
  in BHASHINI_API_KEY). Skeleton — wire udyat endpoint when a key exists.

Every provider's output passes through the same disk cache
(cache key: provider+model, target language, exact text), satisfying quota
and determinism requirements regardless of backend.

Translation must never block an answer: any provider failure falls back to
the English original (the report stays correct, just untranslated).
"""

import logging
from typing import Protocol

from pydantic import BaseModel

from app.api.schemas import AssessResponse
from app.config import settings
from app.llm.cache import cache_key, get_cache

logger = logging.getLogger(__name__)

# Language registry — adding a language here (plus a frontend dictionary) is
# ALL it takes; no code changes. Codes are BCP-47 primary subtags.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "mr": "Marathi",
    "te": "Telugu",
    "ta": "Tamil",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
}

_BATCH_SIZE = 16


class TranslationProvider(Protocol):
    """Translate a batch of English texts into `target` (a SUPPORTED_LANGUAGES
    code). Must return exactly one output per input, order-preserved."""

    name: str

    def translate_batch(self, texts: list[str], target: str) -> list[str]: ...


class _IndexedTranslation(BaseModel):
    i: int
    text: str


class _TranslationBatch(BaseModel):
    translations: list[_IndexedTranslation]


# Inputs and outputs are INDEXED because an LLM may return a batch shuffled —
# a mere count check once let a scheme's how-to-apply land in a reason slot.
# The index makes alignment provable instead of assumed.
_LLM_PROMPT = """Translate the following English texts to {language} for a government
welfare-scheme eligibility report read by ordinary citizens.

Rules — these protect legally meaningful content:
- Copy through UNCHANGED: numbers, currency amounts (like ₹2,50,000), dates,
  percentages, URLs, email addresses, scheme names and acronyms (PM-KISAN,
  PMAY-G, BPL, SECC, LPG, LoR, ULB, Aadhaar and similar), and anything inside
  markdown link targets. Translate the words AROUND them.
- Keep markdown structure (headings, lists, links, bold) exactly.
- Plain, warm, respectful register (in Hindi use the आप form). Prefer everyday
  words over bureaucratic ones. Do not add, drop, or soften any condition.
- Return one object per input as {{"i": <its index>, "text": "<translation>"}} —
  every index exactly once, {n} in total.

Input texts (JSON array of [index, text] pairs):
{texts_json}
"""


class LLMTranslationProvider:
    """Gemini→Groq structured translation with the shared repair/fallback path."""

    name = "llm"

    def translate_batch(self, texts: list[str], target: str) -> list[str]:
        import json

        from app.llm.router import generate_structured_resilient

        def _indices_ok(result: _TranslationBatch) -> None:
            got = sorted(t.i for t in result.translations)
            if got != list(range(len(texts))):
                raise ValueError(
                    f"expected indices 0..{len(texts) - 1} exactly once, got {got}"
                )

        prompt = _LLM_PROMPT.format(
            language=SUPPORTED_LANGUAGES[target],
            n=len(texts),
            texts_json=json.dumps(list(enumerate(texts)), ensure_ascii=False),
        )
        result = generate_structured_resilient(prompt, _TranslationBatch, validate=_indices_ok)
        by_index = {t.i: t.text for t in result.translations}
        return [by_index[i] for i in range(len(texts))]


class IndicTrans2Provider:
    """Local AI4Bharat IndicTrans2 (en→indic). Fully offline; optional deps."""

    name = "indictrans2"

    # IndicTrans2 uses flores-style tags.
    _FLORES = {
        "hi": "hin_Deva", "bn": "ben_Beng", "mr": "mar_Deva", "te": "tel_Telu",
        "ta": "tam_Taml", "gu": "guj_Gujr", "kn": "kan_Knda", "ml": "mal_Mlym",
        "pa": "pan_Guru", "or": "ory_Orya",
    }

    def __init__(self) -> None:
        try:
            from IndicTransToolkit.processor import IndicProcessor  # type: ignore
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore
        except ImportError as exc:  # pragma: no cover — env-dependent
            raise RuntimeError(
                "IndicTrans2 provider needs optional deps: "
                "pip install transformers IndicTransToolkit torch — or set "
                "TRANSLATION_PROVIDER=llm"
            ) from exc
        model_name = "ai4bharat/indictrans2-en-indic-dist-200M"
        self._processor = IndicProcessor(inference=True)
        self._tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True)

    def translate_batch(self, texts: list[str], target: str) -> list[str]:  # pragma: no cover
        tgt = self._FLORES[target]
        batch = self._processor.preprocess_batch(texts, src_lang="eng_Latn", tgt_lang=tgt)
        inputs = self._tokenizer(batch, truncation=True, padding="longest", return_tensors="pt")
        generated = self._model.generate(**inputs, num_beams=5, max_length=512)
        decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True)
        return self._processor.postprocess_batch(decoded, lang=tgt)


class BhashiniProvider:
    """Government Bhashini/ULCA pipeline (free; requires a registered API key)."""

    name = "bhashini"

    def __init__(self) -> None:
        if not settings.bhashini_api_key:  # pragma: no cover — env-dependent
            raise RuntimeError(
                "Bhashini needs BHASHINI_API_KEY (register at bhashini.gov.in/ulca) "
                "— or set TRANSLATION_PROVIDER=llm"
            )
        raise NotImplementedError(
            "Bhashini pipeline call not wired yet — add the ULCA compute call here "
            "once a key is registered. The interface and cache already fit it."
        )

    def translate_batch(self, texts: list[str], target: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError


_provider: TranslationProvider | None = None


def get_provider() -> TranslationProvider:
    global _provider
    if _provider is None:
        kind = settings.translation_provider
        if kind == "indictrans2":
            _provider = IndicTrans2Provider()
        elif kind == "bhashini":
            _provider = BhashiniProvider()
        else:
            _provider = LLMTranslationProvider()
    return _provider


def translate_many(texts: list[str], target: str) -> list[str]:
    """Disk-cached, order-preserving batch translation. English passes through.

    Any provider failure returns the English originals for the failed batch —
    a report must never be blocked or broken by translation."""
    if target == "en" or not texts:
        return list(texts)
    if target not in SUPPORTED_LANGUAGES:
        logger.warning("unsupported target language %r; returning English", target)
        return list(texts)

    provider = get_provider()
    cache = get_cache()

    def key_for(text: str) -> str:
        return cache_key("translate", provider.name, {"target": target, "text": text})

    out: dict[int, str] = {}
    misses: list[tuple[int, str]] = []
    for i, text in enumerate(texts):
        if not text.strip():
            out[i] = text
            continue
        cached = cache.get(key_for(text))
        if cached is not None:
            out[i] = cached
        else:
            misses.append((i, text))

    for start in range(0, len(misses), _BATCH_SIZE):
        chunk = misses[start : start + _BATCH_SIZE]
        chunk_texts = [t for _, t in chunk]
        try:
            translated = provider.translate_batch(chunk_texts, target)
        except Exception:  # noqa: BLE001 — never block the report on translation
            logger.exception("translation batch failed; returning English originals")
            translated = chunk_texts
        else:
            for (_, original), result in zip(chunk, translated, strict=True):
                cache.set(key_for(original), result)
        for (i, _), result in zip(chunk, translated, strict=True):
            out[i] = result

    return [out[i] for i in range(len(texts))]


def translate_text(text: str, target: str) -> str:
    return translate_many([text], target)[0]


def to_english(text: str, source: str) -> str:
    """Inbound edge: user free text → canonical English (before extraction).

    Cached like everything else. On failure the original text is passed
    through — the extractor handles multilingual input imperfectly rather
    than the request failing."""
    if source == "en" or not text.strip():
        return text
    provider = get_provider()
    cache = get_cache()
    key = cache_key("translate", provider.name, {"target": "en", "source": source, "text": text})
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        if isinstance(provider, LLMTranslationProvider):
            import json

            from app.llm.router import generate_structured_resilient

            prompt = (
                f"Translate this {SUPPORTED_LANGUAGES.get(source, source)} text to English, "
                "preserving all numbers, amounts, and names exactly. Return one object "
                'as {"i": 0, "text": "<the English translation>"}:\n'
                f"{json.dumps([text], ensure_ascii=False)}"
            )
            result = generate_structured_resilient(prompt, _TranslationBatch)
            english = result.translations[0].text
        else:  # pragma: no cover — provider-dependent
            english = provider.translate_batch([text], "en")[0]
    except Exception:  # noqa: BLE001 — pass through rather than fail the request
        logger.exception("inbound translation failed; passing original through")
        return text
    cache.set(key, english)
    return english


def translate_response(response: AssessResponse, target: str) -> AssessResponse:
    """Outbound edge: translate PROSE fields of an assess response, in one
    batched pass. Never touched: verdict, scheme_id/name/short_name, page_url,
    references, citations (verbatim official quotes), dropped_claims, profile.
    """
    if target == "en":
        return response

    # Collect every translatable string with a path back to its slot.
    texts: list[str] = []

    def add(text: str | None) -> int | None:
        if text is None or not text.strip():
            return None
        texts.append(text)
        return len(texts) - 1

    q_idx = add(response.question)
    slots = []
    for result in response.results:
        slots.append(
            {
                "summary": add(result.summary),
                "reasons": [add(r.text) for r in result.reasons],
                "missing_info": [add(m) for m in result.missing_info],
                "confirm": [add(c) for c in result.confirm_before_applying],
                "documents": add(result.documents),
                "how_to_apply": add(result.how_to_apply),
                # near-miss: only the ask prose is translated; the clause is a
                # verbatim official quote and stays untouched like citations.
                "near_miss_ask": add(result.near_miss.ask) if result.near_miss else None,
                # Packet lines: step/document text is prose; mode kinds,
                # guide keys, links, and rule ids are language-invariant.
                "steps": [
                    [add(step.text) for step in mode.steps] for mode in result.application_modes
                ],
                "doc_items": [add(item.text) for item in result.document_items],
                "confirmations": [add(c.text) for c in result.confirmations],
            }
        )

    translated = translate_many(texts, target)

    def pick(idx: int | None, original: str) -> str:
        return translated[idx] if idx is not None else original

    new_results = []
    for result, slot in zip(response.results, slots, strict=True):
        new_results.append(
            result.model_copy(
                update={
                    "summary": pick(slot["summary"], result.summary),
                    "reasons": [
                        r.model_copy(update={"text": pick(idx, r.text)})
                        for r, idx in zip(result.reasons, slot["reasons"], strict=True)
                    ],
                    "missing_info": [
                        pick(idx, m)
                        for m, idx in zip(result.missing_info, slot["missing_info"], strict=True)
                    ],
                    "confirm_before_applying": [
                        pick(idx, c)
                        for c, idx in zip(
                            result.confirm_before_applying, slot["confirm"], strict=True
                        )
                    ],
                    "documents": pick(slot["documents"], result.documents),
                    "how_to_apply": pick(slot["how_to_apply"], result.how_to_apply),
                    "near_miss": (
                        result.near_miss.model_copy(
                            update={"ask": pick(slot["near_miss_ask"], result.near_miss.ask)}
                        )
                        if result.near_miss
                        else None
                    ),
                    "application_modes": [
                        mode.model_copy(
                            update={
                                "steps": [
                                    step.model_copy(update={"text": pick(idx, step.text)})
                                    for step, idx in zip(mode.steps, step_slots, strict=True)
                                ]
                            }
                        )
                        for mode, step_slots in zip(
                            result.application_modes, slot["steps"], strict=True
                        )
                    ],
                    "document_items": [
                        item.model_copy(update={"text": pick(idx, item.text)})
                        for item, idx in zip(result.document_items, slot["doc_items"], strict=True)
                    ],
                    "confirmations": [
                        c.model_copy(update={"text": pick(idx, c.text)})
                        for c, idx in zip(result.confirmations, slot["confirmations"], strict=True)
                    ],
                }
            )
        )

    return response.model_copy(
        update={
            "question": pick(q_idx, response.question) if response.question else None,
            "results": new_results,
        }
    )
