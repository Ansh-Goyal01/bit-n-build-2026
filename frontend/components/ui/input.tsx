import * as React from "react";

import { cn } from "@/lib/utils";

function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        // text-base (16px) prevents iOS auto-zoom; h-11 keeps a 44px touch target
        "h-11 w-full rounded-lg border border-input bg-card px-3.5 text-base text-foreground placeholder:text-muted-foreground transition-colors duration-150",
        "aria-invalid:border-destructive",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
