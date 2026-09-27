"use client";

import { Sparkles } from "lucide-react";

import { useT } from "@/lib/i18n";
import type { NearMiss, NearMissCondition } from "@/lib/types";
import { CitationChip } from "./citation-chip";

/** Localized rendering for the numeric thresholds people can actually act
 * on (age, income). Anything else falls back to the rule's own question,
 * which arrives already translated from the backend. */
function conditionText(
  condition: NearMissCondition,
  t: ReturnType<typeof useT>,
): string | null {
  const { field, op, value } = condition;
  if (typeof value !== "number") return null;
  if (field === "age") {
    if (op === "gte" || op === "gt")
      return t("nearMiss.needAgeAtLeast", { value: op === "gt" ? value + 1 : value });
    if (op === "lte" || op === "lt")
      return t("nearMiss.needAgeAtMost", { value: op === "lt" ? value - 1 : value });
  }
  if (field === "annual_family_income_inr") {
    const amount = value.toLocaleString("en-IN");
    if (op === "lte" || op === "lt") return t("nearMiss.needIncomeAtMost", { amount });
    if (op === "gte" || op === "gt") return t("nearMiss.needIncomeAtLeast", { amount });
  }
  return null;
}

/** R1 — shown on a not_eligible card that is exactly one rule away from an
 * eligible verdict. Everything shown is deterministic engine output. */
export function NearMissNotice({ nearMiss }: { nearMiss: NearMiss }) {
  const t = useT();
  const rendered = nearMiss.conditions
    .map((c) => conditionText(c, t))
    .filter((text): text is string => text !== null);

  return (
    <div className="rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
      <p className="flex items-center gap-1.5 font-medium">
        <Sparkles className="size-4 shrink-0" aria-hidden="true" />
        {t("nearMiss.title")}
      </p>
      <p className="mt-1">
        {nearMiss.unlocked_verdict === "eligible"
          ? t("nearMiss.bodyEligible")
          : t("nearMiss.bodyLikely")}
      </p>
      {rendered.length > 0 ? (
        <ul className="mt-1.5 list-disc space-y-1 pl-5">
          {rendered.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5">
          {t("nearMiss.ruleAsks")} {nearMiss.ask}
        </p>
      )}
      <span className="mt-2 flex">
        <CitationChip
          citation={{
            chunk_id: `rule:${nearMiss.rule_id}`,
            quote: nearMiss.clause,
            section: nearMiss.kind === "exclude" ? "exclusions" : "eligibility",
            source_url: nearMiss.source_url,
          }}
        />
      </span>
    </div>
  );
}
