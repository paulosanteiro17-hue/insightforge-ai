"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  Mail,
  ShoppingBag
} from "lucide-react";
import { DetailSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { StatusBadge } from "@/components/data/status-badge";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type CustomerDetail as CustomerDetailContract,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";
import { formatDateTime, formatLongDate, formatMoney } from "@/lib/format";

export function CustomerDetailContent({
  customer,
  organizationSlug
}: {
  customer: CustomerDetailContract;
  organizationSlug: string;
}) {
  const cards = [
    {
      label: "Lifetime spend",
      value: formatMoney(customer.total_spent_minor),
      detail: `${customer.order_count} eligible orders`,
      icon: ShoppingBag
    },
    {
      label: "Average order value",
      value:
        customer.metrics.average_order_value_minor === null
          ? "Not available"
          : formatMoney(customer.metrics.average_order_value_minor),
      detail: "Across all eligible orders",
      icon: Building2
    },
    {
      label: "Last purchase",
      value: customer.last_order_at
        ? formatLongDate(customer.last_order_at)
        : "No purchase",
      detail:
        customer.metrics.recency_days === null
          ? "No completed order yet"
          : `${customer.metrics.recency_days} days since the last order`,
      icon: CalendarDays
    },
    {
      label: "Customer since",
      value: formatLongDate(customer.acquired_at),
      detail: customer.external_id
        ? `External ID ${customer.external_id}`
        : "Created in InsightForge",
      icon: CalendarDays
    }
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label} className="p-4">
              <span className="bg-ink-50 text-ink-600 grid size-9 place-items-center rounded-xl">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <p className="text-ink-400 mt-3 text-[10px] font-bold tracking-[0.11em] uppercase">
                {item.label}
              </p>
              <p className="text-ink-950 mt-1 text-base font-bold">
                {item.value}
              </p>
              <p className="text-ink-500 mt-1 text-[10px]">{item.detail}</p>
            </Card>
          );
        })}
      </div>

      <Card className="p-5">
        <h2 className="text-ink-950 text-lg font-bold">Customer profile</h2>
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="text-ink-400 text-[10px] font-bold uppercase">
              Company
            </dt>
            <dd className="text-ink-800 mt-1 font-semibold">
              {customer.company ?? "Not provided"}
            </dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] font-bold uppercase">
              Email
            </dt>
            <dd className="text-ink-800 mt-1 flex items-center gap-2 break-all">
              <Mail className="size-4 shrink-0" aria-hidden="true" />
              {customer.email ?? "Not provided"}
            </dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] font-bold uppercase">
              Segment
            </dt>
            <dd className="text-ink-800 mt-1 capitalize">
              {customer.segment.replace("_", " ")}
            </dd>
          </div>
          <div>
            <dt className="text-ink-400 text-[10px] font-bold uppercase">
              Status
            </dt>
            <dd className="mt-1">
              <StatusBadge status={customer.status} />
            </dd>
          </div>
        </dl>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-ink-100 border-b px-5 py-4">
          <h2 className="text-ink-950 text-lg font-bold">Recent orders</h2>
          <p className="text-ink-500 mt-1 text-xs">
            The latest order history associated with this customer.
          </p>
        </div>
        {customer.recent_orders.length ? (
          <div className="divide-ink-100 divide-y">
            {customer.recent_orders.map((order) => (
              <Link
                key={order.id}
                href={`/app/${organizationSlug}/sales/orders/${order.id}`}
                className="hover:bg-ink-50 flex flex-col gap-3 px-5 py-4 transition-colors sm:flex-row sm:items-center"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-ink-950 text-sm font-semibold">
                    {order.order_number}
                  </p>
                  <p className="text-ink-400 mt-1 text-[10px]">
                    {formatDateTime(order.ordered_at)} · {order.item_count}{" "}
                    items
                  </p>
                </div>
                <StatusBadge status={order.status} />
                <strong className="text-ink-950 text-sm sm:w-24 sm:text-right">
                  {formatMoney(order.total_minor)}
                </strong>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-ink-500 p-8 text-center text-sm">
            No orders are available for this customer.
          </p>
        )}
      </Card>
    </div>
  );
}

export function CustomerDetail({
  organization,
  customerId
}: {
  organization: OrganizationSummary;
  customerId: string;
}) {
  const customerQuery = useQuery({
    queryKey: ["organization", organization.id, "customers", customerId],
    queryFn: ({ signal }) =>
      insightForgeApi.customers.getById(organization.id, customerId, signal)
  });

  return (
    <div>
      <Link
        href={`/app/${organization.slug}/customers`}
        className="text-ink-600 hover:text-ink-950 mb-5 inline-flex items-center gap-2 text-sm font-semibold"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> Back to customers
      </Link>
      {customerQuery.isPending ? <DetailSkeleton /> : null}
      {customerQuery.isError ? (
        <ErrorState
          title="Customer unavailable"
          message={
            customerQuery.error instanceof ApiProblemError
              ? customerQuery.error.problem.detail
              : "The customer could not be loaded."
          }
          requestId={
            customerQuery.error instanceof ApiProblemError
              ? customerQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void customerQuery.refetch()}
        />
      ) : null}
      {customerQuery.data ? (
        <>
          <PageHeader
            eyebrow="Customer profile"
            title={customerQuery.data.name}
            description={
              [customerQuery.data.company, customerQuery.data.email]
                .filter(Boolean)
                .join(" · ") || "Customer details"
            }
            actions={<StatusBadge status={customerQuery.data.status} />}
          />
          <CustomerDetailContent
            customer={customerQuery.data}
            organizationSlug={organization.slug}
          />
        </>
      ) : null}
    </div>
  );
}
