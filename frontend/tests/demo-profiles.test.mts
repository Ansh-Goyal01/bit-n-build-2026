// Run: npm test (node --test with native type stripping — no test framework).
import assert from "node:assert/strict";
import { test } from "node:test";

import { DEMO_PROFILES } from "../lib/demo-profiles.ts";
import { STEPS, answersToProfile, decodeAnswers, encodeAnswers } from "../lib/wizard.ts";

const FIELDS = new Map(STEPS.flatMap((step) => step.fields.map((f) => [f.key, f] as const)));

test("every demo answer is a real wizard field with a valid value", () => {
  for (const demo of DEMO_PROFILES) {
    for (const [key, value] of Object.entries(demo.answers)) {
      const field = FIELDS.get(key);
      assert.ok(field, `${demo.id}: unknown field ${key}`);
      if (field.type === "number") {
        assert.equal(typeof value, "number", `${demo.id}.${key}`);
        if (field.min !== undefined) assert.ok((value as number) >= field.min);
        if (field.max !== undefined) assert.ok((value as number) <= field.max);
      } else if (field.options) {
        const allowed = field.options.map((o) => o.value);
        assert.ok(allowed.includes(value as string), `${demo.id}.${key}=${value}`);
      }
    }
  }
});

test("demo answers survive the share-link round trip", () => {
  for (const demo of DEMO_PROFILES) {
    assert.deepEqual(decodeAnswers(encodeAnswers(demo.answers)), demo.answers);
  }
});

test("every demo profile lives in Uttar Pradesh", () => {
  for (const demo of DEMO_PROFILES) {
    assert.equal(answersToProfile(demo.answers).state, "Uttar Pradesh");
  }
});
