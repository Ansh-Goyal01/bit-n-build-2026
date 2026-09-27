"use client";

import { useState } from "react";
import { ChevronDown, ExternalLink, Quote } from "lucide-react";

import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { VerifiedCitation } from "@/lib/types";

const KNOWN_SECTIONS = new Set([
  "eligibility",
  "exclusions",
  "benefits",
  "details",
  "application",
  "documents",
  "faq",
]);

/** A tappable reference chip that reveals the verbatim official text it cites. */
export function CitationChip({ citation }: { citation: VerifiedCitation }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const label = KNOWN_SECTIONS.has(citation.section)
    ? t(`citation.sections.${citation.section}`)
    : t("citation.officialText");

  return (
    <div className="inline-block max-w-full align-top">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft",
          "px-2.5 py-0.5 text-xs font-medium text-accent transition-colors",
          "hover:bg-accent/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        )}
      >
        <Quote className="size-3" aria-hidden="true" />
        {label}
        <ChevronDown
          className={cn("size-3 transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      {/* Kept in the DOM so printed reports carry their evidence. */}
      <blockquote
        hidden={!open}
        className="print-block mt-2 rounded-lg border border-accent/20 bg-accent-soft/60 p-3 text-sm leading-relaxed text-foreground"
      >
        “{citation.quote}”
        <a
          href={citation.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 flex w-fit items-center gap-1 text-xs font-medium text-accent underline-offset-2 hover:underline"
        >
          {t("citation.viewSource")}
          <ExternalLink className="size-3" aria-hidden="true" />
        </a>
      </blockquote>
    </div>
  );
}
