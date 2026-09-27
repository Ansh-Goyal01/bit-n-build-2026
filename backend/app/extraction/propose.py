"""Rule-extraction pipeline: an LLM PROPOSES rules; humans decide what ships.

Given a scheme's official corpus text, the LLM drafts rules in the existing
YAML schema, each tagged with its exact source clause and URL. Drafts are
validated against the CLOSED UserProfile field vocabulary:

- drafts over known fields become engine-schema rules (review_status:
  proposed) written to app/rules/proposed/<scheme_id>.yaml — a directory the
  engine loader NEVER reads, so nothing goes live without human sign-off and
  an explicit move to app/rules/schemes/;
- drafts needing facts the profile can't express are quarantined as
  `blocked_rules` with the proposed new field named — adding a field is a
  schema + wizard + extraction-prompt change, a human decision.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from app.agent.state import UserProfile
from app.ingestion.models import CorpusDoc
from app.llm.router import generate_structured_resilient
from app.rules.engine import Condition, Rule

logger = logging.getLogger(__name__)

PROPOSED_DIR = Path(__file__).resolve().parents[1] / "rules" / "proposed"

# One line per profile field the rules engine can test. A unit test asserts
# this vocabulary and UserProfile.model_fields never drift apart.
FIELD_VOCABULARY = """\
age: int — the person's age in years
gender: "male" | "female" | "other"
marital_status: "married" | "widowed" | "single" | "divorced"
state: str — Indian state of residence, canonical full name (e.g. "Uttar Pradesh")
area: "rural" | "urban"
occupation: str — free-text occupation
is_farmer_with_land: bool — family owns cultivable land in its own name
annual_family_income_inr: int — yearly family income in rupees
social_category: "general" | "sc" | "st" | "obc" | "minority"
has_bpl_card: bool — household is on the Below Poverty Line list
disability_percent: int — certified disability percentage
has_bank_account: bool — holds an individual bank/post-office account
pays_income_tax: bool — person or family member paid income tax
is_student: bool — currently studying
daughter_age: int — age of the (youngest relevant) daughter
family_member_in_govt_service: bool — the applicant or any family member holds a government job
receives_govt_pension_over_10k: bool — family member draws govt pension above Rs 10,000/month
holds_constitutional_or_political_post: bool — self/family holds(-held) constitutional/elected post
is_practicing_registered_professional: bool — self/family is a registered practicing professional
cultivates_crops: bool — actively cultivates crops (owner, tenant, or sharecropper)
has_land_ownership_or_tenure_docs: bool — has land papers or a valid written tenancy agreement
house_type: "kutcha" | "pucca"
owns_motorized_vehicle: bool — household owns a motorised 2/3/4-wheeler or fishing boat
is_pmjay_priority_category: bool — household matches an SECC deprivation/occupational category
has_lpg_connection: bool — household already has an LPG connection
is_street_vendor: bool — sells goods/services from a cart/stall/public space
has_vending_certificate_or_lor: bool — holds a Certificate of Vending or vendor ID, is listed in the ULB vending survey, or holds a LoR
is_vishwakarma_trade_artisan: bool — self-employed artisan in one of the 18 Vishwakarma trades
is_post_matric_student: bool — studying beyond class 10 at a recognized institution
is_pregnant: bool — the person is currently pregnant
single_girl_child: bool — the applicant is the only girl child in the family (no brother)
disability_type: one of autism|cerebral_palsy|intellectual_disability|multiple_disabilities|other
bereavement_event: bool — the family's primary breadwinner has died
receives_other_govt_pension: bool — already draws a pension under another state/central scheme
number_of_children: int — number of children in the family
"""

# `notes` is free text the engine never tests; excluded from the vocabulary.
NON_RULE_FIELDS = {"notes"}

EXTRACT_PROMPT = """You translate Indian welfare-scheme eligibility text into executable rules.

Scheme: {scheme_name} ({scheme_id})
Official page: {page_url}

Official text (the ONLY source you may use):
\"\"\"{official_text}\"\"\"

Available profile fields — a rule may ONLY test these (exact names):
{vocabulary}

Write one rule per checkable criterion:
- kind: "require" (must hold) or "exclude" (must not hold — disqualifying conditions).
- id: short kebab-case (e.g. "age-at-least-18", "exclude-income-tax-payer").
- field / op ("eq","ne","gt","gte","lt","lte") / value. Use `any_of`/`all_of`
  with sub-conditions only when the text itself is an OR/AND of criteria.
- CRITICAL — alternatives are ONE rule with `any_of`, never several require rules.
  When the text lists options where satisfying ANY ONE qualifies — "SC, ST or OBC",
  "EWS/LIG/MIG income bands", "a farmer OR a member of a Self-Help Group" — emit a
  SINGLE require rule whose `when` is `any_of` of the options. Emitting them as
  separate require rules means ALL must hold, which for one field is impossible
  (nobody is both SC and OBC) and wrongly rejects every applicant. Example — the
  text "candidates belonging to SC, ST or OBC": one rule, when =
  any_of[(field social_category eq sc), (field social_category eq st),
  (field social_category eq obc)].
  A single field cannot equal two values; if you find yourself writing two
  require rules on the same field, they are alternatives — combine them.
- clause: the EXACT sentence(s) of official text the rule encodes — copy verbatim,
  never paraphrase, never merge distant sentences.
- ask: one kind plain-language question that would resolve the fact if unknown.
- self_declared: true only for facts the state ultimately verifies against its own
  lists (BPL list membership, SECC category) — the person can claim but not prove them
  in conversation.
Rules for numbers: transcribe thresholds exactly (18 stays 18; "Rs. 2.5 lakh" = 250000
yearly). If the text gives a monthly income limit, convert to yearly and note that in
notes_for_reviewer.

If a real criterion cannot be expressed with the available fields, put it in
blocked_rules with proposed_field (snake_case name + type + one-line meaning) instead
of forcing a wrong encoding.

If a criterion is real but too operational to model (state-specific notification,
enrollment windows, document formalities), list it in simplifications instead.

Output every checkable criterion from the text — do not invent criteria that are not
in the text, and do not skip exclusions.
"""


class ConditionDraft(BaseModel):
    """Relaxed condition: field names unvalidated until checked against the schema."""

    field: str | None = None
    op: str | None = None
    # A list means "matches any of these values" — models sometimes collapse
    # an any_of into a single leaf with a list value (e.g. social_category in
    # [sc, st]); expanded back into any_of below rather than rejected.
    value: bool | int | str | list[bool | int | str] | None = None
    any_of: list["ConditionDraft"] | None = None
    all_of: list["ConditionDraft"] | None = None

    def to_engine_form(self) -> dict:
        if self.any_of is not None:
            return {"any": [c.to_engine_form() for c in self.any_of]}
        if self.all_of is not None:
            return {"all": [c.to_engine_form() for c in self.all_of]}
        if isinstance(self.value, list):
            return {
                "any": [{"field": self.field, "op": self.op, "value": v} for v in self.value]
            }
        return {"field": self.field, "op": self.op, "value": self.value}


class RuleDraft(BaseModel):
    id: str
    kind: str
    when: ConditionDraft
    clause: str
    ask: str
    self_declared: bool = False
    notes_for_reviewer: str = ""


class ProposedField(BaseModel):
    name: str
    type: str
    meaning: str


class BlockedRule(BaseModel):
    criterion: str  # the official clause that could not be encoded
    proposed_field: ProposedField
    suggested_rule_id: str = ""


class ExtractionOutput(BaseModel):
    """What the LLM returns."""

    rules: list[RuleDraft]
    blocked_rules: list[BlockedRule] = []
    simplifications: list[str] = []


class SchemeProposal(BaseModel):
    """Validated pipeline output — the review-queue artifact."""

    scheme_id: str
    scheme_name: str
    extracted_at: str
    source_url: str
    rules: list[Rule]  # engine-schema-valid, review_status="proposed"
    rejected_drafts: list[dict]  # failed validation; kept for the reviewer
    blocked_rules: list[BlockedRule]
    simplifications: list[str]


def official_text(doc: CorpusDoc) -> str:
    """The sections a rule may cite: eligibility and exclusions first, then
    the descriptive sections that often carry criteria on myScheme."""
    parts = []
    for section in ("eligibility", "exclusions", "details", "benefits"):
        body = doc.sections.get(section, "").strip()
        if body:
            parts.append(f"## {section}\n{body}")
    return "\n\n".join(parts)


def validate_draft(draft: RuleDraft, source_url: str) -> Rule:
    """Promote a draft to an engine-schema Rule (raises ValidationError if the
    draft tests unknown fields, bad ops, or malformed conditions)."""
    return Rule.model_validate(
        {
            "id": draft.id,
            "kind": draft.kind,
            "when": draft.when.to_engine_form(),
            "clause": draft.clause,
            "source_url": source_url,
            "ask": draft.ask,
            "self_declared": draft.self_declared,
            "review_status": "proposed",
        }
    )


def compose_or_groups(rules: list[Rule]) -> list[Rule]:
    """Merge separate `require` rules that share a (field, op) into one `any_of`.

    Alternatives the extractor split into parallel require rules — "SC, ST or
    OBC", income bands, age floors for different tracks — are AND-ed by the
    engine when kept separate, which for a single field can never be satisfied
    (nobody is both SC and OBC) and rejects every applicant. Grouping same
    (field, op) leaves into an `any_of` restores OR semantics. Only touches
    `require` leaf rules with 2+ members; ranges (age gte + age lte) differ in
    op and are left alone. Merged rules are flagged for the human reviewer.
    """
    groups: dict[tuple[str, str], list[Rule]] = {}
    order: list[object] = []  # preserves output ordering: group-key or single Rule
    for rule in rules:
        w = rule.when
        is_mergeable_leaf = (
            rule.kind == "require" and w.field is not None and w.any is None and w.all is None
        )
        if is_mergeable_leaf:
            key = (w.field, w.op)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(rule)
        else:
            order.append(rule)

    composed: list[Rule] = []
    for item in order:
        if isinstance(item, Rule):
            composed.append(item)
            continue
        members = groups[item]
        if len(members) < 2:
            composed.append(members[0])
            continue
        field, op = item
        leaves = [Condition(field=field, op=op, value=m.when.value) for m in members]
        merged_ids = [m.id for m in members]
        composed.append(
            Rule(
                id=f"any-{field}",
                kind="require",
                when=Condition(any=leaves),
                clause="; ".join(dict.fromkeys(m.clause for m in members)),
                source_url=members[0].source_url,
                ask=members[0].ask,
                self_declared=any(m.self_declared for m in members),
                review_status="proposed",
                notes_for_reviewer=(
                    f"AUTO-COMPOSED from {len(members)} same-field require rules "
                    f"({', '.join(merged_ids)}) as an OR group — confirm these are "
                    "genuine alternatives, not separate requirements."
                ),
            )
        )
    return composed


def propose_rules(doc: CorpusDoc) -> SchemeProposal:
    prompt = EXTRACT_PROMPT.format(
        scheme_name=doc.name,
        scheme_id=doc.scheme_id,
        page_url=doc.page_url,
        official_text=official_text(doc),
        vocabulary=FIELD_VOCABULARY,
    )
    output = generate_structured_resilient(prompt, ExtractionOutput)

    rules: list[Rule] = []
    rejected: list[dict] = []
    for draft in output.rules:
        try:
            rules.append(validate_draft(draft, doc.page_url))
        except ValidationError as exc:
            logger.warning("draft %s rejected: %s", draft.id, exc)
            rejected.append(
                {"draft": draft.model_dump(exclude_none=True), "error": str(exc)}
            )

    return SchemeProposal(
        scheme_id=doc.scheme_id,
        scheme_name=doc.name,
        extracted_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        source_url=doc.page_url,
        rules=compose_or_groups(rules),
        rejected_drafts=rejected,
        blocked_rules=output.blocked_rules,
        simplifications=output.simplifications,
    )


def write_proposal(proposal: SchemeProposal) -> Path:
    """Write the review-queue YAML. NEVER writes to app/rules/schemes/."""
    PROPOSED_DIR.mkdir(exist_ok=True)
    payload = {
        "scheme_id": proposal.scheme_id,
        "version": proposal.extracted_at,
        "extraction": {
            "extracted_at": proposal.extracted_at,
            "status": "awaiting-human-review",
            "source_url": proposal.source_url,
        },
        "rules": [r.model_dump(exclude_none=True) for r in proposal.rules],
        "blocked_rules": [b.model_dump() for b in proposal.blocked_rules],
        "rejected_drafts": proposal.rejected_drafts,
        "simplifications": proposal.simplifications,
    }
    out = PROPOSED_DIR / f"{proposal.scheme_id}.yaml"
    out.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=88),
        encoding="utf-8",
    )
    return out


def vocabulary_field_names() -> set[str]:
    """Field names promised to the LLM — tested against UserProfile for drift."""
    return {
        line.split(":")[0].strip()
        for line in FIELD_VOCABULARY.splitlines()
        if line.strip()
    }


def profile_rule_fields() -> set[str]:
    return set(UserProfile.model_fields) - NON_RULE_FIELDS
