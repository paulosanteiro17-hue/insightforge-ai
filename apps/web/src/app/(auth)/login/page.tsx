import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to your workspace"
      description="Continue to the decisions, trends, and priorities shaping your business."
    >
      <Suspense
        fallback={
          <div
            className="bg-ink-100 h-[34rem] animate-pulse rounded-2xl"
            aria-label="Loading sign in form"
          />
        }
      >
        <AuthForm mode="sign-in" />
      </Suspense>
    </AuthShell>
  );
}
