"use client";

import { ListOrdered } from "lucide-react";

import { useT } from "@/lib/i18n";
import { type DocumentsHave, rankMissingDocuments } from "@/lib/packet";
import type { SchemeResult } from "@/lib/types";

/** Cross-scheme document priority: which missing document to get first,
 * ranked by how many of the person's schemes it unlocks. Built only from
 * the official documents lists (language-invariant guide keys). */
export function DocumentPriority({
  results,
  have,
  onToggle,
}: {
  results: SchemeResult[];
  have: DocumentsHave;
  onToggle: (key: string) => void;
}) {
  const t = useT();
  const ranked = rankMissingDocuments(results, have);
  const withoutList = results.filter(
    (r) => !(r.document_items ?? []).some((item) => item.kind === "item"),
  ).length;
  if (ranked.length === 0 && withoutList === 0) return null;

  return (
    <section aria-label={t("packet.priorityTitle")} className="flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
          <ListOrdered className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-semibold tracking-tight sm:text-2xl">
            {t("packet.priorityTitle")}
          </h2>
          <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
            {t("packet.priorityLead")}
          </p>
        </div>
      </div>

      {ranked.length === 0 ? (
        <p className="rounded-xl border border-border bg-card p-4 text-sm leading-relaxed text-muted-foreground">
          {t("packet.priorityAllInHand")}
        </p>
      ) : (
        <ol className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4">
          {ranked.map((entry, i) => (
            <li key={entry.key} className="flex items-start gap-3 text-sm leading-relaxed">
              <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-primary-foreground">
                {i + 1}
              </span>
              <div className="flex-1">
                <p className="font-medium text-foreground">
                  {t("packet.priorityItem", {
                    document: t(`docGuides.${entry.key}.name`),
                    count: entry.schemeIds.length,
                    total: results.length,
                  })}
                </p>
                <p className="text-xs text-muted-foreground">
                  {entry.shortNames.join(" · ")} — {t(`docGuides.${entry.key}.where`)}
                </p>
              </div>
              <label className="print-hidden flex shrink-0 cursor-pointer items-center gap-1.5 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={Boolean(have[`doc:${entry.key}`])}
                  onChange={() => onToggle(`doc:${entry.key}`)}
                  className="size-4 accent-accent"
                />
                {t("packet.haveIt")}
              </label>
            </li>
          ))}
        </ol>
      )}

      {withoutList > 0 && (
        <p className="text-xs leading-relaxed text-muted-foreground">
          {t("packet.priorityUnlisted", { count: withoutList })}
        </p>
      )}
    </section>
  );
}
