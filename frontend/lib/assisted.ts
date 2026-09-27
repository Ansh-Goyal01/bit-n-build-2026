/** Assisted mode — a CSC / Jan Seva Kendra operator helping a citizen.
 *
 * The operator can record that they have SEEN the proof behind a
 * self-declared fact (a BPL card, an income certificate). That is an
 * annotation shown next to the verdict, never an input to it: nothing here
 * reads or writes `verdict`, and the engine is never re-run because of it.
 *
 * Pure functions with type-only imports, so `node --test` loads them with
 * native type stripping. */

import type { ApplicationStep, SchemeResult } from "./types";

/** Keep operator notes short: they describe what was seen ("BPL card
 * no. checked"), not the person — and they travel in the case file. */
export const NOTE_MAX_LENGTH = 80;

export interface OperatorAnnotation {
  seen: boolean;
  note: string;
}

/** Keyed by `annotationKey(scheme_id, rule_id)`. */
export type Annotations = Record<string, OperatorAnnotation>;

export function annotationKey(schemeId: string, ruleId: string): string {
  return `${schemeId}:${ruleId}`;
}

export function withAnnotation(
  annotations: Annotations,
  key: string,
  change: Partial<OperatorAnnotation>,
): Annotations {
  const current = annotations[key] ?? { seen: false, note: "" };
  const next = { ...current, ...change };
  return { ...annotations, [key]: { ...next, note: next.note.slice(0, NOTE_MAX_LENGTH) } };
}

export interface VerifiedFact {
  ruleId: string;
  /** The scheme's own verify hint — official-text derived, never generated. */
  text: string;
  note: string;
}

export interface AnnotatedResult {
  /** The engine's result, passed through untouched. */
  result: SchemeResult;
  verified: VerifiedFact[];
  /** Self-declared facts the operator has not yet seen proof for. */
  pending: VerifiedFact[];
}

export function annotate(result: SchemeResult, annotations: Annotations): AnnotatedResult {
  const verified: VerifiedFact[] = [];
  const pending: VerifiedFact[] = [];
  for (const step of result.confirmations ?? []) {
    const annotation = annotations[annotationKey(result.scheme_id, step.rule_id)];
    const fact = { ruleId: step.rule_id, text: step.text, note: annotation?.note ?? "" };
    (annotation?.seen ? verified : pending).push(fact);
  }
  return { result, verified, pending };
}

export interface Handoff {
  verified: VerifiedFact[];
  pending: VerifiedFact[];
  missingDocuments: string[];
  /** The scheme's own offline / CSC application steps, as parsed from the
   * official page — no office is ever named that the page doesn't name. */
  nextSteps: ApplicationStep[];
  officialUrl: string;
}

/** `missingDocuments` comes from the packet's document tracker (the lines
 * not yet ticked), passed in so this module stays import-free. */
export function handoffSummary(
  result: SchemeResult,
  annotations: Annotations,
  missingDocuments: string[],
): Handoff {
  const { verified, pending } = annotate(result, annotations);
  const modes = result.application_modes ?? [];
  const inPerson = modes.find((m) => m.mode === "offline" || m.mode === "csc");
  return {
    verified,
    pending,
    missingDocuments,
    nextSteps: (inPerson?.steps ?? []).filter((step) => step.kind === "step"),
    officialUrl: result.page_url,
  };
}
