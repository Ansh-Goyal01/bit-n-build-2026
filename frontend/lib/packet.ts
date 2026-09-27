/** Application packet logic — pure functions, no React, no runtime imports.
 *
 * Kept import-free (type-only imports are erased) so `node --test` can run
 * it directly with Node's native type stripping. Every list here is built
 * from engine output and the official text the backend parsed: nothing is
 * invented — a scheme whose page lists no documents gets no documents.
 */

import type { DocumentItem, SchemeResult, UserProfile, Verdict } from "./types";

/** Document types with a localized how-to guide (backend doc_guides.py), in
 * display order — also the tie-break order for the cross-scheme priority. */
export const KNOWN_DOC_KEYS = [
  "aadhaar",
  "bank_account",
  "caste_certificate",
  "income_certificate",
  "bpl_card",
  "ration_card",
  "land_records",
  "disability_certificate",
  "photo",
  "age_proof",
  "residence_proof",
  "death_certificate",
] as const;

/** Which documents a person has ticked, keyed by `documentKey`. */
export type DocumentsHave = Record<string, boolean>;

export function isEntitled(verdict: Verdict): boolean {
  return verdict === "eligible" || verdict === "likely_eligible";
}

/** Tick-state key for one document line. A known document type is shared
 * across schemes (holding an Aadhaar card satisfies every list asking for
 * it); anything else is specific to its scheme and position. */
export function documentKey(schemeId: string, index: number, item: DocumentItem): string {
  return item.guide_key ? `doc:${item.guide_key}` : `item:${schemeId}:${index}`;
}

/** Known document types one scheme's official list asks for. */
export function schemeDocTypes(result: SchemeResult): string[] {
  const fromItems = (result.document_items ?? [])
    .filter((item) => item.kind === "item" && item.guide_key)
    .map((item) => item.guide_key as string);
  const keys = fromItems.length > 0 ? fromItems : (result.document_guide_keys ?? []);
  return [...new Set(keys)];
}

export interface DocumentPriority {
  key: string;
  schemeIds: string[];
  shortNames: string[];
}

/** Missing documents ranked by how many of the person's schemes each one
 * unlocks — "get an income certificate: needed for 3 of your schemes".
 * Ties keep KNOWN_DOC_KEYS order so the list is stable across renders. */
export function rankMissingDocuments(
  results: SchemeResult[],
  have: DocumentsHave,
): DocumentPriority[] {
  const needs = new Map<string, SchemeResult[]>();
  for (const result of results.filter((r) => isEntitled(r.verdict))) {
    for (const key of schemeDocTypes(result)) {
      if (have[`doc:${key}`]) continue;
      needs.set(key, [...(needs.get(key) ?? []), result]);
    }
  }
  const order = (key: string) => {
    const index = (KNOWN_DOC_KEYS as readonly string[]).indexOf(key);
    return index === -1 ? KNOWN_DOC_KEYS.length : index;
  };
  return [...needs.entries()]
    .sort(([a, ra], [b, rb]) => rb.length - ra.length || order(a) - order(b))
    .map(([key, schemes]) => ({
      key,
      schemeIds: schemes.map((r) => r.scheme_id),
      shortNames: schemes.map((r) => r.short_name),
    }));
}

export interface TrackerLine {
  key: string;
  item: DocumentItem;
}

/** A scheme's tickable document lines plus how many are already in hand. */
export function documentTracker(
  result: SchemeResult,
  have: DocumentsHave,
): { lines: TrackerLine[]; missing: TrackerLine[]; haveCount: number } {
  const lines = (result.document_items ?? []).flatMap((item, index) =>
    item.kind === "item" ? [{ key: documentKey(result.scheme_id, index, item), item }] : [],
  );
  const missing = lines.filter((line) => !have[line.key]);
  return { lines, missing, haveCount: lines.length - missing.length };
}

/** Generic applicant fields most welfare forms ask for. Deliberately NOT a
 * scheme's official form — the UI labels it a worksheet. Name is always
 * left to the person: Adhikaar never asks for it. */
export const WORKSHEET_FIELDS = [
  "name",
  "age",
  "gender",
  "social_category",
  "annual_family_income_inr",
  "state",
  "area",
  "has_bpl_card",
  "has_bank_account",
] as const;

export type WorksheetField = (typeof WORKSHEET_FIELDS)[number];

export interface WorksheetRow {
  field: WorksheetField;
  /** Canonical value from the check (localized by the component), or null. */
  value: string | number | boolean | null;
  filled: boolean;
}

export function buildWorksheet(profile: UserProfile): WorksheetRow[] {
  return WORKSHEET_FIELDS.map((field) => {
    const raw = field === "name" ? null : profile[field];
    const value = raw === undefined || raw === "" ? null : (raw as WorksheetRow["value"]);
    return { field, value, filled: value !== null };
  });
}

type Translate = (key: string, params?: Record<string, string | number>) => string;

/** Plain-text packet summary for a WhatsApp share — scheme, verdict, what
 * is still missing, and the official link. No personal facts: the person
 * chooses who receives it, and the worksheet values stay on the device. */
export function packetShareText(
  result: SchemeResult,
  have: DocumentsHave,
  t: Translate,
): string {
  const { missing, lines } = documentTracker(result, have);
  const parts = [
    `${result.scheme_name} (${result.short_name}) — ${t(`verdicts.${result.verdict}`)}`,
  ];
  if (lines.length === 0) {
    parts.push(t("packet.noDocumentsListed"));
  } else if (missing.length > 0) {
    parts.push(t("packet.shareMissing"));
    parts.push(...missing.map((line) => `• ${stripMarkdown(line.item.text)}`));
  } else {
    parts.push(t("packet.shareAllDocuments"));
  }
  for (const step of result.confirmations ?? []) parts.push(`✓ ${step.text}`);
  if (result.page_url) parts.push(result.page_url);
  return parts.join("\n");
}

/** Markdown emphasis/links → plain text, for share text and print lines. */
export function stripMarkdown(text: string): string {
  return text
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/(^|\s)_([^_]+)_(?=\s|$)/g, "$1$2")
    .trim();
}
