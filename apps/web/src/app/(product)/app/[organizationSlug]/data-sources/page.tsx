import type { Metadata } from "next";
import { Suspense } from "react";
import { ListSkeleton } from "@/components/data/list-states";
import { DataSourcesPage } from "@/components/imports/data-sources-page";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Data Sources" };

export default async function DataSourcesRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <DataSourcesPage organization={organization} />
    </Suspense>
  );
}
