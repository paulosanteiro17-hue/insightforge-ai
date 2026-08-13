import type { Metadata } from "next";
import { OrderDetail } from "@/components/sales/order-detail";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Order detail" };

export default async function OrderDetailPage({
  params
}: {
  params: Promise<{ organizationSlug: string; orderId: string }>;
}) {
  const { organizationSlug, orderId } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return <OrderDetail organization={organization} orderId={orderId} />;
}
