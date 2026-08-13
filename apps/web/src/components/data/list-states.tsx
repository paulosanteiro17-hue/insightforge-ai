import { LoadingBlock } from "@/components/ui/states";

export function ListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div
      className="border-ink-200/80 overflow-hidden rounded-2xl border bg-white shadow-[var(--shadow-panel)]"
      role="status"
      aria-label="Loading results"
    >
      <span className="sr-only">Loading results.</span>
      <div className="border-ink-100 border-b p-4">
        <LoadingBlock className="h-10 w-full" />
      </div>
      <div className="space-y-3 p-4">
        {Array.from({ length: rows }, (_, index) => (
          <LoadingBlock key={index} className="h-16 w-full" />
        ))}
      </div>
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading details">
      <span className="sr-only">Loading details.</span>
      <LoadingBlock className="h-24" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <LoadingBlock key={index} className="h-32" />
        ))}
      </div>
      <LoadingBlock className="h-80" />
    </div>
  );
}
