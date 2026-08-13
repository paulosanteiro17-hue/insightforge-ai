"use client";

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { ApiProblemError } from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";

export function PasswordResetForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => insightForgeApi.auth.requestPasswordReset(email.trim()),
    onError: (cause) =>
      setError(
        cause instanceof ApiProblemError
          ? cause.problem.detail
          : "Reset instructions could not be requested. Try again."
      )
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    setError(null);
    mutation.mutate();
  }

  if (mutation.isSuccess) {
    return (
      <div
        className="rounded-2xl border border-teal-500/20 bg-teal-50 p-6"
        role="status"
      >
        <CheckCircle2 className="size-6 text-teal-700" aria-hidden="true" />
        <h2 className="text-ink-950 mt-4 text-lg font-bold">
          Check your inbox
        </h2>
        <p className="text-ink-600 mt-2 text-sm leading-6">
          If an account exists for that address, password reset instructions are
          ready.
        </p>
        {mutation.data.recovery_path ? (
          <a
            href={mutation.data.recovery_path}
            className="mt-5 inline-flex min-h-10 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
          >
            Continue with the local recovery link
          </a>
        ) : null}
      </div>
    );
  }

  return (
    <form noValidate onSubmit={handleSubmit}>
      <label
        htmlFor="reset-email"
        className="text-ink-800 text-sm font-semibold"
      >
        Work email
      </label>
      <input
        id="reset-email"
        type="email"
        inputMode="email"
        autoComplete="email"
        value={email}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? "reset-email-error" : undefined}
        onChange={(event) => setEmail(event.target.value)}
        className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 text-sm shadow-sm"
        placeholder="you@company.com"
      />
      {error ? (
        <p
          id="reset-email-error"
          className="text-coral-700 mt-1.5 text-xs font-medium"
        >
          {error}
        </p>
      ) : null}
      <Button
        type="submit"
        size="lg"
        className="mt-5 w-full"
        disabled={mutation.isPending}
      >
        {mutation.isPending ? (
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        ) : null}
        Send reset instructions
      </Button>
    </form>
  );
}
