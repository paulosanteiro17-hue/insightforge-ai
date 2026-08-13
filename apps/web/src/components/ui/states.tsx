import { AlertTriangle, Database, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

export function LoadingBlock({ className }: { className?: string }) {
  return (
    <div
      className={cn("bg-ink-100 animate-pulse rounded-xl", className)}
      aria-hidden="true"
    />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading dashboard">
      <span className="sr-only">Loading dashboard data.</span>
      <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <LoadingBlock key={index} className="h-36" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(300px,1fr)]">
        <LoadingBlock className="h-[420px]" />
        <LoadingBlock className="h-[420px]" />
      </div>
      <LoadingBlock className="h-72" />
    </div>
  );
}

export function ErrorState({
  title = "We could not load this view",
  message,
  requestId,
  onRetry
}: {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
}) {
  return (
    <Card
      className="flex min-h-72 flex-col items-center justify-center p-8 text-center"
      role="alert"
    >
      <span className="bg-coral-50 text-coral-700 mb-4 grid size-12 place-items-center rounded-2xl">
        <AlertTriangle className="size-5" aria-hidden="true" />
      </span>
      <h2 className="text-ink-950 text-xl font-semibold tracking-[-0.02em]">
        {title}
      </h2>
      <p className="text-ink-600 mt-2 max-w-md text-sm leading-6">{message}</p>
      {requestId ? (
        <p className="text-ink-500 mt-2 font-mono text-xs">
          Request ID: {requestId}
        </p>
      ) : null}
      {onRetry ? (
        <Button className="mt-5" variant="outline" onClick={onRetry}>
          <RefreshCw className="size-4" aria-hidden="true" />
          Try again
        </Button>
      ) : null}
    </Card>
  );
}

export function EmptyState({
  title = "No data in this range",
  message = "Choose another period or import business data to populate this view."
}: {
  title?: string;
  message?: string;
}) {
  return (
    <Card className="flex min-h-72 flex-col items-center justify-center p-8 text-center">
      <span className="mb-4 grid size-12 place-items-center rounded-2xl bg-teal-50 text-teal-700">
        <Database className="size-5" aria-hidden="true" />
      </span>
      <h2 className="text-ink-950 text-xl font-semibold tracking-[-0.02em]">
        {title}
      </h2>
      <p className="text-ink-600 mt-2 max-w-md text-sm leading-6">{message}</p>
    </Card>
  );
}
