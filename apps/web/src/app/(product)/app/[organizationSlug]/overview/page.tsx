import type { Metadata } from "next";
import { Suspense } from "react";
import { OverviewDashboard } from "@/components/dashboard/overview-dashboard";
import { DashboardSkeleton } from "@/components/ui/states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Overview" };

export default async function OverviewPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);

  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <OverviewDashboard organization={organization} />
    </Suspense>
  );
}
