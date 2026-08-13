"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { DataToolbar } from "@/components/data/data-toolbar";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { OrdersTable } from "@/components/sales/orders-table";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type OrderListQuery,
  type OrderStatus,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange, parseOption, parsePage } from "@/lib/url-state";

const statusOptions: Array<{ value: OrderStatus; label: string }> = [
  { value: "pending", label: "Pending" },
  { value: "paid", label: "Paid" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "refunded", label: "Refunded" }
];
const sortValues = [
  "ordered_at_desc",
  "ordered_at_asc",
  "total_desc",
  "total_asc"
] as const;

export function SalesOrders({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const range = parseAnalyticsRange(searchParams.get("range"));
  const statusValue = searchParams.get("status");
  const status = statusOptions.some((option) => option.value === statusValue)
    ? (statusValue as OrderStatus)
    : undefined;
  const query: OrderListQuery = {
    search: searchParams.get("q") || undefined,
    status,
    sort: parseOption(searchParams.get("sort"), sortValues, "ordered_at_desc"),
    page: parsePage(searchParams.get("page")),
    page_size: 6,
    range
  };
  const ordersQuery = useQuery({
    queryKey: ["organization", organization.id, "orders", query],
    queryFn: ({ signal }) =>
      insightForgeApi.orders.list(organization.id, query, signal)
  });

  return (
    <div>
      <PageHeader
        eyebrow="Revenue operations"
        title="Sales & orders"
        description={`Track every order across ${organization.name}, from first payment signal through completion or refund.`}
        badge="Live order ledger"
        actions={<RangeFilter value={range} />}
      />
      <div className="mb-4">
        <DataToolbar
          searchLabel="Search orders"
          searchPlaceholder="Search order number or customer"
          filters={[
            {
              param: "status",
              label: "Order status",
              allLabel: "All statuses",
              options: statusOptions
            }
          ]}
          sortOptions={[
            { value: "ordered_at_desc", label: "Newest first" },
            { value: "ordered_at_asc", label: "Oldest first" },
            { value: "total_desc", label: "Highest total" },
            { value: "total_asc", label: "Lowest total" }
          ]}
        />
      </div>
      {ordersQuery.isPending ? <ListSkeleton /> : null}
      {ordersQuery.isError ? (
        <ErrorState
          message={
            ordersQuery.error instanceof ApiProblemError
              ? ordersQuery.error.problem.detail
              : "Orders could not be loaded."
          }
          requestId={
            ordersQuery.error instanceof ApiProblemError
              ? ordersQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void ordersQuery.refetch()}
        />
      ) : null}
      {ordersQuery.data && ordersQuery.data.items.length === 0 ? (
        <EmptyState
          title="No orders match these filters"
          message="Clear a filter, broaden the reporting period, or search for another customer."
        />
      ) : null}
      {ordersQuery.data && ordersQuery.data.items.length > 0 ? (
        <OrdersTable
          orders={ordersQuery.data.items}
          pagination={ordersQuery.data.pagination}
          organizationSlug={organization.slug}
        />
      ) : null}
    </div>
  );
}
