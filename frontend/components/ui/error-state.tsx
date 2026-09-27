import * as React from "react";
import { AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

/** True system errors only — never used for eligibility outcomes. */
export function ErrorState({ title, body, action, className }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-destructive-border bg-destructive-soft px-6 py-12 text-center",
        className,
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-card text-destructive">
        <AlertCircle className="size-5" aria-hidden="true" />
      </span>
      <p className="font-semibold text-foreground">{title}</p>
      {body && <p className="max-w-md text-sm leading-relaxed text-foreground/80">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
