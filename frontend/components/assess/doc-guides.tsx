"use client";

import { Landmark } from "lucide-react";

import { useT } from "@/lib/i18n";
import { KNOWN_DOC_KEYS } from "@/lib/packet";
import type { SchemeResult } from "@/lib/types";

/** R4 — how-to guides for the document types the report's checklists mention.
 * Keys arrive language-invariant from the backend (document_guide_keys);
 * all content renders from the docGuides dictionary. Order follows KNOWN_DOC_KEYS
 * so the section is stable across schemes and languages. */

export function DocGuides({ results }: { results: SchemeResult[] }) {
  const t = useT();

  const mentioned = new Set(results.flatMap((r) => r.document_guide_keys ?? []));
  const keys = KNOWN_DOC_KEYS.filter((key) => mentioned.has(key));
  if (keys.length === 0) return null;

  return (
    <section aria-label={t("docGuides.title")} className="flex flex-col gap-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
          <Landmark className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-semibold tracking-tight sm:text-2xl">
            {t("docGuides.title")}
          </h2>
          <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
            {t("docGuides.lead")}
          </p>
        </div>
      </div>

      {/* Print-only: one line per document — same facts, no card chrome. */}
      <ul className="hidden print-block">
        {keys.map((key) => (
          <li key={key} className="mb-1 text-sm leading-snug">
            <span className="font-semibold">{t(`docGuides.${key}.name`)}</span>
            {" — "}
            {t(`docGuides.${key}.where`)} {t(`docGuides.${key}.cost`)} {t(`docGuides.${key}.time`)}
          </li>
        ))}
      </ul>

      <div className="print-hidden grid gap-4 sm:grid-cols-2">
        {keys.map((key) => (
          <div
            key={key}
            className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5 shadow-card"
          >
            <h3 className="font-semibold">{t(`docGuides.${key}.name`)}</h3>
            <dl className="flex flex-col gap-1.5 text-sm leading-relaxed">
              <div>
                <dt className="inline font-medium text-foreground">
                  {t("docGuides.whereLabel")}:{" "}
                </dt>
                <dd className="inline text-muted-foreground">{t(`docGuides.${key}.where`)}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-foreground">
                  {t("docGuides.costLabel")}:{" "}
                </dt>
                <dd className="inline text-muted-foreground">{t(`docGuides.${key}.cost`)}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-foreground">
                  {t("docGuides.timeLabel")}:{" "}
                </dt>
                <dd className="inline text-muted-foreground">{t(`docGuides.${key}.time`)}</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
