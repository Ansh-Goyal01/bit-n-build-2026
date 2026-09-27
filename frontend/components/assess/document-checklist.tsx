"use client";

import * as React from "react";
import { ClipboardList } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { useT } from "@/lib/i18n";
import type { DocumentsHave } from "@/lib/packet";
import type { SchemeResult } from "@/lib/types";
import { DocumentTrackerList } from "./application-packet";

/** Consolidated document tracker across the schemes the person can claim.
 *
 * Each scheme's official documents list renders as tickable lines. A known
 * document type (Aadhaar, income certificate…) is one tick shared by every
 * scheme that asks for it. Tick state lives in the report page (and in the
 * case file only if the person chooses to save one); without a controlling
 * parent it is local and ephemeral. On paper the boxes print empty, so the
 * PDF doubles as a physical checklist to carry to the office.
 */
export function DocumentChecklist({
  results,
  have,
  onToggle,
}: {
  results: SchemeResult[];
  have?: DocumentsHave;
  onToggle?: (key: string) => void;
}) {
  const t = useT();
  const [localHave, setLocalHave] = React.useState<DocumentsHave>({});
  const current = have ?? localHave;
  const toggle =
    onToggle ?? ((key: string) => setLocalHave((prev) => ({ ...prev, [key]: !prev[key] })));

  // Parsed lists (current API) show every entitled scheme, including an
  // honest "no documents listed"; raw markdown is the fallback.
  const shown = results.filter((r) => r.document_items !== undefined || r.documents);
  if (shown.length === 0) return null;

  return (
    <section aria-label={t("results.checklistTitle")} className="flex flex-col gap-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
          <ClipboardList className="size-4.5" aria-hidden="true" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-semibold tracking-tight sm:text-2xl">
            {t("results.checklistTitle")}
          </h2>
          <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
            {t("results.checklistLead")}
          </p>
        </div>
      </div>

      {/* avoid-break sits on each scheme block, not the whole card — keeping
          the full card intact would push it to a fresh page and waste one. */}
      <div className="flex flex-col gap-5 rounded-xl border border-border bg-card p-5 print:gap-2 print:border-0 print:p-0">
        {shown.map((result) => (
          <div key={result.scheme_id} className="print-avoid-break">
            <h3 className="mb-2 text-sm font-semibold text-foreground">{result.short_name}</h3>
            {result.document_items !== undefined ? (
              <DocumentTrackerList
                result={result}
                have={current}
                onToggle={toggle}
                showGuides={false}
              />
            ) : (
              <ReactMarkdown
                components={{
                  // Flatten markdown structure to checklist rows; only list
                  // items become tickable.
                  ul: ({ children }) => <ul className="flex flex-col gap-1.5">{children}</ul>,
                  ol: ({ children }) => <ol className="flex flex-col gap-1.5">{children}</ol>,
                  li: ({ children }) => (
                    <li className="list-none">
                      <label className="flex cursor-pointer items-start gap-2.5 text-sm leading-relaxed text-foreground">
                        <input type="checkbox" className="mt-1 size-4 shrink-0 accent-accent" />
                        <span>{children}</span>
                      </label>
                    </li>
                  ),
                  p: ({ children }) => (
                    <p className="mb-1.5 text-sm leading-relaxed text-muted-foreground">
                      {children}
                    </p>
                  ),
                }}
              >
                {result.documents}
              </ReactMarkdown>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
