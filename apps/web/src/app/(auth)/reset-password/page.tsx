import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { PasswordRecoveryConfirmationForm } from "@/components/auth/password-recovery-confirmation-form";

export const metadata: Metadata = { title: "Set a new password" };

export default function ResetPasswordPage() {
  return (
    <AuthShell
      eyebrow="Account recovery"
      title="Set a new password"
      description="Choose a strong password for your InsightForge AI account."
    >
      <Suspense
        fallback={
          <div
            className="bg-ink-100 h-64 animate-pulse rounded-2xl"
            aria-label="Loading password recovery form"
          />
        }
      >
        <PasswordRecoveryConfirmationForm />
      </Suspense>
    </AuthShell>
  );
}
