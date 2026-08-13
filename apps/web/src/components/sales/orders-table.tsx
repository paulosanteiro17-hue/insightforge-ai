import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { PaginationControls } from "@/components/data/pagination-controls";
import { StatusBadge } from "@/components/data/status-badge";
import { Card } from "@/components/ui/card";
import type { OrderListItem, PaginationMeta } from "@/lib/api/contracts";
import { formatDateTime, formatMoney } from "@/lib/format";

export function OrdersTable({
  orders,
  pagination,
  organizationSlug
}: {
  orders: OrderListItem[];
  pagination: PaginationMeta;
  organizationSlug: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">
            Orders matching the selected filters
          </caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Order</th>
              <th className="px-5 py-3.5">Customer</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Items</th>
              <th className="px-5 py-3.5">Date</th>
              <th className="px-5 py-3.5 text-right">Total</th>
              <th className="w-14">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {orders.map((order) => (
              <tr
                key={order.id}
                className="hover:bg-ink-50/60 transition-colors"
              >
                <td className="px-5 py-4">
                  <Link
                    href={`/app/${organizationSlug}/sales/orders/${order.id}`}
                    className="text-ink-950 font-semibold hover:text-teal-700"
                  >
                    {order.order_number}
                  </Link>
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <span className="bg-ink-100 text-ink-600 grid size-8 shrink-0 place-items-center rounded-lg text-[10px] font-bold">
                      {order.customer.initials}
                    </span>
                    <div className="min-w-0">
                      <p className="text-ink-800 truncate font-medium">
                        {order.customer.name}
                      </p>
                      <p className="text-ink-400 truncate text-[10px]">
                        {order.customer.email}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={order.status} />
                </td>
                <td className="text-ink-600 px-5 py-4">{order.item_count}</td>
                <td className="text-ink-600 px-5 py-4 text-xs whitespace-nowrap">
                  {formatDateTime(order.ordered_at)}
                </td>
                <td className="text-ink-950 px-5 py-4 text-right font-bold">
                  {formatMoney(order.total_minor)}
                </td>
                <td className="pr-4">
                  <Link
                    href={`/app/${organizationSlug}/sales/orders/${order.id}`}
                    aria-label={`View ${order.order_number}`}
                    className="text-ink-400 hover:bg-ink-100 hover:text-ink-900 grid size-9 place-items-center rounded-lg"
                  >
                    <ArrowUpRight className="size-4" aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {orders.map((order) => (
          <article key={order.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link
                  href={`/app/${organizationSlug}/sales/orders/${order.id}`}
                  className="text-ink-950 text-sm font-bold"
                >
                  {order.order_number}
                </Link>
                <p className="text-ink-500 mt-1 text-xs">
                  {formatDateTime(order.ordered_at)}
                </p>
              </div>
              <StatusBadge status={order.status} />
            </div>
            <div className="mt-4 flex items-center gap-3">
              <span className="bg-ink-100 text-ink-600 grid size-9 place-items-center rounded-xl text-[10px] font-bold">
                {order.customer.initials}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-ink-800 truncate text-sm font-semibold">
                  {order.customer.name}
                </p>
                <p className="text-ink-400 truncate text-[10px]">
                  {order.customer.email}
                </p>
              </div>
              <div className="text-right">
                <p className="text-ink-950 text-sm font-bold">
                  {formatMoney(order.total_minor)}
                </p>
                <p className="text-ink-400 text-[10px]">
                  {order.item_count} items
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>
      <PaginationControls
        page={pagination.page}
        totalPages={pagination.total_pages}
        totalItems={pagination.total_items}
        itemLabel="orders"
      />
    </Card>
  );
}
