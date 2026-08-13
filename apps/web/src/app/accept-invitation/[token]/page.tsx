import type { Metadata } from "next";
import { AcceptInvitationPage } from "@/components/administration/accept-invitation-page";

export const metadata: Metadata = {
  title: "Accept invitation",
  robots: { index: false, follow: false }
};

export default async function InvitationPage({
  params
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <AcceptInvitationPage token={token} />;
}
