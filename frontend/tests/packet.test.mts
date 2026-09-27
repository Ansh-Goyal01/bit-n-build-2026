// Run: npm test (node --test with native type stripping — no test framework).
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildWorksheet,
  documentKey,
  documentTracker,
  packetShareText,
  rankMissingDocuments,
  schemeDocTypes,
  stripMarkdown,
} from "../lib/packet.ts";
import type { DocumentItem, SchemeResult } from "../lib/types.ts";

const item = (text: string, guide_key: string | null = null): DocumentItem => ({
  kind: "item",
  text,
  guide_key,
});

function result(
  scheme_id: string,
  verdict: SchemeResult["verdict"],
  document_items: DocumentItem[],
): SchemeResult {
  return {
    scheme_id,
    scheme_name: `${scheme_id} scheme`,
    short_name: scheme_id.toUpperCase(),
    verdict,
    summary: "",
    reasons: [],
    missing_info: [],
    documents: "",
    how_to_apply: "",
    page_url: `https://example.gov.in/${scheme_id}`,
    references: [],
    dropped_claims: 0,
    document_items,
  };
}

const t = (key: string) => key;

test("known document types share one tick key across schemes", () => {
  assert.equal(documentKey("a", 0, item("Aadhaar Card", "aadhaar")), "doc:aadhaar");
  assert.equal(documentKey("a", 3, item("PAN Card")), "item:a:3");
});

test("priority ranks missing documents by how many schemes they unlock", () => {
  const results = [
    result("a", "eligible", [item("Aadhaar", "aadhaar"), item("Income cert", "income_certificate")]),
    result("b", "likely_eligible", [item("Income cert", "income_certificate")]),
    result("c", "eligible", [item("Income proof", "income_certificate"), item("Photo", "photo")]),
    result("d", "not_eligible", [item("Aadhaar", "aadhaar")]),
  ];
  const ranked = rankMissingDocuments(results, {});
  assert.deepEqual(
    ranked.map((p) => [p.key, p.schemeIds.length]),
    [
      ["income_certificate", 3],
      ["aadhaar", 1],
      ["photo", 1],
    ],
  );
  assert.deepEqual(ranked[0].shortNames, ["A", "B", "C"]);
});

test("ties keep the canonical document order and ticked documents drop out", () => {
  const results = [result("a", "eligible", [item("Photo", "photo"), item("Aadhaar", "aadhaar")])];
  assert.deepEqual(
    rankMissingDocuments(results, {}).map((p) => p.key),
    ["aadhaar", "photo"],
  );
  assert.deepEqual(
    rankMissingDocuments(results, { "doc:aadhaar": true }).map((p) => p.key),
    ["photo"],
  );
});

test("doc types fall back to guide keys when no parsed items exist", () => {
  const r = { ...result("a", "eligible", []), document_guide_keys: ["ration_card"] };
  assert.deepEqual(schemeDocTypes(r), ["ration_card"]);
});

test("tracker counts only tickable items and honours shared ticks", () => {
  const r = result("a", "eligible", [
    { kind: "group", text: "For 1st Loan" },
    item("Aadhaar Card", "aadhaar"),
    item("Certificate of Vending"),
  ]);
  const tracker = documentTracker(r, { "doc:aadhaar": true });
  assert.equal(tracker.lines.length, 2);
  assert.equal(tracker.haveCount, 1);
  assert.deepEqual(
    tracker.missing.map((line) => line.key),
    ["item:a:2"],
  );
});

test("worksheet fills known facts, never invents the rest", () => {
  const rows = buildWorksheet({ age: 62, gender: "female", has_bpl_card: false, state: null });
  const byField = Object.fromEntries(rows.map((row) => [row.field, row]));
  assert.equal(byField.name.filled, false);
  assert.deepEqual([byField.age.value, byField.age.filled], [62, true]);
  assert.deepEqual([byField.has_bpl_card.value, byField.has_bpl_card.filled], [false, true]);
  assert.equal(byField.state.filled, false);
  assert.equal(byField.annual_family_income_inr.filled, false);
});

test("share text lists what is missing, or says honestly that nothing is listed", () => {
  const listed = result("a", "eligible", [item("Aadhaar", "aadhaar"), item("**Land** papers")]);
  const text = packetShareText(listed, { "doc:aadhaar": true }, t);
  assert.match(text, /packet\.shareMissing/);
  assert.match(text, /• Land papers/);
  assert.doesNotMatch(text, /Aadhaar/);
  assert.match(packetShareText(result("b", "eligible", []), {}, t), /packet\.noDocumentsListed/);
});

test("stripMarkdown removes links and emphasis only", () => {
  assert.equal(stripMarkdown("Visit the [portal](https://x.gov.in) **now**"), "Visit the portal now");
});
