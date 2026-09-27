import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const chipVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap [&_svg]:size-3.5 [&_svg]:shrink-0",
  {
    variants: {
      tone: {
        neutral: "border-border bg-muted text-muted-foreground",
        accent: "border-accent-soft bg-accent-soft text-accent-soft-foreground",
        yes: "border-verdict-yes-border bg-verdict-yes-soft text-verdict-yes",
        info: "border-verdict-info-border bg-verdict-info-soft text-verdict-info",
        no: "border-verdict-no-border bg-verdict-no-soft text-verdict-no",
        error: "border-destructive-border bg-destructive-soft text-destructive",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

function Chip({
  className,
  tone,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof chipVariants>) {
  return <span className={cn(chipVariants({ tone, className }))} {...props} />;
}

export { Chip, chipVariants };
