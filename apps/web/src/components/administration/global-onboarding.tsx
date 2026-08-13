"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Building2, LoaderCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { BrandMark } from "@/components/brand/brand-mark";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiProblemError } from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function GlobalOnboarding() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [industry, setIndustry] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      insightForgeApi.organizations.create({
        name: name.trim(),
        slug: slug.trim() || undefined,
        reporting_currency: "USD",
        timezone,
        industry: industry.trim() || null
      }),
    onSuccess: (organization) => {
      router.replace(`/app/${organization.slug}/onboarding`);
      router.refresh();
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (name.trim().length < 2) return;
    createMutation.mutate();
  }

  return (
    <main className="bg-ink-50 min-h-screen px-4 py-10 sm:py-16">
      <div className="mx-auto max-w-2xl">
        <BrandMark />
        <Card className="mt-8 overflow-hidden">
          <div className="bg-ink-950 p-6 text-white sm:p-8">
            <span className="grid size-11 place-items-center rounded-2xl bg-teal-400/15 text-teal-300">
              <Building2 className="size-5" aria-hidden="true" />
            </span>
            <p className="mt-6 text-xs font-bold tracking-[0.14em] text-teal-300 uppercase">
              Workspace setup
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">
              Create your organization
            </h1>
            <p className="text-ink-300 mt-3 max-w-xl text-sm leading-6">
              Start with the organization details used for reporting. You can
              choose a data source and finish your profile next.
            </p>
          </div>
          <form className="grid gap-5 p-6 sm:p-8" onSubmit={submit}>
            {createMutation.isError ? (
              <div
                role="alert"
                className="border-coral-200 bg-coral-50 text-coral-800 rounded-xl border px-4 py-3 text-sm"
              >
                {createMutation.error instanceof ApiProblemError
                  ? createMutation.error.problem.detail
                  : "The organization could not be created. Try again."}
              </div>
            ) : null}
            <label className="text-ink-800 text-sm font-semibold">
              Organization name
              <input
                required
                minLength={2}
                maxLength={120}
                value={name}
                onChange={(event) => {
                  setName(event.target.value);
                  if (!slug || slug === slugify(name)) {
                    setSlug(slugify(event.target.value));
                  }
                }}
                className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 font-normal shadow-sm"
                placeholder="Acme Commerce"
              />
            </label>
            <label className="text-ink-800 text-sm font-semibold">
              Workspace URL
              <div className="border-ink-200 mt-2 flex h-12 items-center rounded-xl border bg-white px-4 shadow-sm">
                <span className="text-ink-400 font-normal">/app/</span>
                <input
                  required
                  minLength={2}
                  maxLength={80}
                  pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                  value={slug}
                  onChange={(event) => setSlug(slugify(event.target.value))}
                  className="min-w-0 flex-1 font-normal outline-none"
                  aria-label="Workspace URL slug"
                />
              </div>
            </label>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="text-ink-800 text-sm font-semibold">
                Time zone
                <input
                  required
                  value={timezone}
                  onChange={(event) => setTimezone(event.target.value)}
                  className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 font-normal shadow-sm"
                  placeholder="America/New_York"
                />
              </label>
              <label className="text-ink-800 text-sm font-semibold">
                Industry <span className="text-ink-400">(optional)</span>
                <input
                  maxLength={80}
                  value={industry}
                  onChange={(event) => setIndustry(event.target.value)}
                  className="border-ink-200 mt-2 h-12 w-full rounded-xl border bg-white px-4 font-normal shadow-sm"
                  placeholder="Retail"
                />
              </label>
            </div>
            <div className="flex justify-end">
              <Button
                type="submit"
                size="lg"
                disabled={createMutation.isPending || name.trim().length < 2}
              >
                {createMutation.isPending ? (
                  <LoaderCircle
                    className="size-4 animate-spin"
                    aria-hidden="true"
                  />
                ) : null}
                Continue setup
                {!createMutation.isPending ? (
                  <ArrowRight className="size-4" aria-hidden="true" />
                ) : null}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </main>
  );
}
