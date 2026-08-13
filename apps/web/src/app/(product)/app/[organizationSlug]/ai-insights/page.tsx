import type { Metadata } from "next";
import { Suspense } from "react";
import { InsightsPage } from "@/components/ai/insights-page";
import { ListSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "AI Insights" };

export default async function AiInsightsRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <InsightsPage organization={organization} />
    </Suspense>
  );
}
