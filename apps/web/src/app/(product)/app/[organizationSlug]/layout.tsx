import type { ReactNode } from "react";
import { ProductShell } from "@/components/product/product-shell";
import { requireOrganization } from "@runtime-server-bootstrap";

export default async function OrganizationLayout({
  children,
  params
}: {
  children: ReactNode;
  params: Promise<{ organizationSlug: string }>;
}) {
  const { organizationSlug } = await params;
  const { organization, organizations, session } = await requireOrganization(
    organizationSlug,
    { allowIncomplete: true }
  );

  return (
    <ProductShell
      organization={organization}
      organizations={organizations}
      user={session.user}
    >
      {children}
    </ProductShell>
  );
}
