import type { Metadata } from "next";
import { Suspense } from "react";
import { SalesOrders } from "@/components/sales/sales-orders";
import { ListSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Sales & orders" };

export default async function SalesPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <SalesOrders organization={organization} />
    </Suspense>
  );
}
