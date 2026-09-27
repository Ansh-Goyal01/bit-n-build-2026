"""Typed state flowing through the agent pipeline."""

from typing import Literal, TypedDict, get_args

from pydantic import BaseModel, Field, field_validator

from app.agent.states import canonical_state
from app.retrieval.search import RetrievedChunk

Verdict = Literal["eligible", "likely_eligible", "not_eligible", "need_more_info"]


class UserProfile(BaseModel):
    """Structured facts extracted from the user's plain-language description.

    Every field is optional — `None` means "not stated", and the pipeline treats
    missing facts as unknowns, never as defaults.
    """

    age: int | None = None
    gender: Literal["male", "female", "other"] | None = None
    marital_status: Literal["married", "widowed", "single", "divorced"] | None = None
    state: str | None = None
    area: Literal["rural", "urban"] | None = None
    occupation: str | None = None
    is_farmer_with_land: bool | None = None
    annual_family_income_inr: int | None = None
    social_category: (
        Literal["general", "sc", "st", "obc", "minority", "ews", "dnt", "safai_mitra"]
        | None
    ) = None
    has_bpl_card: bool | None = None
    disability_percent: int | None = None
    has_bank_account: bool | None = None
    pays_income_tax: bool | None = None
    is_student: bool | None = None
    daughter_age: int | None = None
    # Facts that make occupation/household rules deterministic (Phase 2 engine).
    family_member_in_govt_service: bool | None = None
    receives_govt_pension_over_10k: bool | None = None
    holds_constitutional_or_political_post: bool | None = None
    is_practicing_registered_professional: bool | None = None
    cultivates_crops: bool | None = None
    has_land_ownership_or_tenure_docs: bool | None = None
    house_type: Literal["kutcha", "pucca"] | None = None
    owns_motorized_vehicle: bool | None = None
    is_pmjay_priority_category: bool | None = None
    has_lpg_connection: bool | None = None
    is_street_vendor: bool | None = None
    has_vending_certificate_or_lor: bool | None = None
    is_vishwakarma_trade_artisan: bool | None = None
    is_post_matric_student: bool | None = None
    is_pregnant: bool | None = None
    # The applicant is the only girl child of the family (no brother; per scheme
    # text, a girl with a brother is not a "single girl child").
    single_girl_child: bool | None = None
    # Disability category as enumerated in the National Trust Act 1999 / RPwD Act
    # scheme text (Autism, Cerebral Palsy, Intellectual Disability, Multiple
    # Disabilities); "other" for a certified disability outside those four.
    disability_type: (
        Literal[
            "autism",
            "cerebral_palsy",
            "intellectual_disability",
            "multiple_disabilities",
            "other",
        ]
        | None
    ) = None
    # The family's primary breadwinner has died (National Family Benefit Scheme).
    bereavement_event: bool | None = None
    # Already drawing a pension under another state or central government
    # scheme (old-age, widow, disability or similar) — UP pension exclusions.
    receives_other_govt_pension: bool | None = None
    # Number of children in the family (Kanya Sumangala Yojana's two-child rule).
    number_of_children: int | None = None
    notes: str = ""

    @field_validator("state", mode="before")
    @classmethod
    def _normalize_state(cls, value: object) -> object:
        """State rules compare exact canonical names, so "UP" or "uttar
        pradesh" become "Uttar Pradesh" and anything unrecognised becomes
        None ("not stated") rather than a string no rule can ever match."""
        if not isinstance(value, str):
            return value
        return canonical_state(value)

    @field_validator(
        "gender",
        "marital_status",
        "area",
        "social_category",
        "house_type",
        "disability_type",
        mode="before",
    )
    @classmethod
    def _normalize_category(cls, value: object, info) -> object:
        """Extractors sometimes return 'SC', 'Rural', or junk like 'BPL' (an
        economic status, not a social category). Lowercase valid values; treat
        anything outside the Literal as "not stated" rather than failing the
        whole request — with disk-cached completions such a failure would be
        deterministic and permanent."""
        if not isinstance(value, str):
            return value
        lowered = value.strip().lower()
        allowed = get_args(get_args(cls.model_fields[info.field_name].annotation)[0])
        return lowered if lowered in allowed else None


class ProfileExtraction(BaseModel):
    """Gemini structured output for the profile-builder node."""

    profile: UserProfile
    is_enough_to_assess: bool
    clarifying_question: str = Field(
        default="",
        description="One kind, plain-language question asking ONLY for the most "
        "valuable missing facts. Empty if is_enough_to_assess.",
    )


class Citation(BaseModel):
    chunk_id: str
    quote: str


class Reason(BaseModel):
    text: str
    citations: list[Citation]


class SchemeAssessment(BaseModel):
    scheme_id: str
    verdict: Verdict
    summary: str
    reasons: list[Reason]
    missing_info: list[str] = []


class AssessmentBatch(BaseModel):
    assessments: list[SchemeAssessment]


class VerifiedCitation(BaseModel):
    chunk_id: str
    quote: str
    section: str
    source_url: str


class VerifiedReason(BaseModel):
    text: str
    citations: list[VerifiedCitation]


Op = Literal["eq", "ne", "gt", "gte", "lt", "lte"]


class NearMissCondition(BaseModel):
    """One leaf comparison the person would need to satisfy (require) or
    escape (exclude) — language-invariant, rendered client-side."""

    field: str
    op: Op
    value: bool | int | str


class NearMiss(BaseModel):
    """R1 — a scheme blocked by exactly ONE rule, where resolving that rule
    alone would make the person eligible. Deterministic: the blocking rule's
    official clause plus the concrete leaf conditions."""

    rule_id: str
    kind: Literal["require", "exclude"]
    clause: str
    source_url: str
    ask: str
    unlocked_verdict: Verdict  # what the verdict becomes with the blocker resolved
    conditions: list[NearMissCondition]


ApplicationModeKind = Literal["online", "offline", "csc", "other"]


class ApplicationStep(BaseModel):
    """One line of the official application process. `text` is always a
    substring of the source markdown — steps are split, never rewritten."""

    kind: Literal["step", "heading", "note"]
    text: str


class ApplicationMode(BaseModel):
    """One `### Application mode: X` block of the official application text."""

    mode: ApplicationModeKind  # language-invariant; the frontend localizes it
    steps: list[ApplicationStep]
    links: list[str] = []  # official URLs quoted in the block, in order


class DocumentItem(BaseModel):
    """One line of the official documents list. `item` lines are tickable;
    `group` lines label the items below them; `note` lines are prose."""

    kind: Literal["item", "group", "note"]
    text: str
    # Language-invariant document type (doc_guides) detected in THIS line.
    guide_key: str | None = None


class ConfirmationStep(BaseModel):
    """A self-declared fact a conditional verdict rests on, with the rule it
    comes from — lets an operator annotate it without touching the verdict."""

    rule_id: str
    text: str


class SchemeResult(BaseModel):
    """Final per-scheme answer returned by the API."""

    scheme_id: str
    scheme_name: str
    short_name: str
    verdict: Verdict
    summary: str
    reasons: list[VerifiedReason]
    missing_info: list[str]
    # For conditional (likely_eligible) verdicts: the self-declared facts the
    # verdict rests on, each phrased as a concrete verification step.
    confirm_before_applying: list[str] = []
    documents: str = ""
    # R4: language-invariant keys of common document types detected in the
    # documents section — the frontend renders localized how-to guides per key.
    document_guide_keys: list[str] = []
    how_to_apply: str = ""
    page_url: str = ""
    references: list[dict[str, str]] = []
    dropped_claims: int = 0
    # R1: set only on not_eligible verdicts that are exactly one rule away
    # from eligible — the "close to qualifying" suggestion.
    near_miss: NearMiss | None = None
    # Application packet (eligible / likely_eligible only): the official
    # application and documents text, parsed deterministically from the
    # English corpus before edge translation. Empty for other verdicts.
    application_modes: list[ApplicationMode] = []
    document_items: list[DocumentItem] = []
    # Structured twin of confirm_before_applying (same texts, with rule ids).
    confirmations: list[ConfirmationStep] = []


class AgentState(TypedDict, total=False):
    message: str
    prior_profile: dict | None
    profile: UserProfile
    status: Literal["ok", "need_info"]
    question: str
    retrieved: list[RetrievedChunk]
    assessments: list[SchemeAssessment]
    results: list[SchemeResult]
    # True when any explained verdict shipped a template summary because the
    # LLM explainer was unavailable — verdicts and packets are unaffected.
    explanations_simplified: bool
