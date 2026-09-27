import { cn } from "@/lib/utils";

/** Shared page gutter: ~1150px readable width, 8pt-aligned padding. */
export function Container({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8", className)}
      {...props}
    />
  );
}
