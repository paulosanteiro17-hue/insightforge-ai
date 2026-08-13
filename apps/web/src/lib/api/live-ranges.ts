import type { AnalyticsRange } from "@/lib/api/contracts";

export function rangeDates(range: AnalyticsRange): {
  date_from: string;
  date_to: string;
} {
  const end = new Date();
  const start = new Date(end);
  if (range === "year_to_date") {
    start.setUTCMonth(0, 1);
    start.setUTCHours(0, 0, 0, 0);
  } else {
    start.setUTCDate(start.getUTCDate() - Number.parseInt(range, 10));
  }
  return { date_from: start.toISOString(), date_to: end.toISOString() };
}
