import type { Metadata } from "next";
import { Suspense } from "react";
import { AnalyticsDashboard } from "@/components/analytics/analytics-dashboard";
import { DashboardSkeleton } from "@/components/ui/states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Analytics" };

export default async function AnalyticsPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <AnalyticsDashboard organization={organization} />
    </Suspense>
  );
}
