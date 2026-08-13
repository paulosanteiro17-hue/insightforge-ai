import type { Metadata } from "next";
import { Suspense } from "react";
import { AskDataPage } from "@/components/ai/ask-data-page";
import { DetailSkeleton } from "@/components/data/list-states";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Ask Your Data" };

export default async function AskYourDataRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <AskDataPage organization={organization} />
    </Suspense>
  );
}
