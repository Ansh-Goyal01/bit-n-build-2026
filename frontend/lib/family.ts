/** R2 — family mode. One household, several people, one combined report.
 *
 * The wizard stays single-person (its canonical logic is untouched); family
 * mode is a thin layer over it: completed members accumulate in localStorage,
 * household-level answers carry over into the next member's run, and the
 * report link encodes every member (per-member codes joined with "~" — "~" is
 * URL-safe and outside the base64url alphabet, so splitting is unambiguous).
 */

import { type Answers, decodeAnswers, encodeAnswers } from "./wizard";

export const FAMILY_STORAGE_KEY = "adhikaar-family-v1";

/** Answers that describe the household, not the person — these pre-fill the
 * next member's wizard run. Everything else (age, gender, occupation …) is
 * asked fresh per member. */
const HOUSEHOLD_KEYS = [
  "state",
  "area",
  "annual_family_income_inr",
  "pays_income_tax",
  "social_category",
  "has_bpl_card",
  "house_type",
  "has_lpg_connection",
  "owns_motorized_vehicle",
  "family_member_in_govt_service",
  "receives_govt_pension_over_10k",
  "daughter_age",
  "number_of_children",
  "bereavement_event",
  "is_pmjay_priority_category",
] as const;

export function householdAnswers(answers: Answers): Answers {
  return Object.fromEntries(
    HOUSEHOLD_KEYS.flatMap((key) =>
      answers[key] !== null && answers[key] !== undefined ? [[key, answers[key]]] : [],
    ),
  );
}

export function encodeFamily(members: Answers[]): string {
  return members.map(encodeAnswers).join("~");
}

export function decodeFamily(code: string): Answers[] | null {
  const members = code.split("~").map(decodeAnswers);
  if (members.length === 0 || members.some((m) => m === null || Object.keys(m).length === 0)) {
    return null;
  }
  return members as Answers[];
}

export function loadFamilyMembers(): Answers[] {
  try {
    const stored = localStorage.getItem(FAMILY_STORAGE_KEY);
    if (!stored) return [];
    return decodeFamily(stored) ?? [];
  } catch {
    return [];
  }
}

export function saveFamilyMembers(members: Answers[]): void {
  try {
    if (members.length === 0) localStorage.removeItem(FAMILY_STORAGE_KEY);
    else localStorage.setItem(FAMILY_STORAGE_KEY, encodeFamily(members));
  } catch {
    // Storage unavailable — family mode simply won't persist across pages.
  }
}

export function clearFamilyMembers(): void {
  saveFamilyMembers([]);
}
