"""Pipeline nodes: profile-builder → retriever → assessor → verifier → composer.

Phase 1: the assessor is an LLM judging eligibility from retrieved official text.
Phase 2 will swap it for the deterministic rules engine; every other node stays.
"""

import json
import logging
import re

from app.agent.state import (
    AgentState,
    AssessmentBatch,
    ProfileExtraction,
    SchemeResult,
    UserProfile,
    VerifiedCitation,
    VerifiedReason,
)
from app.ingestion.corpus import load_corpus
from app.ingestion.models import CorpusDoc
from app.llm.router import generate_structured_resilient
from app.retrieval.rerank import search_reranked
from app.retrieval.search import RetrievedChunk, get_sections
from app.rules.application import parse_application_modes, parse_document_items
from app.rules.doc_guides import guide_keys_for
from app.rules.engine import evaluate_scheme
from app.rules.loader import load_all_rules

logger = logging.getLogger(__name__)

TOP_K = 18
MAX_CONTEXT_CHUNKS = 26
MIN_QUOTE_CHARS = 12
MIN_DECISIVE_FACTS = 3

_corpus_by_id: dict[str, CorpusDoc] | None = None


def corpus_by_id() -> dict[str, CorpusDoc]:
    global _corpus_by_id
    if _corpus_by_id is None:
        _corpus_by_id = {doc.scheme_id: doc for doc in load_corpus()}
    return _corpus_by_id


# --- 1. profile builder ---

PROFILE_PROMPT = """You extract structured facts from how a person describes their life
situation, for checking Indian government welfare scheme eligibility.

Rules:
- Extract ONLY what the person actually stated or clearly implied. Never guess.
- Leave a field null if not stated. Do not default anything.
- annual_family_income_inr is yearly family income in rupees (convert "2 lakh" = 200000,
  monthly incomes to yearly).
- Field meanings (set only when stated/clearly implied; else null):
  - is_farmer_with_land: family owns cultivable land in their own name.
  - cultivates_crops: actively cultivates crops (as owner, tenant, or sharecropper).
  - has_land_ownership_or_tenure_docs: has land papers OR a valid written tenancy agreement.
  - family_member_in_govt_service: the person or a family member holds a government job.
  - receives_govt_pension_over_10k: a family member draws a government pension above
    Rs 10,000/month.
  - holds_constitutional_or_political_post: the person or a family member holds or
    formerly held a constitutional post or elected political office (minister, MP,
    MLA/MLC, mayor of a municipal corporation, district panchayat chairperson).
  - is_practicing_registered_professional: the person or a family member is a
    professional registered with a professional body (doctor, engineer, lawyer,
    chartered accountant, architect) AND practices that profession.
  - house_type: "kutcha" (mud/thatch/temporary, 0-2 rooms) or "pucca" (brick/concrete).
  - owns_motorized_vehicle: household owns a motorised 2/3/4-wheeler or fishing boat.
  - is_pmjay_priority_category: household clearly matches an SECC deprivation or listed
    occupational category (landless households on manual casual labour, destitute,
    ragpickers, domestic workers, street vendors, construction workers, sanitation
    workers, and similar).
  - has_lpg_connection: household already has an LPG gas connection.
  - is_street_vendor: sells goods/services from a cart/stall/public space.
  - has_vending_certificate_or_lor: holds a Certificate of Vending, ULB vendor ID card,
    is listed in the vending survey, or holds a Letter of Recommendation.
  - is_vishwakarma_trade_artisan: SELF-EMPLOYED artisan working with hands and tools in
    the unorganized sector in one of the 18 Vishwakarma trades: carpenter, boat maker,
    armourer, blacksmith, hammer/tool-kit maker, locksmith, goldsmith, potter,
    sculptor/stone carver, cobbler, mason, basket/mat/broom maker, doll & toy maker,
    barber, garland maker, washerman, tailor, fishing-net maker. Machine operators
    (e.g. powerloom) and traders/vendors are NOT.
  - is_post_matric_student: studying beyond class 10 (class 11/12, diploma, UG, PG) at a
    recognized institution.
  - is_pregnant: the person is currently pregnant.
  - single_girl_child: the applicant is the only girl child in the family (no brother).
  - disability_type: the certified disability CATEGORY, if stated — one of "autism",
    "cerebral_palsy", "intellectual_disability", "multiple_disabilities", or "other".
  - bereavement_event: the family's primary breadwinner (main earner) has died.
  - daughter_age: age of the person's (youngest relevant) daughter, if mentioned.
  - state: the Indian state or union territory where the person lives, as its full
    name (e.g. "Uttar Pradesh", not "UP" or a city name).
  - receives_other_govt_pension: the person already receives a pension under another
    state or central government scheme (old-age, widow, disability or similar).
  - number_of_children: how many children are in the person's family, if stated.
- is_enough_to_assess: true if the description gives at least a broad picture
  (some of: age, occupation, income, family situation). false only if it is too
  thin to say anything useful.
- If false, write ONE kind clarifying question in simple words asking only for the
  most decision-relevant missing facts (at most 3 things).

Previously known profile (merge; new statements override): {prior}

The person says:
\"\"\"{message}\"\"\"
"""


def build_profile(state: AgentState) -> AgentState:
    prior = state.get("prior_profile") or {}

    # Structured submissions (the guided wizard) send a full profile and no
    # message — nothing to extract, so the LLM call is skipped entirely.
    if not state["message"].strip():
        extraction = ProfileExtraction(profile=UserProfile(), is_enough_to_assess=False)
    else:
        prompt = PROFILE_PROMPT.format(
            prior=json.dumps(prior, ensure_ascii=False), message=state["message"]
        )
        extraction = generate_structured_resilient(prompt, ProfileExtraction)

    # Merge: keep prior values unless the new extraction states them.
    merged = UserProfile.model_validate(prior) if prior else UserProfile()
    update = extraction.profile.model_dump(exclude_none=True, exclude={"notes"})
    merged = merged.model_copy(update=update)
    if extraction.profile.notes:
        merged.notes = extraction.profile.notes

    # "Enough to assess" is policy, not extraction — decide it deterministically.
    # Location/gender alone don't drive eligibility; three other concrete facts do.
    low_signal_fields = {"notes", "state", "area", "gender"}
    decisive_facts = sum(
        1
        for field, value in merged.model_dump().items()
        if field not in low_signal_fields and value is not None
    )
    if (
        extraction.is_enough_to_assess
        or decisive_facts >= MIN_DECISIVE_FACTS
        or _rules_reach_entitlement(merged)
    ):
        return {"profile": merged, "status": "ok"}
    return {
        "profile": merged,
        "status": "need_info",
        "question": extraction.clarifying_question
        or "Could you share your age, what you do for a living, and your family's yearly income?",
    }


def _rules_reach_entitlement(profile: UserProfile) -> bool:
    """True when the stated facts already fully satisfy at least one scheme's
    rules (eligible / likely_eligible). Abstaining then would hide a concrete
    entitlement behind a clarifying question, so the gate lets the case through
    even if the overall fact count is sparse. Deterministic and LLM-free."""
    return any(
        evaluate_scheme(scheme_rules, profile).verdict in ("eligible", "likely_eligible")
        for scheme_rules in load_all_rules().values()
    )


# --- 2. retriever ---


def _profile_query(profile: UserProfile) -> str:
    parts: list[str] = []
    if profile.age is not None:
        parts.append(f"{profile.age} year old")
    if profile.gender:
        parts.append(profile.gender)
    if profile.marital_status:
        parts.append(profile.marital_status)
    if profile.occupation:
        parts.append(profile.occupation)
    if profile.is_farmer_with_land:
        parts.append("farmer with cultivable land")
    if profile.area:
        parts.append(f"{profile.area} area")
    if profile.social_category and profile.social_category != "general":
        parts.append(profile.social_category.upper())
    if profile.has_bpl_card:
        parts.append("below poverty line BPL card")
    if profile.disability_percent:
        parts.append(f"{profile.disability_percent}% disability")
    if profile.annual_family_income_inr is not None:
        parts.append(f"family income {profile.annual_family_income_inr} rupees per year")
    if profile.is_student:
        parts.append("student")
    if profile.daughter_age is not None:
        parts.append(f"daughter aged {profile.daughter_age}")
    if profile.notes:
        parts.append(profile.notes)
    return "eligibility for government welfare schemes: " + ", ".join(parts)


def retrieve(state: AgentState) -> AgentState:
    hits = search_reranked(_profile_query(state["profile"]), k=TOP_K)

    # Guarantee the LLM sees the decisive sections of every candidate scheme.
    seen: dict[str, RetrievedChunk] = {c.chunk_id: c for c in hits}
    for scheme_id in {c.scheme_id for c in hits}:
        for chunk in get_sections(scheme_id, ["eligibility", "exclusions"]):
            seen.setdefault(chunk.chunk_id, chunk)

    chunks = sorted(seen.values(), key=lambda c: c.score, reverse=True)[:MAX_CONTEXT_CHUNKS]
    return {"retrieved": chunks}


# --- 3. assessor (Phase 1: LLM judgment) ---

ASSESS_PROMPT = """You are checking which Indian central government welfare schemes a person
may be eligible for, using ONLY the official scheme text excerpts provided.

Person's profile (null = unknown, never assume):
{profile}

Official excerpts (each begins with CHUNK <chunk_id>):
{context}

Candidate scheme ids — output EXACTLY ONE assessment for EACH of these:
{candidate_ids}

For each candidate scheme:
- verdict:
  - "eligible" — the profile clearly satisfies every criterion visible in the excerpts.
  - "likely_eligible" — criteria in the excerpts are satisfied but a self-declared or
    unverifiable fact remains (e.g. BPL list membership).
  - "not_eligible" — the profile clearly violates at least one criterion or exclusion.
  - "need_more_info" — a required fact is null in the profile; list it in missing_info.
- summary: one kind, plain-language sentence speaking directly to the person as "you"
  (e.g. "You appear to qualify because…"), never "the person" or "the applicant".
- reasons: each reason states ONE criterion check, and MUST cite the chunk_id it came
  from with a short VERBATIM quote (copy the exact words) from that chunk.
- Never invent criteria, amounts, or entitlements not present in the excerpts.
- missing_info: plain-language names of the missing facts (only for need_more_info).
"""


def assess(state: AgentState) -> AgentState:
    context = "\n\n".join(f"CHUNK {c.chunk_id}\n{c.text}" for c in state["retrieved"])
    candidate_ids = sorted({c.scheme_id for c in state["retrieved"]})
    prompt = ASSESS_PROMPT.format(
        profile=state["profile"].model_dump_json(indent=1),
        context=context,
        candidate_ids=", ".join(candidate_ids),
    )
    def reject_empty(batch: AssessmentBatch) -> None:
        if not batch.assessments:
            raise ValueError("assessor returned an empty batch despite retrieved candidates")

    batch = generate_structured_resilient(prompt, AssessmentBatch, validate=reject_empty)

    # LLMs sometimes echo the scheme's name instead of its id — map both back.
    candidates: dict[str, str] = {}
    for chunk in state["retrieved"]:
        candidates[chunk.scheme_id.lower()] = chunk.scheme_id
        candidates[chunk.short_name.lower()] = chunk.scheme_id
        candidates[chunk.scheme_name.lower()] = chunk.scheme_id

    assessments = []
    for assessment in batch.assessments:
        canonical = candidates.get(assessment.scheme_id.strip().lower())
        if canonical is None:
            logger.warning(
                "assessor referenced unknown scheme %r — discarded", assessment.scheme_id
            )
            continue
        assessments.append(assessment.model_copy(update={"scheme_id": canonical}))
    return {"assessments": assessments}


# --- 4. verifier ---


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def verify_and_compose(state: AgentState) -> AgentState:
    """Drop any claim whose citation can't be matched to retrieved official text,
    then compose final per-scheme results enriched with documents & how-to-apply."""
    chunks = {c.chunk_id: c for c in state["retrieved"]}
    corpus = corpus_by_id()
    results: list[SchemeResult] = []

    for assessment in state["assessments"]:
        doc = corpus.get(assessment.scheme_id)
        if doc is None:
            continue
        verified_reasons: list[VerifiedReason] = []
        dropped = 0
        for reason in assessment.reasons:
            kept: list[VerifiedCitation] = []
            for citation in reason.citations:
                chunk = chunks.get(citation.chunk_id)
                quote_ok = (
                    chunk is not None
                    and len(citation.quote) >= MIN_QUOTE_CHARS
                    and _normalize(citation.quote) in _normalize(chunk.text)
                )
                if quote_ok:
                    kept.append(
                        VerifiedCitation(
                            chunk_id=citation.chunk_id,
                            quote=citation.quote,
                            section=chunk.section,
                            source_url=chunk.source_url,
                        )
                    )
                else:
                    dropped += 1
            if kept:
                verified_reasons.append(VerifiedReason(text=reason.text, citations=kept))
            else:
                dropped += 1

        verdict = assessment.verdict
        summary = assessment.summary
        missing = list(assessment.missing_info)
        if not verified_reasons and verdict != "need_more_info":
            verdict = "need_more_info"
            summary = (
                "We couldn't verify this against the official scheme text, "
                "so we're not making a claim either way."
            )
            missing = missing or ["verification against official text"]
            logger.warning(
                "verifier downgraded %s: no verifiable citations", assessment.scheme_id
            )

        results.append(
            SchemeResult(
                scheme_id=assessment.scheme_id,
                scheme_name=doc.name,
                short_name=doc.short_name,
                verdict=verdict,
                summary=summary,
                reasons=verified_reasons,
                missing_info=missing,
                documents=doc.sections.get("documents", ""),
                document_guide_keys=guide_keys_for(doc.sections.get("documents", "")),
                how_to_apply=doc.sections.get("application", ""),
                page_url=doc.page_url,
                references=[r.model_dump() for r in doc.references],
                dropped_claims=dropped,
                **(
                    {
                        "application_modes": parse_application_modes(
                            doc.sections.get("application", "")
                        ),
                        "document_items": parse_document_items(
                            doc.sections.get("documents", "")
                        ),
                    }
                    if verdict in ("eligible", "likely_eligible")
                    else {}
                ),
            )
        )

    order = {"eligible": 0, "likely_eligible": 1, "need_more_info": 2, "not_eligible": 3}
    results.sort(key=lambda r: order[r.verdict])
    return {"results": results, "status": "ok"}
