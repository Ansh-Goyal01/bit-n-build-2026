"use client";

import { useState } from "react";
import { ChevronDown, ClipboardCheck, ExternalLink, FileText, Landmark } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { SchemeLevelBadge } from "@/components/schemes/scheme-level-badge";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ReadAloud } from "@/components/ui/read-aloud";
import type { SchemeResult } from "@/lib/types";
import { CitationChip } from "./citation-chip";
import { NearMissNotice } from "./near-miss-notice";
import { VerdictBadge } from "./verdict-badge";

function Expandable({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="print-hidden flex w-full items-center justify-between py-3 text-sm font-medium text-foreground transition-colors hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <span className="flex items-center gap-2">
          {icon}
          {title}
        </span>
        <ChevronDown
          className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      {/* Stays in the DOM so the printed report is complete even when collapsed. */}
      <div
        hidden={!open}
        className="print-block prose-sm pb-4 text-sm leading-relaxed text-muted-foreground [&_a]:text-accent [&_a]:underline-offset-2 [&_li]:mt-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:text-foreground [&_ul]:list-disc [&_ul]:pl-5"
      >
        <h5 className="mb-1 hidden font-semibold text-foreground print:block">{title}</h5>
        {children}
      </div>
    </div>
  );
}

export function ResultCard({
  result,
  badges,
  packet,
}: {
  result: SchemeResult;
  /** Extra labels under the title (state-scheme badge, operator notes). */
  badges?: React.ReactNode;
  /** Application packet — shown behind "Prepare application" when given. */
  packet?: React.ReactNode;
}) {
  const t = useT();
  const [packetOpen, setPacketOpen] = useState(false);
  // Read-aloud covers the decision content of this card: verdict label,
  // summary, and every reason — in the user's language.
  const spokenText = [
    result.scheme_name,
    t(`verdicts.${result.verdict}`),
    result.summary,
    ...result.reasons.map((r) => r.text),
    ...(result.confirm_before_applying ?? []),
  ].join(". ");
  return (
    <Card className="print-avoid-break border-border bg-card shadow-xs">
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="font-serif text-lg leading-snug font-semibold">
            {result.scheme_name}
          </h3>
          <span className="flex items-center gap-1">
            <VerdictBadge verdict={result.verdict} />
            <ReadAloud text={spokenText} />
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5 empty:hidden">
          <SchemeLevelBadge schemeId={result.scheme_id} />
          {badges}
        </div>
        <p className="text-[15px] leading-relaxed text-foreground">{result.summary}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.reasons.length > 0 && (
          <div>
            <h4 className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("card.why")}
            </h4>
            <ul className="space-y-3">
              {result.reasons.map((reason, i) => (
                <li key={i} className="text-sm leading-relaxed">
                  {reason.text}
                  <span className="mt-1.5 flex flex-wrap gap-1.5">
                    {reason.citations.map((citation, j) => (
                      <CitationChip key={j} citation={citation} />
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {result.near_miss && <NearMissNotice nearMiss={result.near_miss} />}

        {result.missing_info.length > 0 && (
          <div className="rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
            <span className="font-medium">{t("card.confirm")}</span>
            {result.missing_info.join(" · ")}
          </div>
        )}

        {(result.confirm_before_applying?.length ?? 0) > 0 && (
          <div className="rounded-lg bg-verdict-info-soft p-3 text-sm leading-relaxed text-verdict-info">
            <p className="font-medium">{t("card.beforeApply")}</p>
            <ul className="mt-1.5 list-disc space-y-1 pl-5">
              {result.confirm_before_applying!.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </div>
        )}

        {result.documents && (
          <Expandable
            title={t("card.documents")}
            icon={<FileText className="size-4 text-accent" aria-hidden="true" />}
          >
            <ReactMarkdown>{result.documents}</ReactMarkdown>
          </Expandable>
        )}
        {result.how_to_apply && (
          <Expandable
            title={t("card.howToApply")}
            icon={<Landmark className="size-4 text-accent" aria-hidden="true" />}
          >
            <ReactMarkdown>{result.how_to_apply}</ReactMarkdown>
          </Expandable>
        )}

        {packet && (
          <div className="print-hidden flex flex-col gap-3 border-t border-border pt-3">
            <button
              type="button"
              onClick={() => setPacketOpen(!packetOpen)}
              aria-expanded={packetOpen}
              className="inline-flex w-fit items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <ClipboardCheck className="size-4" aria-hidden="true" />
              {packetOpen ? t("packet.hide") : t("packet.open")}
            </button>
            {packetOpen && packet}
          </div>
        )}

        <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3">
          <a
            href={result.page_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs font-medium text-accent underline-offset-2 hover:underline"
          >
            {t("card.officialPage")} <ExternalLink className="size-3" aria-hidden="true" />
          </a>
          {result.references.slice(0, 2).map((ref) => (
            <a
              key={ref.url}
              href={ref.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs font-medium text-accent underline-offset-2 hover:underline"
            >
              {ref.title} <ExternalLink className="size-3" aria-hidden="true" />
            </a>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
