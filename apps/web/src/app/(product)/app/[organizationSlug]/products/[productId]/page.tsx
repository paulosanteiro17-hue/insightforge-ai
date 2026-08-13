import type { Metadata } from "next";
import { Suspense } from "react";
import { DetailSkeleton } from "@/components/data/list-states";
import { ProductDetail } from "@/components/products/product-detail";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Product performance" };

export default async function ProductDetailPage({
  params
}: {
  params: Promise<{ organizationSlug: string; productId: string }>;
}) {
  const { organizationSlug, productId } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ProductDetail organization={organization} productId={productId} />
    </Suspense>
  );
}
