"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CustomersTable } from "@/components/customers/customers-table";
import { DataToolbar } from "@/components/data/data-toolbar";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type CustomerListQuery,
  type CustomerSegment,
  type CustomerStatus,
  type OrganizationSummary
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";
import { parseOption, parsePage } from "@/lib/url-state";

const statuses: Array<{ value: CustomerStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "at_risk", label: "At risk" },
  { value: "inactive", label: "Inactive" }
];
const segments: Array<{ value: CustomerSegment; label: string }> = [
  { value: "new", label: "New" },
  { value: "repeat", label: "Repeat" },
  { value: "loyal", label: "Loyal" },
  { value: "high_value", label: "High value" },
  { value: "at_risk", label: "At risk" },
  { value: "inactive", label: "Inactive" }
];
const sorts = [
  "total_spent_desc",
  "total_spent_asc",
  "name_asc",
  "last_order_desc"
] as const;

export function CustomersPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const statusValue = searchParams.get("status");
  const segmentValue = searchParams.get("segment");
  const query: CustomerListQuery = {
    search: searchParams.get("q") || undefined,
    status: statuses.some((item) => item.value === statusValue)
      ? (statusValue as CustomerStatus)
      : undefined,
    segment: segments.some((item) => item.value === segmentValue)
      ? (segmentValue as CustomerSegment)
      : undefined,
    sort: parseOption(searchParams.get("sort"), sorts, "total_spent_desc"),
    page: parsePage(searchParams.get("page")),
    page_size: 6
  };
  const customersQuery = useQuery({
    queryKey: ["organization", organization.id, "customers", query],
    queryFn: ({ signal }) =>
      insightForgeApi.customers.list(organization.id, query, signal)
  });
  return (
    <div>
      <PageHeader
        eyebrow="Customer intelligence"
        title="Customers"
        description={`Understand who drives revenue for ${organization.name}, how recently they purchased, and which relationships need attention.`}
        badge="12 customer profiles"
      />
      <div className="mb-4">
        <DataToolbar
          searchLabel="Search customers"
          searchPlaceholder="Search name, email, or company"
          filters={[
            {
              param: "status",
              label: "Customer status",
              allLabel: "All statuses",
              options: statuses
            },
            {
              param: "segment",
              label: "Customer segment",
              allLabel: "All segments",
              options: segments
            }
          ]}
          sortOptions={[
            { value: "total_spent_desc", label: "Highest lifetime spend" },
            { value: "total_spent_asc", label: "Lowest lifetime spend" },
            { value: "name_asc", label: "Name A–Z" },
            { value: "last_order_desc", label: "Most recent purchase" }
          ]}
        />
      </div>
      {customersQuery.isPending ? <ListSkeleton /> : null}
      {customersQuery.isError ? (
        <ErrorState
          message={
            customersQuery.error instanceof ApiProblemError
              ? customersQuery.error.problem.detail
              : "Customers could not be loaded."
          }
          requestId={
            customersQuery.error instanceof ApiProblemError
              ? customersQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void customersQuery.refetch()}
        />
      ) : null}
      {customersQuery.data && customersQuery.data.items.length === 0 ? (
        <EmptyState
          title="No customers match these filters"
          message="Try another search term, segment, or relationship status."
        />
      ) : null}
      {customersQuery.data && customersQuery.data.items.length > 0 ? (
        <CustomersTable
          customers={customersQuery.data.items}
          pagination={customersQuery.data.pagination}
          organizationSlug={organization.slug}
        />
      ) : null}
    </div>
  );
}
