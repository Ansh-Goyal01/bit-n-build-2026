"use client";

import { IndianRupee } from "lucide-react";

import { type ValueEntry, annualTotal, isRecurring } from "@/lib/benefit-total";
import { useT } from "@/lib/i18n";
import { getScheme } from "@/lib/schemes";
import type { SchemeResult } from "@/lib/types";

/** R6 — estimated benefit value on the report headline. Values come from the
 * static catalog (benefit_values.yaml → schemes.json), which carries ONLY
 * human-verified entries — the same nothing-unverified-is-live invariant as
 * rules, so this section is invisible until entries are certified.
 * Amounts are annualized at the source (amount_inr); recurring entries sum
 * into the headline figure (only the largest pension — see annualTotal),
 * cover/one-time entries list below it. */

type Entry = ValueEntry & { shortName: string };

function entriesFor(results: SchemeResult[]): Entry[] {
  return results.flatMap((r) => {
    const scheme = getScheme(r.scheme_id);
    const value = scheme?.benefit_value;
    if (!scheme || !value) return [];
    return [
      {
        schemeId: r.scheme_id,
        category: scheme.category,
        shortName: scheme.short_name,
        amountInr: value.amount_inr,
        period: value.period,
      },
    ];
  });
}

export function ValueHeadline({ results }: { results: SchemeResult[] }) {
  const t = useT();

  const entries = entriesFor(results);
  if (entries.length === 0) return null;

  const { total, pensionsNotSummed } = annualTotal(entries);

  const rupees = (amount: number) => `₹${amount.toLocaleString("en-IN")}`;
  const entryLine = (e: Entry) => {
    if (isRecurring(e)) return t("results.valuePerYear", { amount: rupees(e.amountInr) });
    if (e.period === "cover") return t("results.valueCover", { amount: rupees(e.amountInr) });
    if (e.period === "one_time") return t("results.valueOneTime", { amount: rupees(e.amountInr) });
    return t("results.valueVaries");
  };

  return (
    <section
      aria-label={t("results.valueTitle")}
      className="print-avoid-break rounded-xl border border-border bg-card p-5 shadow-card"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-verdict-yes-soft text-verdict-yes">
          <IndianRupee className="size-4.5" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1.5">
          <h2 className="font-semibold">{t("results.valueTitle")}</h2>
          {total > 0 && (
            <p className="font-serif text-2xl font-semibold tracking-tight">
              {t("results.valueTotal", { amount: rupees(total) })}
            </p>
          )}
          <ul className="flex flex-col gap-0.5 text-sm leading-relaxed text-muted-foreground">
            {entries.map((e) => (
              <li key={e.schemeId}>
                {e.shortName} — {entryLine(e)}
                {pensionsNotSummed.includes(e.schemeId) && ` (${t("results.valueNotSummed")})`}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {t("results.valueNote")}
          </p>
        </div>
      </div>
    </section>
  );
}
