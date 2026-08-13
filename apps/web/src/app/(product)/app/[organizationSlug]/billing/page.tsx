import type { Metadata } from "next";
import { BillingPage } from "@/components/administration/billing-page";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Billing" };

export default async function BillingRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return <BillingPage organization={organization} />;
}
