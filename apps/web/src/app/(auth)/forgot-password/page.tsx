import type { Metadata } from "next";
import { AuthShell } from "@/components/auth/auth-shell";
import { PasswordResetForm } from "@/components/auth/password-reset-form";

export const metadata: Metadata = { title: "Reset password" };

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      eyebrow="Account recovery"
      title="Reset your password"
      description="Enter your work email. We will send instructions if an account is associated with it."
    >
      <PasswordResetForm />
    </AuthShell>
  );
}
