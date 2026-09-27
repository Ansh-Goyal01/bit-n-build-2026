// Run: npm test (node --test with native type stripping — no test framework).
import assert from "node:assert/strict";
import { test } from "node:test";

import { annualTotal } from "../lib/benefit-total.ts";

const entry = (schemeId: string, category: string, amountInr: number, period = "month") => ({
  schemeId,
  category,
  amountInr,
  period,
});

test("only the largest pension counts toward the yearly total", () => {
  const { total, pensionsNotSummed } = annualTotal([
    entry("ignwps", "pension", 3600),
    entry("wpup", "pension", 12000),
    entry("pm-kisan", "farmers", 6000, "year"),
  ]);
  assert.equal(total, 18000);
  assert.deepEqual(pensionsNotSummed, ["ignwps"]);
});

test("non-recurring entries never enter the total", () => {
  const { total, pensionsNotSummed } = annualTotal([
    entry("pmuy", "household", 1600, "one_time"),
    entry("ksy", "household", 0, "varies"),
  ]);
  assert.equal(total, 0);
  assert.deepEqual(pensionsNotSummed, []);
});
