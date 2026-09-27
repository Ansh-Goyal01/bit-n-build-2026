// Run: npm test (node --test with native type stripping — no test framework).
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  NOTE_MAX_LENGTH,
  annotate,
  annotationKey,
  handoffSummary,
  withAnnotation,
} from "../lib/assisted.ts";
import {
  CASE_STORAGE_KEY,
  MAX_CASE_BYTES,
  buildCase,
  caseFileName,
  loadSavedCase,
  parseCaseFile,
  saveCase,
  snapshotOf,
} from "../lib/case.ts";
import type { SchemeResult } from "../lib/types.ts";
import { diffSinceLastCheck, diffVerdicts, isEmptyDiff } from "../lib/verdict-diff.ts";
import { STEPS } from "../lib/wizard.ts";

const KEYS = new Set(STEPS.flatMap((step) => step.fields.map((f) => f.key)));

function result(overrides: Partial<SchemeResult> = {}): SchemeResult {
  return {
    scheme_id: "wpup",
    scheme_name: "Widow Pension - Uttar Pradesh",
    short_name: "UP-WIDOW",
    verdict: "likely_eligible",
    summary: "",
    reasons: [],
    missing_info: [],
    page_url: "https://www.myscheme.gov.in/schemes/wpup",
    confirmations: [
      { rule_id: "uttar-pradesh-resident", text: "Keep proof of residence ready." },
      { rule_id: "bpl", text: "Carry your BPL card." },
    ],
    application_modes: [
      { mode: "online", steps: [{ kind: "step", text: "Visit the portal." }], links: [] },
      {
        mode: "offline",
        steps: [
          { kind: "heading", text: "At the office" },
          { kind: "step", text: "Submit the form at the **Block office**." },
        ],
        links: [],
      },
    ],
    ...overrides,
  } as SchemeResult;
}

// --- assisted mode ---

test("operator annotations never change the verdict or the result", () => {
  const original = result();
  const frozen = JSON.stringify(original);
  const annotations = withAnnotation({}, annotationKey("wpup", "bpl"), { seen: true, note: "card seen" });
  const annotated = annotate(original, annotations);
  assert.equal(annotated.result, original);
  assert.equal(annotated.result.verdict, "likely_eligible");
  assert.equal(JSON.stringify(original), frozen);
  assert.deepEqual(annotated.verified.map((f) => f.ruleId), ["bpl"]);
  assert.deepEqual(annotated.pending.map((f) => f.ruleId), ["uttar-pradesh-resident"]);
});

test("annotations are keyed per scheme, and notes are capped", () => {
  const annotations = withAnnotation({}, annotationKey("other", "bpl"), { seen: true });
  assert.equal(annotate(result(), annotations).verified.length, 0);
  const long = withAnnotation({}, "k", { note: "x".repeat(200) });
  assert.equal(long.k.note.length, NOTE_MAX_LENGTH);
});

test("hand-off uses only the scheme's own offline steps and link", () => {
  const annotations = withAnnotation({}, annotationKey("wpup", "bpl"), { seen: true });
  const handoff = handoffSummary(result(), annotations, ["Aadhaar Card"]);
  assert.deepEqual(handoff.verified.map((f) => f.ruleId), ["bpl"]);
  assert.deepEqual(handoff.missingDocuments, ["Aadhaar Card"]);
  assert.deepEqual(handoff.nextSteps.map((s) => s.text), ["Submit the form at the **Block office**."]);
  assert.equal(handoff.officialUrl, "https://www.myscheme.gov.in/schemes/wpup");
  const onlineOnly = handoffSummary(result({ application_modes: [] }), {}, []);
  assert.deepEqual(onlineOnly.nextSteps, []);
});

// --- case file ---

function sampleCase() {
  return buildCase(
    null,
    {
      lang: "hi",
      answers: { age: 62, state: "Uttar Pradesh", has_bpl_card: "yes" },
      snapshot: snapshotOf([result()]),
      documents_have: { "doc:aadhaar": true },
      annotations: withAnnotation({}, annotationKey("wpup", "bpl"), { seen: true, note: "seen" }),
      assisted: true,
    },
    new Date("2026-09-27T10:00:00Z"),
  );
}

test("case export → import round trip is lossless", () => {
  const value = sampleCase();
  const parsed = parseCaseFile(JSON.stringify(value), KEYS);
  assert.ok(parsed.ok);
  assert.deepEqual(parsed.value, value);
  assert.equal(caseFileName(new Date("2026-09-27T10:00:00Z")), "adhikaar-case-2026-09-27.json");
});

test("re-saving keeps created_at and moves updated_at", () => {
  const first = sampleCase();
  const next = buildCase(first, { ...first, lang: "en" }, new Date("2026-10-01T09:00:00Z"));
  assert.equal(next.created_at, first.created_at);
  assert.equal(next.updated_at, "2026-10-01T09:00:00.000Z");
});

test("malformed, oversized, foreign and wrong-version files are rejected", () => {
  const value = sampleCase();
  const reject = (text: string, error: string) => {
    const parsed = parseCaseFile(text, KEYS);
    assert.equal(parsed.ok, false);
    if (!parsed.ok) assert.equal(parsed.error, error);
  };
  reject("{not json", "not_json");
  reject(JSON.stringify({ ...value, schema: "something-else" }), "not_a_case");
  reject(JSON.stringify({ ...value, version: 2 }), "wrong_version");
  reject(" ".repeat(MAX_CASE_BYTES + 1), "too_large");
  reject(JSON.stringify({ ...value, answers: { full_name: "Asha" } }), "invalid");
  reject(JSON.stringify({ ...value, answers: { age: { nested: 1 } } }), "invalid");
  reject(
    JSON.stringify({ ...value, snapshot: [{ scheme_id: "x", short_name: "X", verdict: "maybe" }] }),
    "invalid",
  );
  reject(JSON.stringify({ ...value, documents_have: { "doc:aadhaar": "yes" } }), "invalid");
  reject(JSON.stringify({ ...value, annotations: { k: { seen: true } } }), "invalid");
});

test("saved case loads back from storage; a corrupt entry reads as none", () => {
  const store = new Map<string, string>();
  const storage = {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  };
  assert.ok(saveCase(storage, sampleCase()));
  assert.deepEqual(loadSavedCase(storage, KEYS), sampleCase());
  store.set(CASE_STORAGE_KEY, "{broken");
  assert.equal(loadSavedCase(storage, KEYS), null);
});

// --- what changed ---

const v = (scheme_id: string, verdict: SchemeResult["verdict"]) => ({
  scheme_id,
  short_name: scheme_id.toUpperCase(),
  verdict,
});

test("diff classifies unlocked, lost, changed and newly added schemes", () => {
  const before = [v("a", "not_eligible"), v("b", "eligible"), v("c", "eligible"), v("d", "need_more_info")];
  const after = [
    v("a", "likely_eligible"),
    v("b", "not_eligible"),
    v("c", "likely_eligible"),
    v("d", "need_more_info"),
    v("e", "eligible"),
    v("f", "not_eligible"),
  ];
  const diff = diffSinceLastCheck(before, after);
  assert.deepEqual(diff.unlocked.map((c) => c.scheme_id), ["a"]);
  assert.deepEqual(diff.lost.map((c) => c.scheme_id), ["b"]);
  assert.deepEqual(diff.changed.map((c) => c.scheme_id), ["c"]);
  assert.deepEqual(diff.added.map((r) => r.scheme_id), ["e"]);
  assert.ok(isEmptyDiff(diffSinceLastCheck(after, after)));
});

test("what-if diff keeps its original behaviour", () => {
  const changes = diffVerdicts([v("a", "not_eligible"), v("b", "eligible")], [v("a", "eligible"), v("c", "eligible")]);
  assert.deepEqual(changes, [{ scheme_id: "a", short_name: "A", before: "not_eligible", after: "eligible" }]);
});
