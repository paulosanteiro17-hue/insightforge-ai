"use client";

import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  LoaderCircle,
  ShieldCheck,
  UserPlus
} from "lucide-react";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { ApiProblemError } from "@/lib/api/contracts";
import { formatDateTime } from "@/lib/format";
import { insightForgeApi } from "@runtime-api";

export function AcceptInvitationPage({ token }: { token: string }) {
  const preview = useQuery({
    queryKey: ["invitation", token, "preview"],
    queryFn: ({ signal }) =>
      insightForgeApi.team.previewInvitation(token, signal)
  });
  const acceptance = useMutation({
    mutationFn: () => insightForgeApi.team.acceptInvitation(token)
  });
  const requiresSignIn =
    acceptance.error instanceof ApiProblemError &&
    acceptance.error.problem.status === 401;

  return (
    <main
      id="main-content"
      className="bg-ink-50 grid min-h-screen place-items-center px-5 py-12"
    >
      <div className="w-full max-w-xl">
        <div className="text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-teal-100 text-teal-700">
            <UserPlus className="size-5" aria-hidden="true" />
          </span>
          <p className="mt-5 text-xs font-bold tracking-[0.14em] text-teal-700 uppercase">
            Secure workspace invitation
          </p>
          <h1 className="text-ink-950 mt-2 text-3xl font-bold tracking-[-0.05em]">
            Join an InsightForge workspace
          </h1>
        </div>

        <Card className="mt-7 p-6 sm:p-8">
          {preview.isPending ? (
            <div className="space-y-4" aria-label="Loading invitation">
              <LoadingBlock className="h-6 w-2/3" />
              <LoadingBlock className="h-16 w-full" />
              <LoadingBlock className="h-11 w-40" />
            </div>
          ) : null}
          {preview.isError ? (
            <ErrorState
              title="Invitation unavailable"
              message={
                preview.error instanceof ApiProblemError
                  ? preview.error.problem.detail
                  : "This invitation link is invalid, expired, or no longer available."
              }
              onRetry={() => void preview.refetch()}
            />
          ) : null}
          {preview.data && !acceptance.data ? (
            <div>
              <div className="flex items-start gap-3">
                <ShieldCheck
                  className="mt-0.5 size-5 shrink-0 text-teal-600"
                  aria-hidden="true"
                />
                <div>
                  <h2 className="text-ink-950 text-lg font-bold">
                    {preview.data.organization_name}
                  </h2>
                  <p className="text-ink-600 mt-2 text-sm leading-6">
                    This invitation grants the{" "}
                    <strong>{preview.data.role}</strong> role to the account
                    matching {preview.data.email_hint}.
                  </p>
                  <p className="text-ink-400 mt-2 text-xs">
                    Expires {formatDateTime(preview.data.expires_at)}
                  </p>
                </div>
              </div>

              {acceptance.isError ? (
                <div
                  role="alert"
                  className="border-coral-200 bg-coral-50 text-coral-800 mt-5 rounded-xl border p-4 text-sm"
                >
                  {requiresSignIn
                    ? "Sign in with the invited email address before accepting this invitation."
                    : acceptance.error instanceof ApiProblemError
                      ? acceptance.error.problem.detail
                      : "The invitation could not be accepted."}
                </div>
              ) : null}

              <div className="mt-6 flex flex-wrap gap-3">
                {requiresSignIn ? (
                  <Link
                    href={`/login?next=${encodeURIComponent(`/accept-invitation/${token}`)}`}
                    className={buttonStyles()}
                  >
                    Sign in to continue
                  </Link>
                ) : (
                  <Button
                    onClick={() => acceptance.mutate()}
                    disabled={acceptance.isPending}
                  >
                    {acceptance.isPending ? (
                      <LoaderCircle
                        className="size-4 animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <UserPlus className="size-4" aria-hidden="true" />
                    )}
                    {acceptance.isPending
                      ? "Accepting invitation"
                      : "Accept invitation"}
                  </Button>
                )}
                <Link href="/" className={buttonStyles({ variant: "outline" })}>
                  Back to home
                </Link>
              </div>
            </div>
          ) : null}
          {acceptance.data ? (
            <div className="text-center">
              <CheckCircle2
                className="mx-auto size-12 text-teal-600"
                aria-hidden="true"
              />
              <h2 className="text-ink-950 mt-4 text-2xl font-bold">
                Invitation accepted
              </h2>
              <p className="text-ink-600 mt-2 text-sm leading-6">
                You are now a member of {acceptance.data.organization_name}.
              </p>
              <Link href="/app" className={buttonStyles({ className: "mt-6" })}>
                Open workspace
              </Link>
            </div>
          ) : null}
        </Card>
      </div>
    </main>
  );
}
