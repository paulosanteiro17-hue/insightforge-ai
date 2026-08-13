"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Eye, EyeOff, LoaderCircle, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  ApiProblemError,
  type SignInInput,
  type SignUpInput
} from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";

type AuthMode = "sign-in" | "sign-up";

interface FormState {
  fullName: string;
  email: string;
  password: string;
  acceptedTerms: boolean;
}

type FormErrors = Partial<Record<keyof FormState | "form", string>>;

function safeNextDestination(candidate: string | null): string | null {
  if (
    candidate &&
    candidate.startsWith("/") &&
    !candidate.startsWith("//") &&
    !candidate.includes("\\") &&
    !/[\u0000-\u001f\u007f]/.test(candidate) &&
    !candidate.startsWith("/login") &&
    !candidate.startsWith("/signup") &&
    !candidate.startsWith("/forgot-password")
  ) {
    return candidate;
  }

  return null;
}

function validate(mode: AuthMode, state: FormState): FormErrors {
  const errors: FormErrors = {};

  if (mode === "sign-up" && state.fullName.trim().length < 2) {
    errors.fullName = "Enter your full name.";
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(state.email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (state.password.length < 12) {
    errors.password = "Use at least 12 characters.";
  }

  if (mode === "sign-up" && !state.acceptedTerms) {
    errors.acceptedTerms = "Accept the Terms and Privacy Policy to continue.";
  }

  return errors;
}

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [state, setState] = useState<FormState>({
    fullName: "",
    email: "",
    password: "",
    acceptedTerms: false
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const authMutation = useMutation({
    mutationFn: async () => {
      if (mode === "sign-in") {
        const input: SignInInput = {
          email: state.email.trim(),
          password: state.password
        };
        return insightForgeApi.auth.signIn(input);
      }

      const input: SignUpInput = {
        display_name: state.fullName.trim(),
        email: state.email.trim(),
        password: state.password
      };
      return insightForgeApi.auth.signUp(input);
    },
    onSuccess: (session) => {
      const organization = session.organizations[0];
      const requestedDestination = safeNextDestination(
        searchParams.get("next")
      );
      const requestedOrganization = requestedDestination?.match(
        /^\/app\/([^/]+)(?:\/|$)/
      )?.[1];
      const canUseRequestedDestination =
        requestedDestination &&
        requestedOrganization &&
        session.organizations.some(
          (item) => item.slug === requestedOrganization
        );
      router.replace(
        canUseRequestedDestination
          ? requestedDestination
          : organization
            ? `/app/${organization.slug}/${
                organization.onboarding_state === "complete"
                  ? "overview"
                  : "onboarding"
              }`
            : "/onboarding"
      );
    },
    onError: (error) => {
      setErrors({
        form:
          error instanceof ApiProblemError
            ? error.problem.detail
            : "We could not complete that request. Check your connection and try again."
      });
    }
  });

  const demoMutation = useMutation({
    mutationFn: () => insightForgeApi.auth.createDemoSession(),
    onSuccess: (session) => {
      const organization = session.organizations[0];
      router.replace(
        organization
          ? `/app/${organization.slug}/${
              organization.onboarding_state === "complete"
                ? "overview"
                : "onboarding"
            }`
          : "/onboarding"
      );
    },
    onError: () => {
      setErrors({
        form: "The demo workspace is unavailable right now. Please try again."
      });
    }
  });

  const isPending = authMutation.isPending || demoMutation.isPending;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate(mode, state);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length === 0) {
      authMutation.mutate();
    }
  }

  return (
    <div>
      <Button
        variant="outline"
        size="lg"
        className="w-full border-teal-500/30 bg-teal-50 text-teal-700 hover:bg-teal-100"
        disabled={isPending}
        onClick={() => demoMutation.mutate()}
      >
        {demoMutation.isPending ? (
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        ) : (
          <Sparkles className="size-4" aria-hidden="true" />
        )}
        Open Demo Owner workspace
      </Button>
      <p className="text-ink-500 mt-2 text-center text-xs leading-5">
        One click · isolated data · no reusable credentials
      </p>

      <div className="my-7 flex items-center gap-3" aria-hidden="true">
        <span className="bg-ink-200 h-px flex-1" />
        <span className="text-ink-400 text-[11px] font-semibold tracking-[0.12em] uppercase">
          or continue with email
        </span>
        <span className="bg-ink-200 h-px flex-1" />
      </div>

      {errors.form ? (
        <div
          className="border-coral-500/20 bg-coral-50 text-coral-700 mb-5 rounded-xl border px-4 py-3 text-sm leading-6"
          role="alert"
        >
          {errors.form}
        </div>
      ) : null}

      <form noValidate onSubmit={handleSubmit} className="grid gap-5">
        {mode === "sign-up" ? (
          <div>
            <label
              htmlFor="full-name"
              className="text-ink-800 text-sm font-semibold"
            >
              Full name
            </label>
            <input
              id="full-name"
              name="fullName"
              type="text"
              autoComplete="name"
              value={state.fullName}
              aria-invalid={Boolean(errors.fullName)}
              aria-describedby={errors.fullName ? "full-name-error" : undefined}
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  fullName: event.target.value
                }))
              }
              className="border-ink-200 text-ink-950 placeholder:text-ink-400 mt-2 h-12 w-full rounded-xl border bg-white px-4 text-sm shadow-sm"
              placeholder="Jordan Blake"
            />
            {errors.fullName ? (
              <p
                id="full-name-error"
                className="text-coral-700 mt-1.5 text-xs font-medium"
              >
                {errors.fullName}
              </p>
            ) : null}
          </div>
        ) : null}

        <div>
          <label htmlFor="email" className="text-ink-800 text-sm font-semibold">
            Work email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={state.email}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            onChange={(event) =>
              setState((current) => ({ ...current, email: event.target.value }))
            }
            className="border-ink-200 text-ink-950 placeholder:text-ink-400 mt-2 h-12 w-full rounded-xl border bg-white px-4 text-sm shadow-sm"
            placeholder="you@company.com"
          />
          {errors.email ? (
            <p
              id="email-error"
              className="text-coral-700 mt-1.5 text-xs font-medium"
            >
              {errors.email}
            </p>
          ) : null}
        </div>

        <div>
          <div className="flex items-center justify-between gap-4">
            <label
              htmlFor="password"
              className="text-ink-800 text-sm font-semibold"
            >
              Password
            </label>
            {mode === "sign-in" ? (
              <Link
                href="/forgot-password"
                className="text-xs font-semibold text-teal-700 hover:text-teal-800"
              >
                Forgot password?
              </Link>
            ) : null}
          </div>
          <div className="relative mt-2">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              minLength={12}
              autoComplete={
                mode === "sign-in" ? "current-password" : "new-password"
              }
              value={state.password}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={
                errors.password
                  ? "password-error"
                  : mode === "sign-up"
                    ? "password-help"
                    : undefined
              }
              onChange={(event) =>
                setState((current) => ({
                  ...current,
                  password: event.target.value
                }))
              }
              className="border-ink-200 text-ink-950 placeholder:text-ink-400 h-12 w-full rounded-xl border bg-white pr-12 pl-4 text-sm shadow-sm"
              placeholder={
                mode === "sign-in"
                  ? "Enter your password"
                  : "Create a secure password"
              }
            />
            <button
              type="button"
              className="text-ink-500 hover:text-ink-950 absolute top-0 right-0 grid size-12 place-items-center rounded-xl"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              onClick={() => setShowPassword((current) => !current)}
            >
              {showPassword ? (
                <EyeOff className="size-4" aria-hidden="true" />
              ) : (
                <Eye className="size-4" aria-hidden="true" />
              )}
            </button>
          </div>
          {errors.password ? (
            <p
              id="password-error"
              className="text-coral-700 mt-1.5 text-xs font-medium"
            >
              {errors.password}
            </p>
          ) : mode === "sign-up" ? (
            <p id="password-help" className="text-ink-500 mt-1.5 text-xs">
              Use 12 or more characters. A longer passphrase is stronger.
            </p>
          ) : null}
        </div>

        {mode === "sign-up" ? (
          <div>
            <label className="text-ink-600 flex cursor-pointer items-start gap-3 text-sm leading-6">
              <input
                type="checkbox"
                checked={state.acceptedTerms}
                aria-invalid={Boolean(errors.acceptedTerms)}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    acceptedTerms: event.target.checked
                  }))
                }
                className="border-ink-300 mt-1 size-4 rounded accent-teal-600"
                aria-describedby={
                  errors.acceptedTerms ? "terms-error" : undefined
                }
              />
              <span>
                I agree to the{" "}
                <Link
                  href="/terms"
                  className="text-ink-900 decoration-ink-300 font-semibold underline underline-offset-2"
                >
                  Terms
                </Link>{" "}
                and{" "}
                <Link
                  href="/privacy"
                  className="text-ink-900 decoration-ink-300 font-semibold underline underline-offset-2"
                >
                  Privacy Policy
                </Link>
                .
              </span>
            </label>
            {errors.acceptedTerms ? (
              <p
                id="terms-error"
                className="text-coral-700 mt-1.5 text-xs font-medium"
              >
                {errors.acceptedTerms}
              </p>
            ) : null}
          </div>
        ) : null}

        <Button type="submit" size="lg" className="w-full" disabled={isPending}>
          {authMutation.isPending ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          ) : null}
          {mode === "sign-in" ? "Sign in" : "Create account"}
          {!authMutation.isPending ? (
            <ArrowRight className="size-4" aria-hidden="true" />
          ) : null}
        </Button>
      </form>

      <p className="text-ink-600 mt-7 text-center text-sm">
        {mode === "sign-in"
          ? "New to InsightForge?"
          : "Already have an account?"}{" "}
        <Link
          href={mode === "sign-in" ? "/signup" : "/login"}
          className="rounded font-semibold text-teal-700 hover:text-teal-800"
        >
          {mode === "sign-in" ? "Create an account" : "Sign in"}
        </Link>
      </p>
    </div>
  );
}
