import type { LucideIcon } from "lucide-react";
import {
  BadgeDollarSign,
  CircleDollarSign,
  Gauge,
  ReceiptText,
  Repeat2,
  ShoppingBag,
  TrendingDown,
  TrendingUp,
  UserRoundPlus,
  UsersRound
} from "lucide-react";
import { Card } from "@/components/ui/card";
import type { KpiMetric } from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatMetricValue } from "@/lib/format";

const metricIcons: Record<KpiMetric["id"], LucideIcon> = {
  total_revenue: CircleDollarSign,
  monthly_revenue: BadgeDollarSign,
  orders: ShoppingBag,
  customers: UsersRound,
  average_order_value: ReceiptText,
  conversion_rate: Gauge,
  customer_growth: UserRoundPlus,
  mrr: Repeat2
};

export function KpiGrid({ metrics }: { metrics: KpiMetric[] }) {
  return (
    <section aria-labelledby="key-metrics-title">
      <h2 id="key-metrics-title" className="sr-only">
        Key business metrics
      </h2>
      <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metricIcons[metric.id];
          const TrendIcon =
            metric.comparison.direction === "down" ? TrendingDown : TrendingUp;
          return (
            <Card key={metric.id} className="group p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-ink-500 truncate text-xs font-semibold">
                    {metric.label}
                  </p>
                  <p className="text-ink-950 mt-2 text-[1.65rem] leading-none font-bold tracking-[-0.055em] sm:text-[1.8rem]">
                    {formatMetricValue(metric.value)}
                  </p>
                </div>
                <span className="bg-ink-50 text-ink-600 grid size-9 shrink-0 place-items-center rounded-xl transition-colors group-hover:bg-teal-50 group-hover:text-teal-700">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
              </div>
              <div className="mt-4 flex items-center gap-1.5">
                <TrendIcon
                  className={cn(
                    "size-3.5",
                    metric.comparison.sentiment === "negative"
                      ? "text-coral-600"
                      : "text-teal-600"
                  )}
                  aria-hidden="true"
                />
                <span
                  className={cn(
                    "text-[11px] font-semibold",
                    metric.comparison.sentiment === "negative"
                      ? "text-coral-700"
                      : "text-teal-700"
                  )}
                >
                  {metric.comparison.label}
                </span>
              </div>
              <p className="text-ink-400 mt-2 truncate text-[10px]">
                {metric.supporting_label}
              </p>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
