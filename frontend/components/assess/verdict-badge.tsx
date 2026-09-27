"use client";

import { CheckCircle2, CircleDashed, HelpCircle, MinusCircle } from "lucide-react";

import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/types";

// The verdict ENUM is canonical and language-invariant; only its display
// label is localized (via the verdicts.* dictionary keys).
const VERDICT_STYLES: Record<Verdict, { className: string; Icon: typeof CheckCircle2 }> = {
  eligible: {
    className: "border-verdict-yes-border bg-verdict-yes-soft text-verdict-yes",
    Icon: CheckCircle2,
  },
  likely_eligible: {
    className: "border-verdict-yes-border bg-verdict-yes-soft text-verdict-yes",
    Icon: CircleDashed,
  },
  need_more_info: {
    className: "border-verdict-info-border bg-verdict-info-soft text-verdict-info",
    Icon: HelpCircle,
  },
  not_eligible: {
    className: "border-verdict-no-border bg-verdict-no-soft text-verdict-no",
    Icon: MinusCircle,
  },
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const t = useT();
  const { className, Icon } = VERDICT_STYLES[verdict];
  const label = t(`verdicts.${verdict}`);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium whitespace-nowrap",
        className,
      )}
    >
      <Icon className="size-4" aria-hidden="true" />
      {label}
    </span>
  );
}
