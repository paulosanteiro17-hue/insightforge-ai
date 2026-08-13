"use client";

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { ApiProblemError } from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";

const subscribeToHydration = () => () => undefined;

export function PasswordRecoveryConfirmationForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const hydrated = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false
  );
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (input: { token: string; password: string }) =>
      insightForgeApi.auth.confirmPasswordReset(input.token, input.password),
    onError: (cause) =>
      setError(
        cause instanceof ApiProblemError
          ? cause.problem.detail
          : "The password could not be reset. Request a new recovery link."
      )
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const password = String(formData.get("password") ?? "");
    const confirmation = String(formData.get("password_confirmation") ?? "");
    if (!token) {
      setError("This recovery link is incomplete. Request a new one.");
      return;
    }
    if (password.length < 12) {
      setError("Use at least 12 characters for the new password.");
      return;
    }
    if (password !== confirmation) {
      setError("The password confirmation does not match.");
      return;
    }
    setError(null);
    mutation.mutate({ token, password });
  }

  if (mutation.isSuccess) {
    return (
      <div
        className="rounded-2xl border border-teal-500/20 bg-teal-50 p-6"
        role="status"
      >
        <CheckCircle2 className="size-6 text-teal-700" aria-hidden="true" />
        <h2 className="text-ink-950 mt-4 text-lg font-bold">
          Password updated
        </h2>
        <p className="text-ink-600 mt-2 text-sm leading-6">
          Existing sessions were revoked. Sign in again with your new password.
        </p>
        <Link
          href="/login"
          className="mt-5 inline-flex min-h-10 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
        >
          Return to sign in
        </Link>
      </div>
    );
  }

  return (
    <form noValidate onSubmit={submit}>
      <label
        htmlFor="new-password"
        className="text-ink-800 text-sm font-semibold"
      >
        New password
      </label>
      <input
        id="new-password"
        name="password"
        type="password"
        autoComplete="new-password"
        disabled={!hydrated}
        className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 text-sm shadow-sm"
      />
      <label
        htmlFor="confirm-password"
        className="text-ink-800 mt-4 block text-sm font-semibold"
      >
        Confirm new password
      </label>
      <input
        id="confirm-password"
        name="password_confirmation"
        type="password"
        autoComplete="new-password"
        disabled={!hydrated}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "password-recovery-error" : undefined}
        className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 text-sm shadow-sm"
      />
      {error ? (
        <p
          id="password-recovery-error"
          className="text-coral-700 mt-2 text-xs font-medium"
        >
          {error}
        </p>
      ) : null}
      <Button
        type="submit"
        size="lg"
        className="mt-5 w-full"
        disabled={!hydrated || mutation.isPending}
      >
        {mutation.isPending ? (
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        ) : null}
        Set new password
      </Button>
    </form>
  );
}
