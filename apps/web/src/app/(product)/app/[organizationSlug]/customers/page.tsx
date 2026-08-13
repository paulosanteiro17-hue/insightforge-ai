import type { Metadata } from "next";
import { Suspense } from "react";
import { CustomersPage } from "@/components/customers/customers-page";
import { ListSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Customers" };

export default async function CustomerListPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <CustomersPage organization={organization} />
    </Suspense>
  );
}
