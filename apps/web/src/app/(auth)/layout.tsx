import type { Metadata } from "next";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import {
  getServerSession,
  sessionDestination
} from "@runtime-server-bootstrap";

export const metadata: Metadata = {
  robots: { index: false, follow: false }
};

export default async function AuthenticationLayout({
  children
}: {
  children: ReactNode;
}) {
  if (process.env.INSIGHTFORGE_API_MODE !== "mock") {
    const session = await getServerSession();
    if (session) redirect(sessionDestination(session));
  }
  return children;
}
