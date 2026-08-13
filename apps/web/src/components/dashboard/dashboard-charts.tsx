"use client";

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
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import type {
  AcquisitionPoint,
  CategoryRevenue,
  OrderStatusDatum,
  ProductPerformance,
  RevenuePoint
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatCompactMoney, formatMoney } from "@/lib/format";

function ChartHeader({
  eyebrow,
  title,
  note
}: {
  eyebrow: string;
  title: string;
  note: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
          {eyebrow}
        </p>
        <h2 className="text-ink-950 mt-1.5 text-lg font-bold tracking-[-0.03em]">
          {title}
        </h2>
      </div>
      <p className="bg-ink-50 text-ink-500 rounded-lg px-2.5 py-1 text-[10px] font-medium">
        {note}
      </p>
    </div>
  );
}

const tooltipStyle = {
  border: "1px solid #dce3ea",
  borderRadius: "12px",
  boxShadow: "0 12px 35px -20px rgba(7,17,31,.35)",
  fontSize: "12px"
};

export function RevenueChart({ data }: { data: RevenuePoint[] }) {
  return (
    <Card id="revenue" className="scroll-mt-28 p-4 sm:p-6">
      <ChartHeader
        eyebrow="Revenue performance"
        title="Revenue across the selected period"
        note="Eligible order revenue"
      />
      <figure className="mt-6" aria-label="Revenue across the selected period">
        <div className="h-[280px] w-full sm:h-[330px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 8, right: 2, left: -16, bottom: 0 }}
            >
              <defs>
                <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0f9f8f" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="#0f9f8f" stopOpacity={0.015} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#edf1f5" vertical={false} />
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#657a91", fontSize: 11 }}
                minTickGap={24}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#657a91", fontSize: 11 }}
                tickFormatter={(value) => formatCompactMoney(Number(value))}
                width={54}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value, name) => [
                  formatMoney(Number(value)),
                  name === "revenue_minor" ? "Revenue" : String(name)
                ]}
              />
              <Area
                type="monotone"
                dataKey="revenue_minor"
                stroke="#0b8f82"
                strokeWidth={2.5}
                fill="url(#revenueFill)"
                activeDot={{
                  r: 5,
                  fill: "#0b8f82",
                  stroke: "#fff",
                  strokeWidth: 2
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <figcaption className="text-ink-500 mt-3 flex flex-wrap items-center gap-4 text-[11px]">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-0.5 w-5 bg-teal-600" /> Revenue
          </span>
          <span className="sm:ml-auto">
            Use keyboard focus or touch to inspect chart points.
          </span>
        </figcaption>
        <table className="sr-only">
          <caption>Revenue values by period</caption>
          <thead>
            <tr>
              <th>Period</th>
              <th>Current revenue</th>
            </tr>
          </thead>
          <tbody>
            {data.map((point) => (
              <tr key={point.date}>
                <th>{point.label}</th>
                <td>{formatMoney(point.revenue_minor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </figure>
    </Card>
  );
}

export function CategoryRevenueChart({ data }: { data: CategoryRevenue[] }) {
  return (
    <Card className="p-4 sm:p-6">
      <ChartHeader
        eyebrow="Revenue mix"
        title="Category contribution"
        note="Selected period"
      />
      <figure className="mt-4" aria-label="Revenue share by category">
        <div className="relative mx-auto h-[210px] max-w-xs">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value) => formatMoney(Number(value))}
              />
              <Pie
                data={data}
                dataKey="revenue_minor"
                nameKey="name"
                innerRadius={58}
                outerRadius={84}
                paddingAngle={2}
                strokeWidth={0}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
            <div>
              <p className="text-ink-500 text-[10px] font-medium">
                Top category
              </p>
              <p className="text-ink-950 mt-1 text-sm font-bold">Software</p>
            </div>
          </div>
        </div>
        <figcaption className="mt-2 grid gap-2">
          {data.map((item) => (
            <div key={item.name} className="flex items-center gap-2 text-xs">
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-ink-600 flex-1">{item.name}</span>
              <span className="text-ink-900 font-semibold">
                {formatMoney(item.revenue_minor)}
              </span>
              <span className="text-ink-400 w-9 text-right">
                {Math.round(item.share_ratio * 100)}%
              </span>
            </div>
          ))}
        </figcaption>
      </figure>
    </Card>
  );
}

export function AcquisitionChart({ data }: { data: AcquisitionPoint[] }) {
  return (
    <Card id="acquisition" className="scroll-mt-28 p-4 sm:p-6">
      <ChartHeader
        eyebrow="Customer momentum"
        title="New customer acquisition"
        note="Revenue-generating"
      />
      <figure className="mt-5" aria-label="New customers by period">
        <div className="h-[230px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
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
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value) => [Number(value), "New customers"]}
              />
              <Bar
                dataKey="customers"
                fill="#334766"
                radius={[6, 6, 0, 0]}
                maxBarSize={36}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <figcaption className="sr-only">
          New customer acquisition is trending upward over the selected period.
        </figcaption>
      </figure>
    </Card>
  );
}

export function TopProducts({ data }: { data: ProductPerformance[] }) {
  return (
    <Card id="products" className="scroll-mt-28 p-4 sm:p-6">
      <ChartHeader
        eyebrow="Product performance"
        title="Top products by revenue"
        note="Top five"
      />
      <ol className="mt-6 space-y-5">
        {data.map((product, index) => (
          <li key={product.name}>
            <div className="flex items-start gap-3">
              <span className="bg-ink-100 text-ink-600 mt-0.5 grid size-6 shrink-0 place-items-center rounded-lg font-mono text-[10px] font-bold">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-ink-900 truncate text-sm font-semibold">
                      {product.name}
                    </p>
                    <p className="text-ink-400 mt-0.5 text-[10px]">
                      {product.category ? `${product.category} · ` : ""}
                      {product.units_sold} units
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-ink-950 text-sm font-bold">
                      {formatMoney(product.revenue_minor)}
                    </p>
                    <p
                      className={cn(
                        "mt-0.5 inline-flex items-center text-[10px] font-semibold",
                        product.change_ratio !== null &&
                          product.change_ratio < 0
                          ? "text-coral-700"
                          : "text-teal-700"
                      )}
                    >
                      {product.change_ratio !== null &&
                      product.change_ratio < 0 ? (
                        <ArrowDownRight className="size-3" aria-hidden="true" />
                      ) : (
                        <ArrowUpRight className="size-3" aria-hidden="true" />
                      )}
                      {product.change_ratio === null
                        ? "No comparison"
                        : `${Math.abs(product.change_ratio * 100).toFixed(1)}%`}
                    </p>
                  </div>
                </div>
                <div className="bg-ink-100 mt-2 h-1.5 overflow-hidden rounded-full">
                  <div
                    className="h-full rounded-full bg-teal-500"
                    style={{ width: `${product.relative_ratio * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function OrderStatusChart({
  data,
  total
}: {
  data: OrderStatusDatum[];
  total: number;
}) {
  return (
    <Card id="orders" className="scroll-mt-28 p-4 sm:p-6">
      <ChartHeader
        eyebrow="Operations"
        title="Orders by status"
        note={`${total} total orders`}
      />
      <div
        className="bg-ink-100 mt-7 flex h-3 overflow-hidden rounded-full"
        aria-label="Order status distribution"
      >
        {data.map((item) => (
          <span
            key={item.status}
            style={{
              width: `${item.share_ratio * 100}%`,
              backgroundColor: item.color
            }}
            title={`${item.status}: ${item.count}`}
          />
        ))}
      </div>
      <ul className="mt-6 grid grid-cols-2 gap-x-5 gap-y-4">
        {data.map((item) => (
          <li key={item.status} className="flex items-center gap-2">
            <span
              className="size-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <p className="text-ink-500 truncate text-xs capitalize">
                {item.status}
              </p>
              <p className="text-ink-950 mt-0.5 text-sm font-bold">
                {item.count}
              </p>
            </div>
            <span className="text-ink-400 text-[10px]">
              {(item.share_ratio * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-6 rounded-xl bg-teal-50 p-3 text-xs leading-5 text-teal-800">
        <strong>Healthy order flow.</strong> Completed, processing, and paid
        orders dominate the current mix.
      </div>
    </Card>
  );
}
