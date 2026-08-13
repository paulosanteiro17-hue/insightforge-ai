"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import {
  AcquisitionChart,
  CategoryRevenueChart,
  OrderStatusChart,
  RevenueChart,
  TopProducts
} from "@/components/dashboard/dashboard-charts";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { RecentTransactions } from "@/components/dashboard/recent-transactions";
import { WeeklySummaryCard } from "@/components/dashboard/weekly-summary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DashboardSkeleton,
  EmptyState,
  ErrorState
} from "@/components/ui/states";
import {
  ApiProblemError,
  type AnalyticsRange,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";

const validRanges = new Set<AnalyticsRange>([
  "7d",
  "30d",
  "90d",
  "year_to_date"
]);

function parseRange(value: string | null): AnalyticsRange {
  return value && validRanges.has(value as AnalyticsRange)
    ? (value as AnalyticsRange)
    : "30d";
}

export function OverviewDashboard({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const rawRange = searchParams.get("range");
  const range = parseRange(rawRange);

  useEffect(() => {
    if (rawRange && !validRanges.has(rawRange as AnalyticsRange)) {
      const canonical = new URLSearchParams(searchParams.toString());
      canonical.set("range", "30d");
      canonical.set("compare", "previous_period");
      router.replace(`${pathname}?${canonical.toString()}`, { scroll: false });
    }
  }, [pathname, rawRange, router, searchParams]);

  const overviewQuery = useQuery({
    queryKey: [
      "organization",
      organization.id,
      "analytics",
      "overview",
      { range }
    ],
    queryFn: ({ signal }) =>
      insightForgeApi.analytics.getOverview(organization.id, range, signal)
  });
  const weeklyGeneration = useMutation({
    mutationFn: () =>
      insightForgeApi.analytics.regenerateWeeklySummary(organization.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["organization", organization.id, "analytics", "overview"]
      });
    }
  });

  return (
    <div>
      <header className="mb-6 flex flex-col gap-5 lg:mb-8 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-teal-500/20 bg-teal-50 text-teal-700">
              {organization.is_demo ? "Live demo data" : "Live workspace data"}
            </Badge>
            <span className="text-ink-400 text-xs">
              {overviewQuery.data
                ? `Generated ${new Intl.DateTimeFormat("en-US", {
                    dateStyle: "medium",
                    timeStyle: "short"
                  }).format(new Date(overviewQuery.data.generated_at))}`
                : "Loading the latest analytics snapshot"}
            </span>
          </div>
          <h1 className="text-ink-950 mt-3 text-3xl font-bold tracking-[-0.055em] sm:text-4xl">
            Welcome back.
          </h1>
          <p className="text-ink-600 mt-2 max-w-2xl text-sm leading-6">
            Here is the operating picture for {organization.name}, with every
            comparison anchored to the previous equivalent period.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <RangeFilter value={range} />
        </div>
      </header>

      {overviewQuery.isPending ? <DashboardSkeleton /> : null}
      {overviewQuery.isError ? (
        <ErrorState
          message={
            overviewQuery.error instanceof ApiProblemError
              ? overviewQuery.error.problem.detail
              : "A network or server error interrupted the dashboard request."
          }
          requestId={
            overviewQuery.error instanceof ApiProblemError
              ? overviewQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void overviewQuery.refetch()}
        />
      ) : null}
      {overviewQuery.data?.data_availability === "empty" ? (
        <EmptyState />
      ) : null}
      {overviewQuery.data?.data_availability === "available" ? (
        <div className="space-y-6">
          <KpiGrid metrics={overviewQuery.data.kpis} />
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.75fr)_minmax(300px,0.8fr)]">
            <RevenueChart data={overviewQuery.data.revenue} />
            <CategoryRevenueChart data={overviewQuery.data.category_revenue} />
          </div>
          <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-[1fr_1.15fr_0.9fr]">
            <AcquisitionChart data={overviewQuery.data.acquisition} />
            <TopProducts data={overviewQuery.data.top_products} />
            <OrderStatusChart
              data={overviewQuery.data.order_statuses}
              total={overviewQuery.data.order_status_total}
            />
          </div>
          {overviewQuery.data.weekly_summary ? (
            <WeeklySummaryCard
              summary={overviewQuery.data.weekly_summary}
              onRegenerate={() => weeklyGeneration.mutate()}
              isRegenerating={weeklyGeneration.isPending}
            />
          ) : (
            <Card className="p-6">
              <p className="text-ink-950 font-bold">Weekly summary</p>
              <p className="text-ink-500 mt-2 text-sm">
                No persisted weekly summary is available for this reporting
                window yet.
              </p>
              <Button
                type="button"
                size="sm"
                className="mt-4"
                disabled={weeklyGeneration.isPending}
                onClick={() => weeklyGeneration.mutate()}
              >
                <RefreshCw
                  className={
                    weeklyGeneration.isPending
                      ? "size-4 animate-spin"
                      : "size-4"
                  }
                  aria-hidden="true"
                />
                {weeklyGeneration.isPending
                  ? "Generating"
                  : "Generate weekly summary"}
              </Button>
            </Card>
          )}
          <RecentTransactions data={overviewQuery.data.recent_transactions} />
          <div className="text-ink-400 flex items-center justify-center gap-2 pb-2 text-[10px]">
            <RefreshCw className="size-3" aria-hidden="true" /> Metric version{" "}
            {overviewQuery.data.metric_version} · Source{" "}
            {overviewQuery.data.source_revision}
          </div>
        </div>
      ) : null}
    </div>
  );
}
