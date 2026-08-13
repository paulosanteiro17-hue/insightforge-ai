"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CreditCard,
  PackageCheck,
  ReceiptText,
  UserRound
} from "lucide-react";
import { DetailSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type OrderDetail as OrderDetailContract,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { formatDateTime, formatMoney } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";

export function OrderDetailContent({
  order,
  organizationSlug
}: {
  order: OrderDetailContract;
  organizationSlug: string;
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Customer",
            value: order.customer.name,
            detail: order.customer.email ?? "No customer email provided",
            icon: UserRound
          },
          {
            label: "Order date",
            value: formatDateTime(order.ordered_at),
            detail: order.source,
            icon: ReceiptText
          },
          {
            label: "Order total",
            value: formatMoney(order.total_minor),
            detail: `${order.currency} reporting currency`,
            icon: CreditCard
          },
          {
            label: "Fulfillment",
            value: `${order.item_count} item${order.item_count === 1 ? "" : "s"}`,
            detail: "Tracked status history",
            icon: PackageCheck
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
              <p className="text-ink-950 mt-1 truncate text-sm font-bold">
                {item.value}
              </p>
              <p className="text-ink-500 mt-1 truncate text-[10px]">
                {item.detail}
              </p>
            </Card>
          );
        })}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.65fr)]">
        <Card className="overflow-hidden">
          <div className="border-ink-100 border-b px-5 py-4">
            <h2 className="text-ink-950 text-lg font-bold">Order items</h2>
            <p className="text-ink-500 mt-1 text-xs">
              Snapshot pricing captured when the order was placed.
            </p>
          </div>
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">
                Products included in {order.order_number}
              </caption>
              <thead className="bg-ink-50 text-ink-500 text-[10px] font-bold tracking-[0.1em] uppercase">
                <tr>
                  <th className="px-5 py-3">Product</th>
                  <th className="px-5 py-3">Quantity</th>
                  <th className="px-5 py-3 text-right">Unit price</th>
                  <th className="px-5 py-3 text-right">Line total</th>
                </tr>
              </thead>
              <tbody className="divide-ink-100 divide-y">
                {order.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-5 py-4">
                      <Link
                        href={`/app/${organizationSlug}/products/${item.product_id}`}
                        className="text-ink-900 font-semibold hover:text-teal-700"
                      >
                        {item.product_name}
                      </Link>
                      <p className="text-ink-400 mt-0.5 font-mono text-[10px]">
                        {item.sku}
                      </p>
                    </td>
                    <td className="text-ink-600 px-5 py-4">{item.quantity}</td>
                    <td className="text-ink-600 px-5 py-4 text-right">
                      {formatMoney(item.unit_price_minor)}
                    </td>
                    <td className="text-ink-950 px-5 py-4 text-right font-bold">
                      {formatMoney(item.line_total_minor)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="divide-ink-100 divide-y sm:hidden">
            {order.items.map((item) => (
              <article key={item.id} className="p-4">
                <div className="flex justify-between gap-3">
                  <div>
                    <Link
                      href={`/app/${organizationSlug}/products/${item.product_id}`}
                      className="text-ink-900 text-sm font-semibold"
                    >
                      {item.product_name}
                    </Link>
                    <p className="text-ink-400 mt-1 font-mono text-[10px]">
                      {item.sku} · Qty {item.quantity}
                    </p>
                  </div>
                  <strong className="text-ink-950 text-sm">
                    {formatMoney(item.line_total_minor)}
                  </strong>
                </div>
              </article>
            ))}
          </div>
          <dl className="border-ink-100 ml-auto max-w-sm space-y-2 border-t px-5 py-5 text-sm">
            <div className="flex justify-between">
              <dt className="text-ink-500">Subtotal</dt>
              <dd className="text-ink-800 font-medium">
                {formatMoney(order.subtotal_minor)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-ink-500">Discount</dt>
              <dd className="text-ink-800 font-medium">
                −{formatMoney(order.discount_minor)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-ink-500">Tax</dt>
              <dd className="text-ink-800 font-medium">
                {formatMoney(order.tax_minor)}
              </dd>
            </div>
            <div className="border-ink-100 mt-3 flex justify-between border-t pt-3">
              <dt className="text-ink-950 font-bold">Total</dt>
              <dd className="text-ink-950 text-lg font-bold">
                {formatMoney(order.total_minor)}
              </dd>
            </div>
          </dl>
        </Card>
        <Card className="p-5">
          <h2 className="text-ink-950 text-lg font-bold">Status history</h2>
          <ol className="mt-5 space-y-0">
            {order.status_history.map((event, index) => (
              <li key={event.id} className="relative flex gap-3 pb-6 last:pb-0">
                {index < order.status_history.length - 1 ? (
                  <span className="bg-ink-200 absolute top-5 left-[9px] h-full w-px" />
                ) : null}
                <span className="mt-1.5 size-[19px] shrink-0 rounded-full border-4 border-white bg-teal-500 shadow-[0_0_0_1px_#afe5dd]" />
                <div>
                  <StatusBadge status={event.to_status} />
                  <p className="text-ink-600 mt-2 text-xs leading-5">
                    {event.reason ??
                      (event.from_status
                        ? `Status changed from ${event.from_status.replaceAll("_", " ")}.`
                        : "Initial order status recorded.")}
                  </p>
                  <p className="text-ink-400 mt-1 text-[10px]">
                    {formatDateTime(event.occurred_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}

export function OrderDetail({
  organization,
  orderId
}: {
  organization: OrganizationSummary;
  orderId: string;
}) {
  const orderQuery = useQuery({
    queryKey: ["organization", organization.id, "orders", orderId],
    queryFn: ({ signal }) =>
      insightForgeApi.orders.getById(organization.id, orderId, signal)
  });
  return (
    <div>
      <Link
        href={`/app/${organization.slug}/sales`}
        className="text-ink-600 hover:text-ink-950 mb-5 inline-flex items-center gap-2 text-sm font-semibold"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Back to sales
      </Link>
      {orderQuery.isPending ? <DetailSkeleton /> : null}
      {orderQuery.isError ? (
        <ErrorState
          title="Order unavailable"
          message={
            orderQuery.error instanceof ApiProblemError
              ? orderQuery.error.problem.detail
              : "The order could not be loaded."
          }
          requestId={
            orderQuery.error instanceof ApiProblemError
              ? orderQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void orderQuery.refetch()}
        />
      ) : null}
      {orderQuery.data ? (
        <>
          <PageHeader
            eyebrow="Order detail"
            title={orderQuery.data.order_number}
            description={`Placed by ${orderQuery.data.customer.name} on ${formatDateTime(orderQuery.data.ordered_at)}.`}
            actions={<StatusBadge status={orderQuery.data.status} />}
          />
          <OrderDetailContent
            order={orderQuery.data}
            organizationSlug={organization.slug}
          />
        </>
      ) : null}
    </div>
  );
}
