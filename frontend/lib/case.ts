/** Case file — the whole state of one person's check, kept on THEIR device
 * (opt-in localStorage) or carried as a JSON file between a phone and a CSC
 * computer. Nothing is ever sent to the server except the answers, which the
 * report already sends.
 *
 * Deliberately holds no name, phone or ID number: the answers are the same
 * facts the wizard asks, plus document ticks and operator annotations.
 *
 * Pure functions with type-only imports (node --test); the thin storage and
 * download helpers take their browser objects as arguments. */

import type { Annotations } from "./assisted";
import type { DocumentsHave } from "./packet";
import type { SchemeResult, Verdict } from "./types";
import type { VerdictLike } from "./verdict-diff";
import type { Answers } from "./wizard";

export const CASE_SCHEMA = "adhikaar-case";
export const CASE_VERSION = 1;
export const CASE_STORAGE_KEY = "adhikaar-case-v1";
/** A real case is a few KB; anything far larger is not one of ours. */
export const MAX_CASE_BYTES = 64 * 1024;

const VERDICTS: readonly Verdict[] = [
  "eligible",
  "likely_eligible",
  "need_more_info",
  "not_eligible",
];

export interface CaseFile {
  schema: typeof CASE_SCHEMA;
  version: typeof CASE_VERSION;
  created_at: string;
  updated_at: string;
  lang: string;
  answers: Answers;
  /** Verdicts at the last check — the baseline for "what changed". */
  snapshot: VerdictLike[];
  documents_have: DocumentsHave;
  annotations: Annotations;
  assisted: boolean;
}

export function snapshotOf(results: SchemeResult[]): VerdictLike[] {
  return results.map(({ scheme_id, short_name, verdict }) => ({ scheme_id, short_name, verdict }));
}

export function buildCase(
  previous: CaseFile | null,
  parts: Pick<CaseFile, "lang" | "answers" | "snapshot" | "documents_have" | "annotations" | "assisted">,
  now: Date,
): CaseFile {
  const stamp = now.toISOString();
  // Fields are picked one by one: spreading `parts` would let a caller that
  // passes a whole previous case overwrite the timestamps.
  return {
    schema: CASE_SCHEMA,
    version: CASE_VERSION,
    created_at: previous?.created_at ?? stamp,
    updated_at: stamp,
    lang: parts.lang,
    answers: parts.answers,
    snapshot: parts.snapshot,
    documents_have: parts.documents_have,
    annotations: parts.annotations,
    assisted: parts.assisted,
  };
}

export function caseFileName(now: Date): string {
  return `adhikaar-case-${now.toISOString().slice(0, 10)}.json`;
}

export type ParseResult = { ok: true; value: CaseFile } | { ok: false; error: string };

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

const isShortString = (v: unknown, max = 200): v is string =>
  typeof v === "string" && v.length <= max;

/** Strict validation for an imported file: unknown answer keys, nested
 * values, bad verdicts or a wrong schema/version reject the whole file —
 * a half-trusted case is worse than none. `knownAnswerKeys` is the set of
 * wizard field keys. */
export function parseCaseFile(text: string, knownAnswerKeys: ReadonlySet<string>): ParseResult {
  if (text.length > MAX_CASE_BYTES) return { ok: false, error: "too_large" };
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return { ok: false, error: "not_json" };
  }
  if (!isRecord(raw) || raw.schema !== CASE_SCHEMA) return { ok: false, error: "not_a_case" };
  if (raw.version !== CASE_VERSION) return { ok: false, error: "wrong_version" };

  const { answers, snapshot, documents_have, annotations } = raw;
  if (!isShortString(raw.created_at, 40) || !isShortString(raw.updated_at, 40))
    return { ok: false, error: "invalid" };
  if (!isShortString(raw.lang, 8) || typeof raw.assisted !== "boolean")
    return { ok: false, error: "invalid" };

  if (!isRecord(answers)) return { ok: false, error: "invalid" };
  for (const [key, value] of Object.entries(answers)) {
    if (!knownAnswerKeys.has(key)) return { ok: false, error: "invalid" };
    const primitive =
      value === null || (typeof value === "number" && Number.isFinite(value)) || isShortString(value);
    if (!primitive) return { ok: false, error: "invalid" };
  }

  if (!Array.isArray(snapshot)) return { ok: false, error: "invalid" };
  for (const entry of snapshot) {
    if (
      !isRecord(entry) ||
      !isShortString(entry.scheme_id, 80) ||
      !isShortString(entry.short_name, 80) ||
      !VERDICTS.includes(entry.verdict as Verdict)
    )
      return { ok: false, error: "invalid" };
  }

  if (!isRecord(documents_have)) return { ok: false, error: "invalid" };
  for (const [key, value] of Object.entries(documents_have)) {
    if (!isShortString(key, 120) || typeof value !== "boolean")
      return { ok: false, error: "invalid" };
  }

  if (!isRecord(annotations)) return { ok: false, error: "invalid" };
  for (const [key, value] of Object.entries(annotations)) {
    if (
      !isShortString(key, 160) ||
      !isRecord(value) ||
      typeof value.seen !== "boolean" ||
      !isShortString(value.note, 80)
    )
      return { ok: false, error: "invalid" };
  }

  return {
    ok: true,
    value: {
      schema: CASE_SCHEMA,
      version: CASE_VERSION,
      created_at: raw.created_at,
      updated_at: raw.updated_at,
      lang: raw.lang,
      answers: answers as Answers,
      snapshot: snapshot.map((e) => ({
        scheme_id: e.scheme_id,
        short_name: e.short_name,
        verdict: e.verdict,
      })) as VerdictLike[],
      documents_have: documents_have as DocumentsHave,
      annotations: Object.fromEntries(
        Object.entries(annotations as Record<string, { seen: boolean; note: string }>).map(
          ([key, { seen, note }]) => [key, { seen, note }],
        ),
      ),
      assisted: raw.assisted,
    },
  };
}

// --- thin browser helpers (storage may throw in private mode) ---

export function loadSavedCase(
  storage: Pick<Storage, "getItem">,
  knownAnswerKeys: ReadonlySet<string>,
): CaseFile | null {
  try {
    const text = storage.getItem(CASE_STORAGE_KEY);
    if (!text) return null;
    const parsed = parseCaseFile(text, knownAnswerKeys);
    return parsed.ok ? parsed.value : null;
  } catch {
    return null;
  }
}

export function saveCase(storage: Pick<Storage, "setItem">, value: CaseFile): boolean {
  try {
    storage.setItem(CASE_STORAGE_KEY, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function clearSavedCase(storage: Pick<Storage, "removeItem">): void {
  try {
    storage.removeItem(CASE_STORAGE_KEY);
  } catch {
    // Nothing to clear if storage is unavailable.
  }
}
