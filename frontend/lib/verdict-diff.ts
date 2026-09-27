/** Verdict diffs — shared by the what-if simulator and the case file's
 * "what changed since last time". Pure, type-only imports (node --test). */

import type { Verdict } from "./types";

export interface VerdictLike {
  scheme_id: string;
  short_name: string;
  verdict: Verdict;
}

export interface VerdictChange {
  scheme_id: string;
  short_name: string;
  before: Verdict;
  after: Verdict;
}

const entitled = (verdict: Verdict) => verdict === "eligible" || verdict === "likely_eligible";

/** Diff two result sets by scheme; order follows the newer run. Schemes
 * present in only one run are not "changes" — see `diffSinceLastCheck`. */
export function diffVerdicts(baseline: VerdictLike[], next: VerdictLike[]): VerdictChange[] {
  const before = new Map(baseline.map((r) => [r.scheme_id, r.verdict]));
  return next
    .filter((r) => before.has(r.scheme_id) && before.get(r.scheme_id) !== r.verdict)
    .map((r) => ({
      scheme_id: r.scheme_id,
      short_name: r.short_name,
      before: before.get(r.scheme_id)!,
      after: r.verdict,
    }));
}

export interface CaseDiff {
  /** Was not eligible / unanswered, now eligible or likely eligible. */
  unlocked: VerdictChange[];
  /** Was eligible or likely eligible, now not. */
  lost: VerdictChange[];
  /** Any other verdict change (e.g. eligible ↔ likely eligible). */
  changed: VerdictChange[];
  /** Entitled now, and absent from the last check altogether. */
  added: VerdictLike[];
}

export function diffSinceLastCheck(previous: VerdictLike[], current: VerdictLike[]): CaseDiff {
  const changes = diffVerdicts(previous, current);
  const known = new Set(previous.map((r) => r.scheme_id));
  return {
    unlocked: changes.filter((c) => entitled(c.after) && !entitled(c.before)),
    lost: changes.filter((c) => entitled(c.before) && !entitled(c.after)),
    changed: changes.filter((c) => entitled(c.before) === entitled(c.after)),
    added: current.filter((r) => !known.has(r.scheme_id) && entitled(r.verdict)),
  };
}

export function isEmptyDiff(diff: CaseDiff): boolean {
  return (
    diff.unlocked.length + diff.lost.length + diff.changed.length + diff.added.length === 0
  );
}
