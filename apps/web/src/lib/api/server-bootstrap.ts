import "server-only";

import { cache } from "react";
import { cookies, headers } from "next/headers";
import { notFound, redirect } from "next/navigation";
import type * as Backend from "@/lib/api/backend-contracts";
import {
  ApiProblemError,
  type OrganizationSummary,
  type SessionView
} from "@/lib/api/contracts";
import { ApiHttpClient } from "@/lib/api/http-client";
import { mapSession } from "@/lib/api/live-mappers";

async function apiBaseUrl(): Promise<{ baseUrl: string; origin: string }> {
  const requestHeaders = await headers();
  const protocol = requestHeaders.get("x-forwarded-proto") ?? "http";
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "127.0.0.1:3000";
  const requestOrigin = `${protocol}://${host}`;
  const internalOrigin =
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ?? requestOrigin;
  return { baseUrl: `${internalOrigin}/api/v1`, origin: requestOrigin };
}

async function serverClient(): Promise<ApiHttpClient> {
  const { baseUrl, origin } = await apiBaseUrl();
  return new ApiHttpClient({
    baseUrl,
    origin,
    credentials: "include",
    defaultHeaders: async () => ({ Cookie: (await cookies()).toString() })
  });
}

export const getServerSession = cache(async (): Promise<SessionView | null> => {
  try {
    const client = await serverClient();
    const response = await client.request<Backend.SessionView>("/auth/session");
    return mapSession(response.data);
  } catch (error) {
    if (
      error instanceof ApiProblemError &&
      (error.problem.status === 401 ||
        error.problem.code === "authentication_required" ||
        error.problem.code === "session_expired")
    ) {
      return null;
    }
    throw error;
  }
});

export async function requireServerSession(
  nextPath = "/app"
): Promise<SessionView> {
  const session = await getServerSession();
  if (!session) {
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }
  return session;
}

export function sessionDestination(session: SessionView): string {
  const organization = session.organizations[0];
  if (!organization) return "/onboarding";
  return `/app/${organization.slug}/${
    organization.onboarding_state === "complete" ? "overview" : "onboarding"
  }`;
}

export async function resolveAppDestination(): Promise<never> {
  const session = await requireServerSession("/app");
  redirect(sessionDestination(session));
}

export async function requireOrganization(
  organizationSlug: string,
  options: { allowIncomplete?: boolean; requestedPath?: string } = {}
): Promise<{
  session: SessionView;
  organization: OrganizationSummary;
  organizations: OrganizationSummary[];
}> {
  const requestedPath =
    options.requestedPath ?? `/app/${organizationSlug}/overview`;
  const session = await requireServerSession(requestedPath);
  if (session.organizations.length === 0) redirect("/onboarding");
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
  return {
    session,
    organization,
    organizations: session.organizations
  };
}

export async function requireGlobalOnboardingSession(): Promise<SessionView> {
  const session = await requireServerSession("/onboarding");
  if (session.organizations.length > 0) redirect(sessionDestination(session));
  return session;
}
