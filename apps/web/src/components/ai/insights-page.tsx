"use client";

import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Lightbulb,
  RefreshCw,
  Sparkles,
  TrendingUp
} from "lucide-react";
import { useState } from "react";
import { DataToolbar } from "@/components/data/data-toolbar";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type AiInsight,
  type InsightCategory,
  type InsightListQuery,
  type InsightSeverity,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange } from "@/lib/url-state";

const categories: Array<{ value: InsightCategory; label: string }> = [
  { value: "growth", label: "Growth" },
  { value: "warning", label: "Warning" },
  { value: "opportunity", label: "Opportunity" },
  { value: "performance", label: "Performance" },
  { value: "anomaly", label: "Anomaly" }
];
const severities: Array<{ value: InsightSeverity; label: string }> = [
  { value: "high", label: "High priority" },
  { value: "medium", label: "Medium priority" },
  { value: "low", label: "Low priority" },
  { value: "info", label: "Information" }
];
const categoryVisuals = {
  growth: {
    icon: TrendingUp,
    tone: "bg-teal-50 text-teal-700",
    label: "Growth"
  },
  warning: {
    icon: AlertTriangle,
    tone: "bg-coral-50 text-coral-700",
    label: "Warning"
  },
  opportunity: {
    icon: Lightbulb,
    tone: "bg-amber-50 text-amber-700",
    label: "Opportunity"
  },
  performance: {
    icon: ArrowUpRight,
    tone: "bg-ink-100 text-ink-700",
    label: "Performance"
  },
  anomaly: {
    icon: Activity,
    tone: "bg-indigo-50 text-indigo-700",
    label: "Anomaly"
  }
};

function metricLabel(key: string): string {
  return key
    .replace(/_minor$/, "")
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function metricValue(
  value: number,
  unit: AiInsight["supporting_metrics"][number]["unit"]
): string {
  if (unit === "ratio") {
    return new Intl.NumberFormat("en-US", {
      style: "percent",
      maximumFractionDigits: 1
    }).format(value);
  }
  return `${value.toLocaleString("en-US")}${unit === "minor_currency" ? " minor units" : ""}`;
}

export function InsightCard({ insight }: { insight: AiInsight }) {
  const visual = categoryVisuals[insight.category];
  const Icon = visual.icon;
  return (
    <Card className="overflow-hidden">
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "grid size-9 place-items-center rounded-xl",
                visual.tone
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-ink-400 text-[10px] font-bold tracking-[0.12em] uppercase">
                {visual.label}
              </p>
              <p className="text-ink-500 mt-0.5 text-[10px]">
                {insight.period_label ??
                  `${insight.period_start} to ${insight.period_end}`}
              </p>
            </div>
          </div>
          <Badge
            className={cn(
              insight.severity === "high"
                ? "border-coral-500/20 bg-coral-50 text-coral-700"
                : insight.severity === "medium"
                  ? "border-amber-500/20 bg-amber-50 text-amber-700"
                  : "border-ink-200 bg-ink-50 text-ink-600"
            )}
          >
            {insight.severity.charAt(0).toUpperCase() +
              insight.severity.slice(1)}{" "}
            priority
          </Badge>
        </div>
        <h2 className="text-ink-950 mt-5 text-xl font-bold tracking-[-0.035em]">
          {insight.title}
        </h2>
        <p className="text-ink-600 mt-2 text-sm leading-6">
          {insight.description}
        </p>
      </div>
      <div className="border-ink-100 bg-ink-50/70 border-t px-5 py-4 sm:px-6">
        <p className="text-ink-400 text-[10px] font-bold tracking-[0.12em] uppercase">
          Supporting metrics
        </p>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          {insight.supporting_metrics.map((metric) => (
            <div
              key={metric.key ?? metric.id}
              className="border-ink-100 rounded-xl border bg-white p-3"
            >
              <dt className="text-ink-500 text-xs">
                {metric.label ?? metricLabel(metric.key ?? "metric")}
              </dt>
              <dd className="text-ink-950 mt-1 text-lg font-bold">
                {metric.formatted_value ??
                  metricValue(metric.value ?? 0, metric.unit)}
              </dd>
              {metric.comparison_value === null && !metric.comparison ? null : (
                <dd className="mt-1 text-[10px] font-semibold text-teal-700">
                  {metric.comparison ??
                    `Previous: ${metricValue(metric.comparison_value ?? 0, metric.unit)}`}
                </dd>
              )}
              <dd className="text-ink-400 mt-2 text-[9px]">
                {metric.source ?? "Tenant analytics"}
              </dd>
            </div>
          ))}
        </dl>
        <p className="text-ink-400 mt-3 text-[10px]">
          Generated {formatDateTime(insight.generated_at)} · {insight.provider}{" "}
          · {insight.generation_mode ?? "deterministic"} mode
        </p>
      </div>
    </Card>
  );
}

export function InsightsPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const range = parseAnalyticsRange(searchParams.get("range"));
  const categoryValue = searchParams.get("category");
  const severityValue = searchParams.get("severity");
  const query: InsightListQuery = {
    search: searchParams.get("q") || undefined,
    category: categories.some((item) => item.value === categoryValue)
      ? (categoryValue as InsightCategory)
      : undefined,
    severity: severities.some((item) => item.value === severityValue)
      ? (severityValue as InsightSeverity)
      : undefined,
    range
  };
  const queryKey = [
    "organization",
    organization.id,
    "insights",
    query
  ] as const;
  const insightsQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      insightForgeApi.insights.list(organization.id, query, signal)
  });
  const generation = useMutation({
    mutationFn: () =>
      insightForgeApi.insights.regenerate(organization.id, range),
    onSuccess: async (result) => {
      setFeedback(result.feedback);
      await queryClient.invalidateQueries({
        queryKey: ["organization", organization.id, "insights"]
      });
    },
    onError: () =>
      setFeedback("Insight regeneration could not be completed. Try again.")
  });

  return (
    <div>
      <PageHeader
        eyebrow="Grounded business intelligence"
        title="AI Insights"
        description={`Prioritized explanations for ${organization.name}, generated only from validated aggregate metrics and deterministic business rules.`}
        badge="No raw rows sent to AI"
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <RangeFilter value={range} />
            <Button
              onClick={() => generation.mutate()}
              disabled={generation.isPending}
            >
              <RefreshCw
                className={cn("size-4", generation.isPending && "animate-spin")}
                aria-hidden="true"
              />
              {generation.isPending ? "Regenerating" : "Regenerate insights"}
            </Button>
          </div>
        }
      />
      {feedback ? (
        <div
          className="mb-4 flex items-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-medium text-teal-800"
          role="status"
        >
          <Sparkles className="size-4 shrink-0" aria-hidden="true" /> {feedback}
        </div>
      ) : null}
      <div className="mb-4">
        <DataToolbar
          searchLabel="Search insights"
          searchPlaceholder="Search insight titles and explanations"
          filters={[
            {
              param: "category",
              label: "Insight category",
              allLabel: "All categories",
              options: categories
            },
            {
              param: "severity",
              label: "Insight priority",
              allLabel: "All priorities",
              options: severities
            }
          ]}
          sortOptions={[
            { value: "generated_at_desc", label: "Newest evidence" }
          ]}
        />
      </div>
      {insightsQuery.isPending ? <ListSkeleton rows={4} /> : null}
      {insightsQuery.isError ? (
        <ErrorState
          message={
            insightsQuery.error instanceof ApiProblemError
              ? insightsQuery.error.problem.detail
              : "Insights could not be loaded."
          }
          requestId={
            insightsQuery.error instanceof ApiProblemError
              ? insightsQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void insightsQuery.refetch()}
        />
      ) : null}
      {insightsQuery.data && insightsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No insights match these filters"
          message="Clear a filter or choose another reporting period."
        />
      ) : null}
      {insightsQuery.data?.items.length ? (
        <section
          className="grid gap-5 xl:grid-cols-2"
          aria-label="Generated insights"
        >
          {insightsQuery.data.items.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </section>
      ) : null}
    </div>
  );
}
