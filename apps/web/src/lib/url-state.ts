import type { AnalyticsRange } from "@/lib/api/contracts";

const analyticsRanges = new Set<AnalyticsRange>([
  "7d",
  "30d",
  "90d",
  "year_to_date"
]);

export function parseAnalyticsRange(value: string | null): AnalyticsRange {
  return value && analyticsRanges.has(value as AnalyticsRange)
    ? (value as AnalyticsRange)
    : "30d";
}

export function isAnalyticsRange(
  value: string | null
): value is AnalyticsRange {
  return Boolean(value && analyticsRanges.has(value as AnalyticsRange));
}

export function parsePage(value: string | null): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}

export function parseOption<T extends string>(
  value: string | null,
  options: readonly T[],
  fallback: T
): T {
  return value && options.includes(value as T) ? (value as T) : fallback;
}
