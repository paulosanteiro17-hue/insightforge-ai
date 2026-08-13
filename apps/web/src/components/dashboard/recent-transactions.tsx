import { ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { RecentTransaction } from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { formatMoney, formatShortDate } from "@/lib/format";

const statusClasses: Record<RecentTransaction["status"], string> = {
  completed: "bg-teal-50 text-teal-700",
  processing: "bg-ink-100 text-ink-700",
  paid: "bg-[#eef3ff] text-[#405f9e]",
  pending: "bg-[#fff4e9] text-[#a45f22]",
  cancelled: "bg-ink-100 text-ink-600",
  refunded: "bg-coral-50 text-coral-700"
};

export function RecentTransactions({ data }: { data: RecentTransaction[] }) {
  return (
    <Card id="transactions" className="scroll-mt-28 overflow-hidden">
      <div className="border-ink-100 flex items-center justify-between gap-4 border-b px-4 py-5 sm:px-6">
        <div>
          <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
            Latest activity
          </p>
          <h2 className="text-ink-950 mt-1.5 text-lg font-bold tracking-[-0.03em]">
            Recent transactions
          </h2>
        </div>
        <span className="text-ink-500 hidden items-center gap-1 text-xs font-semibold sm:inline-flex">
          Updated moments ago{" "}
          <ArrowUpRight className="size-3.5" aria-hidden="true" />
        </span>
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[760px] text-left">
          <thead>
            <tr className="border-ink-100 bg-ink-50/70 text-ink-400 border-b text-[10px] font-bold tracking-[0.12em] uppercase">
              <th className="px-6 py-3">Customer</th>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-6 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {data.map((transaction) => (
              <tr
                key={transaction.id}
                className="hover:bg-ink-50/70 transition-colors"
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <span className="bg-ink-100 text-ink-600 grid size-9 place-items-center rounded-xl text-[10px] font-bold">
                      {transaction.customer_initials}
                    </span>
                    <div>
                      <p className="text-ink-900 text-sm font-semibold">
                        {transaction.customer_name}
                      </p>
                      <p className="text-ink-400 mt-0.5 text-[10px]">
                        {transaction.order_number}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="text-ink-600 px-4 py-4 font-mono text-xs">
                  {transaction.order_number}
                </td>
                <td className="px-4 py-4">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[10px] font-semibold",
                      statusClasses[transaction.status]
                    )}
                  >
                    <span className="capitalize">{transaction.status}</span>
                  </span>
                </td>
                <td className="text-ink-500 px-4 py-4 text-xs">
                  {formatShortDate(transaction.ordered_at)}
                </td>
                <td className="text-ink-950 px-6 py-4 text-right text-sm font-bold">
                  {formatMoney(transaction.total_minor)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {data.map((transaction) => (
          <article key={transaction.id} className="p-4">
            <div className="flex items-start gap-3">
              <span className="bg-ink-100 text-ink-600 grid size-9 shrink-0 place-items-center rounded-xl text-[10px] font-bold">
                {transaction.customer_initials}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-ink-900 truncate text-sm font-semibold">
                    {transaction.customer_name}
                  </p>
                  <p className="text-ink-950 shrink-0 text-sm font-bold">
                    {formatMoney(transaction.total_minor)}
                  </p>
                </div>
                <p className="text-ink-500 mt-1 truncate text-xs">
                  {transaction.order_number}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[10px] font-semibold",
                      statusClasses[transaction.status]
                    )}
                  >
                    <span className="capitalize">{transaction.status}</span>
                  </span>
                  <span className="text-ink-400 text-[10px]">
                    {transaction.order_number} ·{" "}
                    {formatShortDate(transaction.ordered_at)}
                  </span>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
