"use client";

import * as React from "react";
import { ArrowRight, FlaskConical, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, assess } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { SchemeResult, UserProfile } from "@/lib/types";
import { type VerdictChange, diffVerdicts } from "@/lib/verdict-diff";
import { VerdictBadge } from "./verdict-badge";

type SimState =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "error"; message: string }
  | { kind: "done"; changes: VerdictChange[] };

/** What-if simulator — re-runs the REAL rules engine (same /api/assess call
 * as the report) with an edited copy of the profile and shows only the
 * verdicts that would flip. The report above stays untouched; nothing here is
 * stored. Exposes the three fields most rule thresholds hinge on. */
export function WhatIf({
  profile,
  baseline,
  lang,
}: {
  profile: UserProfile;
  baseline: SchemeResult[];
  lang: string;
}) {
  const t = useT();
  const [age, setAge] = React.useState(profile.age != null ? String(profile.age) : "");
  const [income, setIncome] = React.useState(
    profile.annual_family_income_inr != null ? String(profile.annual_family_income_inr) : "",
  );
  const [hasBpl, setHasBpl] = React.useState(profile.has_bpl_card === true);
  const [sim, setSim] = React.useState<SimState>({ kind: "idle" });

  const runSimulation = async () => {
    setSim({ kind: "busy" });
    const draft: UserProfile = {
      ...profile,
      age: age.trim() === "" ? profile.age : Number(age),
      annual_family_income_inr:
        income.trim() === "" ? profile.annual_family_income_inr : Number(income),
      has_bpl_card: hasBpl,
    };
    try {
      const response = await assess("", draft, lang);
      setSim({ kind: "done", changes: diffVerdicts(baseline, response.results) });
    } catch (error) {
      setSim({
        kind: "error",
        message: error instanceof ApiError ? error.message : t("whatIf.error"),
      });
    }
  };

  return (
    <section
      aria-label={t("whatIf.title")}
      className="print-hidden flex flex-col gap-5"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
          <FlaskConical className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-semibold tracking-tight sm:text-2xl">
            {t("whatIf.title")}
          </h2>
          <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
            {t("whatIf.lead")}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="what-if-age" label={t("whatIf.age")}>
            <Input
              type="number"
              inputMode="numeric"
              min={0}
              max={120}
              value={age}
              onChange={(e) => setAge(e.target.value)}
            />
          </Field>
          <Field id="what-if-income" label={t("whatIf.income")}>
            <Input
              type="number"
              inputMode="numeric"
              min={0}
              value={income}
              onChange={(e) => setIncome(e.target.value)}
            />
          </Field>
        </div>
        <label className="flex w-fit cursor-pointer items-center gap-2.5 text-sm font-medium text-foreground">
          <input
            type="checkbox"
            className="size-4 accent-accent"
            checked={hasBpl}
            onChange={(e) => setHasBpl(e.target.checked)}
          />
          {t("whatIf.bplCard")}
        </label>

        <Button
          variant="secondary"
          className="w-fit"
          disabled={sim.kind === "busy"}
          onClick={() => void runSimulation()}
        >
          {sim.kind === "busy" ? (
            <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight className="size-4" aria-hidden="true" />
          )}
          {sim.kind === "busy" ? t("whatIf.running") : t("whatIf.run")}
        </Button>

        <div aria-live="polite">
          {sim.kind === "error" && (
            <p role="alert" className="text-sm leading-relaxed text-destructive">
              {sim.message}
            </p>
          )}
          {sim.kind === "done" && sim.changes.length === 0 && (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {t("whatIf.noChange")}
            </p>
          )}
          {sim.kind === "done" && sim.changes.length > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {t("whatIf.changesHeading")}
              </h3>
              <ul className="flex flex-col gap-2">
                {sim.changes.map((change) => (
                  <li
                    key={change.scheme_id}
                    className="flex flex-wrap items-center gap-2 text-sm leading-relaxed"
                  >
                    <span className="font-medium text-foreground">{change.short_name}</span>
                    <VerdictBadge verdict={change.before} />
                    <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden="true" />
                    <VerdictBadge verdict={change.after} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
