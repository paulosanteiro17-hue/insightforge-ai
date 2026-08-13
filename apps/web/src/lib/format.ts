import type { MetricValue } from "@/lib/api/contracts";

const compactNumber = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1
});

export function formatMoney(amountMinor: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(amountMinor / 100);
}

export function formatCompactMoney(
  amountMinor: number,
  currency = "USD"
): string {
  const symbol = currency === "USD" ? "$" : `${currency} `;
  return `${symbol}${compactNumber.format(amountMinor / 100)}`;
}

export function formatMetricValue(value: MetricValue): string {
  switch (value.kind) {
    case "money":
      return formatMoney(value.amount_minor, value.currency);
    case "integer":
      return new Intl.NumberFormat("en-US").format(value.value);
    case "percentage":
      return new Intl.NumberFormat("en-US", {
        style: "percent",
        maximumFractionDigits: 1
      }).format(value.ratio);
  }
}

export function formatShortDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric"
  }).format(new Date(value));
}

export function formatLongDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(value));
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}
