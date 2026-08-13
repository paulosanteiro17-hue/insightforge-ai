import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export const metadata: Metadata = { title: "Create account" };

export default function SignupPage() {
  return (
    <AuthShell
      eyebrow="Start with clarity"
      title="Create your InsightForge account"
      description="Build a secure analytics workspace and turn your first dataset into a decision-ready view."
    >
      <Suspense
        fallback={
          <div
            className="bg-ink-100 h-[40rem] animate-pulse rounded-2xl"
            aria-label="Loading sign up form"
          />
        }
      >
        <AuthForm mode="sign-up" />
      </Suspense>
    </AuthShell>
  );
}
