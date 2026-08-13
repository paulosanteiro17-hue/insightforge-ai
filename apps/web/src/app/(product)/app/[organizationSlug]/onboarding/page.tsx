import type { Metadata } from "next";
import { Suspense } from "react";
import { OnboardingPage } from "@/components/administration/onboarding-page";
import { ListSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Workspace setup" };

export default async function OnboardingRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug, {
    allowIncomplete: true
  });

  return (
    <Suspense fallback={<ListSkeleton />}>
      <OnboardingPage organization={organization} />
    </Suspense>
  );
}
