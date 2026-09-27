"use client";

// Native radios styled as tappable option cards — keyboard and screen-reader
// behavior comes free from the platform; only the looks are ours.
import * as React from "react";

import { cn } from "@/lib/utils";

export interface RadioOption {
  value: string;
  label: string;
  description?: string;
}

interface RadioGroupProps {
  legend: string;
  name: string;
  options: RadioOption[];
  value: string | null;
  onChange: (value: string) => void;
  help?: React.ReactNode;
  error?: string;
  /** Lay options out in two columns on wider screens (for short labels). */
  columns?: boolean;
  className?: string;
}

export function RadioGroup({
  legend,
  name,
  options,
  value,
  onChange,
  help,
  error,
  columns,
  className,
}: RadioGroupProps) {
  const helpId = help ? `${name}-help` : undefined;
  const errorId = error ? `${name}-error` : undefined;

  return (
    <fieldset
      className={cn("flex flex-col gap-1.5", className)}
      aria-describedby={[helpId, errorId].filter(Boolean).join(" ") || undefined}
    >
      <legend className="text-sm font-medium text-foreground">{legend}</legend>
      {help && (
        <p id={helpId} className="text-sm leading-relaxed text-muted-foreground">
          {help}
        </p>
      )}
      <div className={cn("mt-1 grid gap-2", columns && "sm:grid-cols-2")}>
        {options.map((option) => (
          <label
            key={option.value}
            className={cn(
              "flex cursor-pointer items-start gap-3 rounded-lg border border-border bg-card p-3.5 transition-colors duration-150",
              "hover:border-input",
              "has-checked:border-primary has-checked:bg-accent-soft",
              "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ring",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="peer sr-only"
            />
            <span
              aria-hidden="true"
              className="mt-0.5 flex size-4.5 shrink-0 items-center justify-center rounded-full border-2 border-input bg-card peer-checked:border-primary peer-checked:[&>span]:opacity-100"
            >
              <span className="size-2 rounded-full bg-primary opacity-0 transition-opacity duration-150" />
            </span>
            <span className="flex flex-col gap-0.5">
              <span className="text-base leading-snug font-medium text-foreground">
                {option.label}
              </span>
              {option.description && (
                <span className="text-sm leading-relaxed text-muted-foreground">
                  {option.description}
                </span>
              )}
            </span>
          </label>
        ))}
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </fieldset>
  );
}
