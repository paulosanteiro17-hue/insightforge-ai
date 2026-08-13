import type { Metadata } from "next";
import { Suspense } from "react";
import { ListSkeleton } from "@/components/data/list-states";
import { ProductsPage } from "@/components/products/products-page";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Products" };

export default async function ProductListPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ProductsPage organization={organization} />
    </Suspense>
  );
}
