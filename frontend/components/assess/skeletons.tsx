import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/** Shown while the pipeline reads official text and reasons about eligibility. */
export function ResultsSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      {[0, 1].map((i) => (
        <Card key={i} className="border-border bg-card shadow-xs">
          <CardHeader className="gap-3">
            <div className="flex items-start justify-between gap-2">
              <Skeleton className="h-5 w-3/5" />
              <Skeleton className="h-6 w-32 rounded-full" />
            </div>
            <Skeleton className="h-4 w-4/5" />
          </CardHeader>
          <CardContent className="space-y-2.5">
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3.5 w-11/12" />
            <div className="flex gap-1.5 pt-1">
              <Skeleton className="h-5 w-28 rounded-full" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
