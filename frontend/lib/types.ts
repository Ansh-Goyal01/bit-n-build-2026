/** Mirrors backend/app/agent/state.py + app/api/schemas.py */

export type Verdict = "eligible" | "likely_eligible" | "not_eligible" | "need_more_info";

export interface VerifiedCitation {
  chunk_id: string;
  quote: string;
  section: string;
  source_url: string;
}

export interface VerifiedReason {
  text: string;
  citations: VerifiedCitation[];
}

export interface NearMissCondition {
  field: string;
  op: "eq" | "ne" | "gt" | "gte" | "lt" | "lte";
  value: boolean | number | string;
}

/** R1 — a scheme blocked by exactly one rule; resolving it alone would
 * make the person eligible. Computed by the deterministic rules engine. */
export interface NearMiss {
  rule_id: string;
  kind: "require" | "exclude";
  clause: string;
  source_url: string;
  ask: string;
  unlocked_verdict: Verdict;
  conditions: NearMissCondition[];
}

/** One line of the official application process — split, never rewritten. */
export interface ApplicationStep {
  kind: "step" | "heading" | "note";
  text: string;
}

export interface ApplicationMode {
  mode: "online" | "offline" | "csc" | "other";
  steps: ApplicationStep[];
  links: string[];
}

/** One line of the official documents list; only `item` lines are tickable. */
export interface DocumentItem {
  kind: "item" | "group" | "note";
  text: string;
  guide_key?: string | null;
}

/** A self-declared fact behind a likely_eligible verdict, keyed by rule id. */
export interface ConfirmationStep {
  rule_id: string;
  text: string;
}

export interface SchemeResult {
  scheme_id: string;
  scheme_name: string;
  short_name: string;
  verdict: Verdict;
  summary: string;
  reasons: VerifiedReason[];
  missing_info: string[];
  confirm_before_applying?: string[];
  documents: string;
  /** R4 — language-invariant keys of common documents detected in `documents`;
   * localized how-to guides render per key (docGuides dictionary). */
  document_guide_keys?: string[];
  how_to_apply: string;
  page_url: string;
  references: { title: string; url: string }[];
  dropped_claims: number;
  near_miss?: NearMiss | null;
  /** Application packet — set only on eligible / likely_eligible results. */
  application_modes?: ApplicationMode[];
  document_items?: DocumentItem[];
  confirmations?: ConfirmationStep[];
}

export interface UserProfile {
  age?: number | null;
  gender?: string | null;
  marital_status?: string | null;
  state?: string | null;
  area?: string | null;
  occupation?: string | null;
  is_farmer_with_land?: boolean | null;
  annual_family_income_inr?: number | null;
  social_category?: string | null;
  has_bpl_card?: boolean | null;
  disability_percent?: number | null;
  has_bank_account?: boolean | null;
  pays_income_tax?: boolean | null;
  is_student?: boolean | null;
  daughter_age?: number | null;
  family_member_in_govt_service?: boolean | null;
  receives_govt_pension_over_10k?: boolean | null;
  holds_constitutional_or_political_post?: boolean | null;
  is_practicing_registered_professional?: boolean | null;
  cultivates_crops?: boolean | null;
  has_land_ownership_or_tenure_docs?: boolean | null;
  house_type?: "kutcha" | "pucca" | null;
  owns_motorized_vehicle?: boolean | null;
  is_pmjay_priority_category?: boolean | null;
  has_lpg_connection?: boolean | null;
  is_street_vendor?: boolean | null;
  has_vending_certificate_or_lor?: boolean | null;
  is_vishwakarma_trade_artisan?: boolean | null;
  is_pregnant?: boolean | null;
  is_post_matric_student?: boolean | null;
  single_girl_child?: boolean | null;
  disability_type?:
    | "autism"
    | "cerebral_palsy"
    | "intellectual_disability"
    | "multiple_disabilities"
    | "other"
    | null;
  bereavement_event?: boolean | null;
  receives_other_govt_pension?: boolean | null;
  number_of_children?: number | null;
  notes?: string;
}

export interface AssessResponse {
  status: "ok" | "need_info";
  question: string | null;
  profile: UserProfile;
  results: SchemeResult[];
  /** Summaries fell back to fixed templates (LLM unavailable); verdicts,
   * reasons and packets are unaffected. */
  explanations_simplified?: boolean;
}
