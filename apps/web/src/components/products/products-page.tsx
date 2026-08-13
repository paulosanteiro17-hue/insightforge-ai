"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { DataToolbar } from "@/components/data/data-toolbar";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { RangeFilter } from "@/components/dashboard/range-filter";
import { ProductsTable } from "@/components/products/products-table";
import { EmptyState, ErrorState } from "@/components/ui/states";
import {
  ApiProblemError,
  type OrganizationSummary,
  type ProductListQuery,
  type ProductStatus
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";
import { parseAnalyticsRange, parseOption, parsePage } from "@/lib/url-state";

const statuses: Array<{ value: ProductStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" }
];
const categories = ["Software", "Services", "Education", "Add-ons"].map(
  (value) => ({ value, label: value })
);
const sorts = [
  "revenue_desc",
  "revenue_asc",
  "units_desc",
  "name_asc",
  "price_desc"
] as const;

export function ProductsPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const searchParams = useSearchParams();
  const range = parseAnalyticsRange(searchParams.get("range"));
  const statusValue = searchParams.get("status");
  const categoryValue = searchParams.get("category");
  const query: ProductListQuery = {
    search: searchParams.get("q") || undefined,
    status: statuses.some((item) => item.value === statusValue)
      ? (statusValue as ProductStatus)
      : undefined,
    category: categories.some((item) => item.value === categoryValue)
      ? (categoryValue ?? undefined)
      : undefined,
    sort: parseOption(searchParams.get("sort"), sorts, "revenue_desc"),
    page: parsePage(searchParams.get("page")),
    page_size: 5,
    range
  };
  const productsQuery = useQuery({
    queryKey: ["organization", organization.id, "products", query],
    queryFn: ({ signal }) =>
      insightForgeApi.products.list(organization.id, query, signal)
  });
  return (
    <div>
      <PageHeader
        eyebrow="Catalog performance"
        title="Products"
        description={`Compare catalog revenue, unit velocity, price realization, and availability across ${organization.name}.`}
        badge="Performance-aware catalog"
        actions={<RangeFilter value={range} />}
      />
      <div className="mb-4">
        <DataToolbar
          searchLabel="Search products"
          searchPlaceholder="Search product name or SKU"
          filters={[
            {
              param: "status",
              label: "Product status",
              allLabel: "All statuses",
              options: statuses
            },
            {
              param: "category",
              label: "Product category",
              allLabel: "All categories",
              options: categories
            }
          ]}
          sortOptions={[
            { value: "revenue_desc", label: "Highest revenue" },
            { value: "revenue_asc", label: "Lowest revenue" },
            { value: "units_desc", label: "Most units sold" },
            { value: "name_asc", label: "Name A–Z" },
            { value: "price_desc", label: "Highest price" }
          ]}
        />
      </div>
      {productsQuery.isPending ? <ListSkeleton /> : null}
      {productsQuery.isError ? (
        <ErrorState
          message={
            productsQuery.error instanceof ApiProblemError
              ? productsQuery.error.problem.detail
              : "Products could not be loaded."
          }
          requestId={
            productsQuery.error instanceof ApiProblemError
              ? productsQuery.error.problem.request_id
              : undefined
          }
          onRetry={() => void productsQuery.refetch()}
        />
      ) : null}
      {productsQuery.data && productsQuery.data.items.length === 0 ? (
        <EmptyState
          title="No products match these filters"
          message="Try another search term, category, availability state, or reporting period."
        />
      ) : null}
      {productsQuery.data && productsQuery.data.items.length > 0 ? (
        <ProductsTable
          products={productsQuery.data.items}
          pagination={productsQuery.data.pagination}
          organizationSlug={organization.slug}
        />
      ) : null}
    </div>
  );
}
