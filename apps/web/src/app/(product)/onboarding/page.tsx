import type { Metadata } from "next";
import { GlobalOnboarding } from "@/components/administration/global-onboarding";
import { requireGlobalOnboardingSession } from "@runtime-server-bootstrap";

export const metadata: Metadata = { title: "Create workspace" };

export default async function GlobalOnboardingPage() {
  await requireGlobalOnboardingSession();
  return <GlobalOnboarding />;
}
