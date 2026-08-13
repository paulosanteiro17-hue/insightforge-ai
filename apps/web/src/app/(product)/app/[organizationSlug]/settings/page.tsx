import type { Metadata } from "next";
import { Suspense } from "react";
import { SettingsPage } from "@/components/administration/settings-page";
import { ListSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<ListSkeleton />}>
      <SettingsPage organization={organization} />
    </Suspense>
  );
}
