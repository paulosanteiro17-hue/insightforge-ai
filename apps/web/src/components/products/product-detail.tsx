"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownRight,
  ArrowLeft,
  ArrowUpRight,
  Boxes,
  CircleDollarSign,
  PackageCheck,
  ShoppingCart
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { DetailSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type OrganizationSummary,
  type ProductDetail as ProductDetailContract
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatCompactMoney, formatMoney } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange } from "@/lib/url-state";

const tooltipStyle = {
  border: "1px solid #dce3ea",
  borderRadius: "12px",
  boxShadow: "0 12px 35px -20px rgba(7,17,31,.35)",
  fontSize: "12px"
};

export function ProductDetailContent({
  product
}: {
  product: ProductDetailContract;
}) {
  const changePercent = product.revenue_change_percent;
  const positive = changePercent === null || changePercent >= 0;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Period revenue",
            value: formatMoney(product.current.eligible_revenue_minor),
            detail:
              changePercent === null
                ? "No comparable prior period"
                : `${positive ? "+" : "−"}${Math.abs(changePercent).toFixed(1)}% vs prior period`,
            icon: CircleDollarSign
          },
          {
            label: "Units sold",
            value: product.current.units_sold.toLocaleString("en-US"),
            detail:
              product.units_change_percent === null
                ? "No comparable prior period"
                : `${product.units_change_percent >= 0 ? "+" : "−"}${Math.abs(product.units_change_percent).toFixed(1)}% vs prior period`,
            icon: Boxes
          },
          {
            label: "Average selling price",
            value:
              product.current.average_selling_price_minor === null
                ? "Not available"
                : formatMoney(product.current.average_selling_price_minor),
            detail: `Catalog price ${formatMoney(product.unit_price_minor)}`,
            icon: PackageCheck
          },
          {
            label: "Eligible orders",
            value: product.current.order_count.toLocaleString("en-US"),
            detail: `${product.previous.order_count.toLocaleString("en-US")} in the prior period`,
            icon: ShoppingCart
          }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label} className="p-4">
              <span className="bg-ink-50 text-ink-600 grid size-9 place-items-center rounded-xl">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <p className="text-ink-400 mt-3 text-[10px] font-bold tracking-[0.11em] uppercase">
                {item.label}
              </p>
              <p className="text-ink-950 mt-1 text-xl font-bold">
                {item.value}
              </p>
              <p
                className={cn(
                  "mt-1 text-[10px]",
                  item.label === "Period revenue"
                    ? positive
                      ? "text-teal-700"
                      : "text-coral-700"
                    : "text-ink-500"
                )}
              >
                {item.detail}
              </p>
            </Card>
          );
        })}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.65fr)]">
        <Card className="p-4 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
                Product trend
              </p>
              <h2 className="text-ink-950 mt-1.5 text-lg font-bold">
                Revenue and unit velocity
              </h2>
            </div>
            <span
              className={cn(
                "inline-flex items-center text-xs font-semibold",
                positive ? "text-teal-700" : "text-coral-700"
              )}
            >
              {positive ? (
                <ArrowUpRight className="size-4" aria-hidden="true" />
              ) : (
                <ArrowDownRight className="size-4" aria-hidden="true" />
              )}
              {changePercent === null
                ? "No comparison"
                : `${Math.abs(changePercent).toFixed(1)}%`}
            </span>
          </div>
          <figure className="mt-5" aria-label="Product revenue performance">
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={product.performance}
                  margin={{ top: 5, right: 5, left: -10, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="productRevenueFill"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#0f9f8f"
                        stopOpacity={0.28}
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
                    tick={{ fill: "#657a91", fontSize: 10 }}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#657a91", fontSize: 10 }}
                    tickFormatter={(value) => formatCompactMoney(Number(value))}
                    width={55}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(value, name) => [
                      name === "revenue_minor"
                        ? formatMoney(Number(value))
                        : Number(value),
                      name === "revenue_minor" ? "Revenue" : "Units sold"
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue_minor"
                    stroke="#0b8f82"
                    strokeWidth={2.5}
                    fill="url(#productRevenueFill)"
                  />
                  <Bar dataKey="units_sold" fill="#334766" opacity={0.22} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <figcaption className="text-ink-500 mt-2 text-xs">
              Revenue reflects eligible orders in the selected reporting period.
            </figcaption>
            <table className="sr-only">
              <caption>Product performance by period</caption>
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Revenue</th>
                  <th>Units</th>
                </tr>
              </thead>
              <tbody>
                {product.performance.map((point) => (
                  <tr key={point.date}>
                    <th>{point.label}</th>
                    <td>{formatMoney(point.revenue_minor)}</td>
                    <td>{point.units_sold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </figure>
        </Card>
        <Card className="p-5">
          <h2 className="text-ink-950 text-lg font-bold">Catalog details</h2>
          <p className="text-ink-600 mt-3 text-sm leading-6">
            Current catalog attributes and the prior-period baseline used for
            this performance comparison.
          </p>
          <dl className="mt-6 space-y-4 text-sm">
            <div>
              <dt className="text-ink-400 text-[10px] font-bold uppercase">
                SKU
              </dt>
              <dd className="text-ink-800 mt-1 font-mono">{product.sku}</dd>
            </div>
            <div>
              <dt className="text-ink-400 text-[10px] font-bold uppercase">
                Category
              </dt>
              <dd className="text-ink-800 mt-1">{product.category}</dd>
            </div>
            <div>
              <dt className="text-ink-400 text-[10px] font-bold uppercase">
                Catalog price
              </dt>
              <dd className="text-ink-800 mt-1">
                {formatMoney(product.unit_price_minor)}
              </dd>
            </div>
            <div>
              <dt className="text-ink-400 text-[10px] font-bold uppercase">
                Prior-period revenue
              </dt>
              <dd className="text-ink-800 mt-1">
                {formatMoney(product.previous.eligible_revenue_minor)}
              </dd>
            </div>
            <div>
              <dt className="text-ink-400 text-[10px] font-bold uppercase">
                External reference
              </dt>
              <dd className="text-ink-800 mt-1">
                {product.external_id ?? "Not provided"}
              </dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}

export function ProductDetail({
  organization,
  productId
}: {
  organization: OrganizationSummary;
  productId: string;
}) {
  const searchParams = useSearchParams();
  const range = parseAnalyticsRange(searchParams.get("range"));
  const productQuery = useQuery({
    queryKey: [
      "organization",
      organization.id,
      "products",
      productId,
      { range }
    ],
    queryFn: ({ signal }) =>
      insightForgeApi.products.getById(
        organization.id,
        productId,
        range,
        signal
      )
  });
  return (
    <div>
      <Link
        href={`/app/${organization.slug}/products`}
        className="text-ink-600 hover:text-ink-950 mb-5 inline-flex items-center gap-2 text-sm font-semibold"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Back to products
      </Link>
      {productQuery.isPending ? <DetailSkeleton /> : null}
      {productQuery.isError ? (
        <ErrorState
          title="Product unavailable"
          message={
            productQuery.error instanceof ApiProblemError
              ? productQuery.error.problem.detail
              : "The product could not be loaded."
          }
          requestId={
            productQuery.error instanceof ApiProblemError
              ? productQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void productQuery.refetch()}
        />
      ) : null}
      {productQuery.data ? (
        <>
          <PageHeader
            eyebrow="Product performance"
            title={productQuery.data.name}
            description={`${productQuery.data.sku} · ${productQuery.data.category}`}
            actions={
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge status={productQuery.data.status} />
                <RangeFilter value={range} />
              </div>
            }
          />
          <ProductDetailContent product={productQuery.data} />
        </>
      ) : null}
    </div>
  );
}
