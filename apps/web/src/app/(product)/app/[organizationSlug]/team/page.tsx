import type { Metadata } from "next";
import { TeamPage } from "@/components/administration/team-page";
import { requireOrganization } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Team" };

export default async function TeamRoute({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug);
  return <TeamPage organization={organization} />;
}
