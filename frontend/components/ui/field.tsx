// Labeled form field: label + control + helper text + inline error.
// Wires htmlFor/aria-describedby/aria-invalid so pages can't forget them.
import * as React from "react";

import { cn } from "@/lib/utils";

interface FieldProps {
  id: string;
  label: string;
  help?: React.ReactNode;
  error?: string;
  optional?: boolean;
  className?: string;
  children: React.ReactElement<Record<string, unknown>>;
}

export function Field({ id, label, help, error, optional, className, children }: FieldProps) {
  const helpId = help ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  const control = React.cloneElement(children, {
    id,
    "aria-describedby": describedBy,
    "aria-invalid": error ? true : undefined,
  });

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
        {optional && (
          <span className="ml-1.5 font-normal text-muted-foreground">(optional)</span>
        )}
      </label>
      {help && (
        <p id={helpId} className="text-sm leading-relaxed text-muted-foreground">
          {help}
        </p>
      )}
      {control}
      {error && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
