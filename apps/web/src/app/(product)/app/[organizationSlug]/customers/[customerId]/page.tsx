import type { Metadata } from "next";
import { CustomerDetail } from "@/components/customers/customer-detail";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Customer profile" };

export default async function CustomerDetailPage({
  params
}: {
  params: Promise<{ organizationSlug: string; customerId: string }>;
}) {
  const { organizationSlug, customerId } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return <CustomerDetail organization={organization} customerId={customerId} />;
}
