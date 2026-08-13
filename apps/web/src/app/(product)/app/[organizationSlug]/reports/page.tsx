import type { Metadata } from "next";
import { Suspense } from "react";
import { ListSkeleton } from "@/components/data/list-states";
import { ReportsPage } from "@/components/reports/reports-page";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Reports" };

export default async function ReportsRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ReportsPage organization={organization} />
    </Suspense>
  );
}
