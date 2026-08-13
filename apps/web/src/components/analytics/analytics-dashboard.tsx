"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  UsersRound
} from "lucide-react";
import { useEffect } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { PageHeader } from "@/components/data/page-header";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { Card } from "@/components/ui/card";
import {
  DashboardSkeleton,
  EmptyState,
  ErrorState
} from "@/components/ui/states";
import {
  ApiProblemError,
  type AnalyticsMetric,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import {
  formatCompactMoney,
  formatMetricValue,
  formatMoney
} from "@/lib/format";
import { insightForgeApi } from "@runtime-api";
import { isAnalyticsRange, parseAnalyticsRange } from "@/lib/url-state";

const tooltipStyle = {
  border: "1px solid #dce3ea",
  borderRadius: "12px",
  boxShadow: "0 12px 35px -20px rgba(7,17,31,.35)",
  fontSize: "12px"
};

function MetricCard({ metric }: { metric: AnalyticsMetric }) {
  const positive = metric.change_ratio >= 0;
  return (
    <Card className="p-4 sm:p-5">
      <p className="text-ink-500 text-xs font-medium">{metric.label}</p>
      <p className="text-ink-950 mt-2 text-2xl font-bold tracking-[-0.045em]">
        {formatMetricValue(metric.value)}
      </p>
      <p
        className={cn(
          "mt-3 inline-flex items-center text-xs font-semibold",
          positive ? "text-teal-700" : "text-coral-700"
        )}
      >
        {positive ? (
          <ArrowUpRight className="size-3.5" aria-hidden="true" />
        ) : (
          <ArrowDownRight className="size-3.5" aria-hidden="true" />
        )}
        {Math.abs(metric.change_ratio * 100).toFixed(1)}% vs previous period
      </p>
      <p className="text-ink-400 mt-2 text-[10px] leading-4">
        {metric.context}
      </p>
    </Card>
  );
}

export function AnalyticsDashboard({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const rawRange = searchParams.get("range");
  const range = parseAnalyticsRange(rawRange);

  useEffect(() => {
    if (rawRange && !isAnalyticsRange(rawRange)) {
      const canonical = new URLSearchParams(searchParams.toString());
      canonical.set("range", "30d");
      canonical.set("compare", "previous_period");
      router.replace(`${pathname}?${canonical.toString()}`, { scroll: false });
    }
  }, [pathname, rawRange, router, searchParams]);

  const analyticsQuery = useQuery({
    queryKey: [
      "organization",
      organization.id,
      "analytics",
      "performance",
      { range }
    ],
    queryFn: ({ signal }) =>
      insightForgeApi.analytics.getPerformance(organization.id, range, signal)
  });

  return (
    <div>
      <PageHeader
        eyebrow="Performance intelligence"
        title="Analytics"
        description={`Explore the revenue, customer, order, and product signals shaping ${organization.name}. Every metric uses the same validated reporting window.`}
        badge="Calculated metrics"
        actions={<RangeFilter value={range} />}
      />

      {analyticsQuery.isPending ? <DashboardSkeleton /> : null}
      {analyticsQuery.isError ? (
        <ErrorState
          message={
            analyticsQuery.error instanceof ApiProblemError
              ? analyticsQuery.error.problem.detail
              : "Analytics could not be loaded."
          }
          requestId={
            analyticsQuery.error instanceof ApiProblemError
              ? analyticsQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void analyticsQuery.refetch()}
        />
      ) : null}
      {analyticsQuery.data?.data_availability === "empty" ? (
        <EmptyState />
      ) : null}
      {analyticsQuery.data?.data_availability === "available" ? (
        <div className="space-y-6">
          <section
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
            aria-label="Performance metrics"
          >
            {analyticsQuery.data.metrics.map((metric) => (
              <MetricCard key={metric.id} metric={metric} />
            ))}
          </section>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.8fr)]">
            <Card className="p-4 sm:p-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
                    Sales velocity
                  </p>
                  <h2 className="text-ink-950 mt-1.5 text-lg font-bold">
                    Revenue and order volume
                  </h2>
                </div>
                <BarChart3
                  className="size-5 text-teal-600"
                  aria-hidden="true"
                />
              </div>
              <figure className="mt-6" aria-label="Revenue and order trend">
                <div className="h-[330px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={analyticsQuery.data.sales_trend}
                      margin={{ top: 8, right: 6, left: -14, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient
                          id="analyticsRevenueFill"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#0f9f8f"
                            stopOpacity={0.3}
                          />
                          <stop
                            offset="100%"
                            stopColor="#0f9f8f"
                            stopOpacity={0.02}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#edf1f5" vertical={false} />
                      <XAxis
                        dataKey="label"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#657a91", fontSize: 11 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#657a91", fontSize: 11 }}
                        tickFormatter={(value) =>
                          formatCompactMoney(Number(value))
                        }
                        width={58}
                      />
                      <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(value, name) => [
                          name === "revenue_minor"
                            ? formatMoney(Number(value))
                            : Number(value),
                          name === "revenue_minor" ? "Revenue" : "Orders"
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="revenue_minor"
                        stroke="#0b8f82"
                        strokeWidth={2.5}
                        fill="url(#analyticsRevenueFill)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <figcaption className="text-ink-500 mt-2 text-xs">
                  Net revenue accelerated through the latest reporting interval.
                </figcaption>
                <table className="sr-only">
                  <caption>Revenue and order values</caption>
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Revenue</th>
                      <th>Orders</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsQuery.data.sales_trend.map((point) => (
                      <tr key={point.date}>
                        <th>{point.label}</th>
                        <td>{formatMoney(point.revenue_minor)}</td>
                        <td>{point.order_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </figure>
            </Card>

            <Card className="p-4 sm:p-6">
              <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
                Portfolio mix
              </p>
              <h2 className="text-ink-950 mt-1.5 text-lg font-bold">
                Revenue by category
              </h2>
              <figure
                className="mt-3"
                aria-label="Revenue share by product category"
              >
                <div className="mx-auto h-[230px] max-w-sm">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(value) => formatMoney(Number(value))}
                      />
                      <Pie
                        data={analyticsQuery.data.product_mix}
                        dataKey="revenue_minor"
                        nameKey="name"
                        innerRadius={62}
                        outerRadius={91}
                        paddingAngle={2}
                        strokeWidth={0}
                      >
                        {analyticsQuery.data.product_mix.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <figcaption className="space-y-2">
                  {analyticsQuery.data.product_mix.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-center gap-2 text-xs"
                    >
                      <span
                        className="size-2 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-ink-600 flex-1">{item.name}</span>
                      <strong className="text-ink-900">
                        {Math.round(item.share_ratio * 100)}%
                      </strong>
                    </div>
                  ))}
                </figcaption>
              </figure>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-4 sm:p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
                    Customer quality
                  </p>
                  <h2 className="text-ink-950 mt-1.5 text-lg font-bold">
                    New customers
                  </h2>
                </div>
                <UsersRound
                  className="text-ink-500 size-5"
                  aria-hidden="true"
                />
              </div>
              <figure className="mt-6" aria-label="New customer trend">
                <div className="h-[270px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={analyticsQuery.data.customer_trend}
                      margin={{ top: 4, right: 0, left: -30, bottom: 0 }}
                    >
                      <CartesianGrid stroke="#edf1f5" vertical={false} />
                      <XAxis
                        dataKey="label"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#657a91", fontSize: 10 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#657a91", fontSize: 10 }}
                        allowDecimals={false}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar
                        dataKey="new_customers"
                        name="New customers"
                        fill="#0f9f8f"
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <figcaption className="sr-only">
                  New customer acquisition counts for each period.
                </figcaption>
              </figure>
            </Card>
            <Card className="p-4 sm:p-6">
              <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
                Order health
              </p>
              <h2 className="text-ink-950 mt-1.5 text-lg font-bold">
                Operational status mix
              </h2>
              <div
                className="bg-ink-100 mt-7 flex h-3 overflow-hidden rounded-full"
                aria-label="Order status distribution"
              >
                {analyticsQuery.data.order_statuses.map((status) => (
                  <span
                    key={status.status}
                    style={{
                      width: `${status.share_ratio * 100}%`,
                      backgroundColor: status.color
                    }}
                    title={`${status.status}: ${status.count}`}
                  />
                ))}
              </div>
              <dl className="mt-7 grid grid-cols-2 gap-4 sm:grid-cols-3">
                {analyticsQuery.data.order_statuses.map((status) => (
                  <div key={status.status} className="bg-ink-50 rounded-xl p-3">
                    <dt className="text-ink-500 text-xs">{status.status}</dt>
                    <dd className="text-ink-950 mt-1 text-xl font-bold">
                      {status.count}
                    </dd>
                    <dd className="text-ink-400 text-[10px]">
                      {(status.share_ratio * 100).toFixed(1)}% of orders
                    </dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
}
