import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { PaginationControls } from "@/components/data/pagination-controls";
import { StatusBadge } from "@/components/data/status-badge";
import { Card } from "@/components/ui/card";
import type { CustomerListItem, PaginationMeta } from "@/lib/api/contracts";
import { formatLongDate, formatMoney } from "@/lib/format";

export function CustomersTable({
  customers,
  pagination,
  organizationSlug
}: {
  customers: CustomerListItem[];
  pagination: PaginationMeta;
  organizationSlug: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">
            Customers matching the selected filters
          </caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Customer</th>
              <th className="px-5 py-3.5">Segment</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Orders</th>
              <th className="px-5 py-3.5">Last purchase</th>
              <th className="px-5 py-3.5 text-right">Lifetime spend</th>
              <th className="w-14">
                <span className="sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {customers.map((customer) => (
              <tr
                key={customer.id}
                className="hover:bg-ink-50/60 transition-colors"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <span className="bg-ink-950 grid size-9 shrink-0 place-items-center rounded-xl text-[10px] font-bold text-white">
                      {customer.initials}
                    </span>
                    <div className="min-w-0">
                      <Link
                        href={`/app/${organizationSlug}/customers/${customer.id}`}
                        className="text-ink-950 truncate font-semibold hover:text-teal-700"
                      >
                        {customer.name}
                      </Link>
                      <p className="text-ink-400 truncate text-[10px]">
                        {customer.company} · {customer.email}
                      </p>
                    </div>
                  </div>
                </td>
                <td className="text-ink-600 px-5 py-4">{customer.segment}</td>
                <td className="px-5 py-4">
                  <StatusBadge status={customer.status} />
                </td>
                <td className="text-ink-600 px-5 py-4">
                  {customer.order_count}
                </td>
                <td className="text-ink-600 px-5 py-4 text-xs whitespace-nowrap">
                  {customer.last_order_at
                    ? formatLongDate(customer.last_order_at)
                    : "No orders"}
                </td>
                <td className="text-ink-950 px-5 py-4 text-right font-bold">
                  {formatMoney(customer.total_spent_minor)}
                </td>
                <td className="pr-4">
                  <Link
                    href={`/app/${organizationSlug}/customers/${customer.id}`}
                    aria-label={`View ${customer.name}`}
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
        {customers.map((customer) => (
          <article key={customer.id} className="p-4">
            <div className="flex items-start gap-3">
              <span className="bg-ink-950 grid size-10 shrink-0 place-items-center rounded-xl text-xs font-bold text-white">
                {customer.initials}
              </span>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/app/${organizationSlug}/customers/${customer.id}`}
                  className="text-ink-950 text-sm font-bold"
                >
                  {customer.name}
                </Link>
                <p className="text-ink-500 mt-0.5 truncate text-xs">
                  {customer.company}
                </p>
              </div>
              <StatusBadge status={customer.status} />
            </div>
            <dl className="bg-ink-50 mt-4 grid grid-cols-3 gap-2 rounded-xl p-3 text-center">
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Spend</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {formatMoney(customer.total_spent_minor)}
                </dd>
              </div>
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Orders</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {customer.order_count}
                </dd>
              </div>
              <div>
                <dt className="text-ink-400 text-[9px] uppercase">Segment</dt>
                <dd className="text-ink-900 mt-1 text-xs font-bold">
                  {customer.segment}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      <PaginationControls
        page={pagination.page}
        totalPages={pagination.total_pages}
        totalItems={pagination.total_items}
        itemLabel="customers"
      />
    </Card>
  );
}
