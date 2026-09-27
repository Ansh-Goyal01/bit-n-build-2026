"use client";

// Print-only compact rendering of a result group. On screen the full
// ResultCards do the explaining; on paper this list states the same facts —
// verdict, summary, cited reasons, what to confirm — in document form,
// without card chrome, expanded quotes, or apply-instructions prose.
import { useT } from "@/lib/i18n";
import type { SchemeResult } from "@/lib/types";

export function PrintSchemeList({ results }: { results: SchemeResult[] }) {
  const t = useT();

  return (
    <ol className="hidden print-block">
      {results.map((result) => (
        <li key={result.scheme_id} className="print-avoid-break mb-4 border-b border-border pb-3">
          <p className="text-sm font-semibold">
            {result.short_name}
            <span className="font-normal text-muted-foreground"> — {result.scheme_name}</span>
            {" · "}
            {t(`verdicts.${result.verdict}`)}
          </p>
          <p className="mt-1 text-sm leading-snug">{result.summary}</p>
          {result.reasons.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-sm leading-snug">
              {result.reasons.map((reason, i) => (
                <li key={i}>
                  {reason.text}
                  {reason.citations[0] && (
                    <span className="text-muted-foreground"> ({reason.citations[0].section})</span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {(result.confirm_before_applying?.length ?? 0) > 0 && (
            <p className="mt-1 text-sm leading-snug">
              {t("results.beforeApply")} {result.confirm_before_applying?.join("; ")}
            </p>
          )}
          {result.missing_info.length > 0 && (
            <p className="mt-1 text-sm leading-snug">
              {t("results.confirm")}
              {result.missing_info.join("; ")}
            </p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">{result.page_url}</p>
        </li>
      ))}
    </ol>
  );
}
