"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { AnalyticsRange } from "@/lib/api/contracts";
import { cn } from "@/lib/cn";

const options: Array<{
  value: AnalyticsRange;
  label: string;
  accessibleLabel: string;
}> = [
  { value: "7d", label: "7d", accessibleLabel: "Last 7 days" },
  { value: "30d", label: "30d", accessibleLabel: "Last 30 days" },
  { value: "90d", label: "90d", accessibleLabel: "Last 90 days" },
  { value: "year_to_date", label: "YTD", accessibleLabel: "Year to date" }
];

export function RangeFilter({ value }: { value: AnalyticsRange }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function selectRange(range: AnalyticsRange) {
    const next = new URLSearchParams(searchParams.toString());
    next.set("range", range);
    next.set("compare", "previous_period");
    next.delete("from");
    next.delete("to");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  return (
    <div
      className="border-ink-200 inline-flex rounded-xl border bg-white p-1 shadow-sm"
      role="group"
      aria-label="Dashboard date range"
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-label={option.accessibleLabel}
          aria-pressed={value === option.value}
          onClick={() => selectRange(option.value)}
          className={cn(
            "min-h-9 min-w-11 rounded-lg px-2.5 text-xs font-semibold transition-colors sm:px-3",
            value === option.value
              ? "bg-ink-950 text-white"
              : "text-ink-500 hover:bg-ink-50 hover:text-ink-950"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
