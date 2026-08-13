import { cache } from "react";
import { notFound, redirect } from "next/navigation";
import type { OrganizationSummary, SessionView } from "@/lib/api/contracts";
import { mockSession } from "@/lib/api/mock-fixtures";

export const getServerSession = cache(async (): Promise<SessionView> =>
  structuredClone(mockSession)
);

export async function requireServerSession(): Promise<SessionView> {
  return getServerSession();
}

export function sessionDestination(session: SessionView): string {
  const organization = session.organizations[0];
  if (!organization) return "/onboarding";
  return `/app/${organization.slug}/${
    organization.onboarding_state === "complete" ? "overview" : "onboarding"
  }`;
}

export async function resolveAppDestination(): Promise<never> {
  redirect(sessionDestination(await getServerSession()));
}

export async function requireOrganization(
  organizationSlug: string,
  options: { allowIncomplete?: boolean; requestedPath?: string } = {}
): Promise<{
  session: SessionView;
  organization: OrganizationSummary;
  organizations: OrganizationSummary[];
}> {
  const session = await getServerSession();
  const organization = session.organizations.find(
    (item) => item.slug === organizationSlug
  );
  if (!organization) notFound();
  if (
    !options.allowIncomplete &&
    organization.onboarding_state !== "complete"
  ) {
    redirect(`/app/${organization.slug}/onboarding`);
  }
  return { session, organization, organizations: session.organizations };
}

export async function requireGlobalOnboardingSession(): Promise<SessionView> {
  const session = await getServerSession();
  if (session.organizations.length > 0) redirect(sessionDestination(session));
  return session;
}
