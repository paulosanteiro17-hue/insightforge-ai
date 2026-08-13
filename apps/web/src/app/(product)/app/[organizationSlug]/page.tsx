import { redirect } from "next/navigation";
import { requireOrganization } from "@runtime-server-bootstrap";

export default async function OrganizationPage({
  params
}: {
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization } = await requireOrganization(organizationSlug, {
    allowIncomplete: true,
    requestedPath: `/app/${organizationSlug}`
  });
  redirect(
    `/app/${organizationSlug}/${
      organization.onboarding_state === "complete" ? "overview" : "onboarding"
    }`
  );
}
