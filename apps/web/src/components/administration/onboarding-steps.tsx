"use client";

import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  Database,
  LoaderCircle,
  Sparkles,
  Upload,
  UserRound
} from "lucide-react";
import type { FormEvent } from "react";
import { fieldClassName } from "@/components/administration/admin-utils";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type {
  AccountPreferences,
  OnboardingDataChoice,
  OnboardingSnapshot,
  OnboardingStep,
  OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";

export const onboardingSteps: Array<{
  id: OnboardingStep;
  label: string;
  shortLabel: string;
}> = [
  { id: "organization", label: "Organization", shortLabel: "Workspace" },
  { id: "data", label: "Data setup", shortLabel: "Data" },
  { id: "profile", label: "Profile and preferences", shortLabel: "Profile" },
  { id: "complete", label: "Review and complete", shortLabel: "Review" }
];

const dataChoices: Array<{
  id: OnboardingDataChoice;
  title: string;
  description: string;
  icon: typeof Sparkles;
  note: string;
}> = [
  {
    id: "demo",
    title: "Use demo data",
    description:
      "Explore every dashboard immediately with deterministic commerce data.",
    icon: Sparkles,
    note: "Recommended for a guided product tour"
  },
  {
    id: "csv",
    title: "Import CSV files",
    description:
      "Start with validated customer, product, and order templates after setup.",
    icon: Upload,
    note: "Best when your business data is ready"
  },
  {
    id: "empty",
    title: "Start with an empty workspace",
    description:
      "Configure the workspace now and connect data when your team is ready.",
    icon: Database,
    note: "Dashboards will show clear empty states"
  }
];

export function OnboardingProgress({
  activeStep,
  completed,
  onNavigate
}: {
  activeStep: OnboardingStep;
  completed: boolean;
  onNavigate: (step: OnboardingStep) => void;
}) {
  const stepIndex = onboardingSteps.findIndex((step) => step.id === activeStep);
  return (
    <Card className="mb-5 overflow-hidden">
      <ol className="grid grid-cols-4" aria-label="Onboarding progress">
        {onboardingSteps.map((step, index) => {
          const selected = step.id === activeStep;
          const reached = completed || index <= stepIndex;
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onNavigate(step.id)}
                className={cn(
                  "border-ink-100 flex min-h-20 w-full items-center gap-3 border-r px-3 text-left last:border-r-0 sm:px-5",
                  selected ? "bg-teal-50" : "hover:bg-ink-50 bg-white"
                )}
                aria-current={selected ? "step" : undefined}
              >
                <span
                  className={cn(
                    "grid size-8 shrink-0 place-items-center rounded-full text-xs font-bold",
                    reached
                      ? "bg-teal-600 text-white"
                      : "bg-ink-100 text-ink-500"
                  )}
                >
                  {completed || index < stepIndex ? (
                    <Check className="size-4" aria-hidden="true" />
                  ) : (
                    index + 1
                  )}
                </span>
                <span
                  className={cn(
                    "hidden text-xs font-semibold sm:block",
                    selected ? "text-teal-800" : "text-ink-600"
                  )}
                >
                  <span className="lg:hidden">{step.shortLabel}</span>
                  <span className="hidden lg:inline">{step.label}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

export function OrganizationOnboardingStep({
  name,
  slug,
  timeZone,
  pending,
  onNameChange,
  onSlugChange,
  onTimeZoneChange,
  onSubmit
}: {
  name: string;
  slug: string;
  timeZone: string;
  pending: boolean;
  onNameChange: (value: string) => void;
  onSlugChange: (value: string) => void;
  onTimeZoneChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="grid lg:grid-cols-[0.75fr_1.25fr]">
        <StepIntroduction
          icon={Building2}
          title="Start with the organization"
          description="These values provide the stable workspace identity used throughout reports, imports, and analytics."
          points={[
            "USD is the supported reporting currency",
            "The time zone controls reporting boundaries",
            "The slug uses a stable URL-safe format"
          ]}
        />
        <form onSubmit={onSubmit} className="p-5 sm:p-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="sm:col-span-2">
              <span className="text-ink-700 text-xs font-semibold">
                Organization name
              </span>
              <input
                required
                minLength={2}
                value={name}
                onChange={(event) => onNameChange(event.target.value)}
                className={fieldClassName}
                autoComplete="organization"
              />
            </label>
            <label>
              <span className="text-ink-700 text-xs font-semibold">
                Workspace slug
              </span>
              <input
                required
                pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
                value={slug}
                onChange={(event) => onSlugChange(event.target.value)}
                className={fieldClassName}
                aria-describedby="slug-help"
              />
              <span
                id="slug-help"
                className="text-ink-500 mt-1.5 block text-xs"
              >
                Lowercase letters, numbers, and single hyphens.
              </span>
            </label>
            <label>
              <span className="text-ink-700 text-xs font-semibold">
                Reporting currency
              </span>
              <input
                value="USD — United States dollar"
                disabled
                className={fieldClassName}
              />
            </label>
            <label className="sm:col-span-2">
              <span className="text-ink-700 text-xs font-semibold">
                Organization time zone
              </span>
              <select
                value={timeZone}
                onChange={(event) => onTimeZoneChange(event.target.value)}
                className={fieldClassName}
              >
                <option value="America/New_York">Eastern Time</option>
                <option value="America/Chicago">Central Time</option>
                <option value="America/Denver">Mountain Time</option>
                <option value="America/Los_Angeles">Pacific Time</option>
                <option value="America/Sao_Paulo">Brasília Time</option>
                <option value="UTC">Coordinated Universal Time</option>
              </select>
            </label>
          </div>
          <div className="mt-6 flex justify-end">
            <Button type="submit" disabled={pending}>
              {pending ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : null}
              Save and continue
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
}

export function DataOnboardingStep({
  choice,
  pending,
  onChoiceChange,
  onBack,
  onContinue
}: {
  choice: OnboardingDataChoice | null;
  pending: boolean;
  onChoiceChange: (choice: OnboardingDataChoice) => void;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <Card className="p-5 sm:p-7">
      <div className="max-w-2xl">
        <p className="text-ink-400 text-[10px] font-bold tracking-[0.14em] uppercase">
          Data setup
        </p>
        <h2 className="text-ink-950 mt-2 text-2xl font-bold tracking-[-0.035em]">
          How should this workspace begin?
        </h2>
        <p className="text-ink-600 mt-2 text-sm leading-6">
          This choice is reversible. CSV imports remain validated and demo data
          never contacts an external provider.
        </p>
      </div>
      <div
        className="mt-6 grid gap-4 lg:grid-cols-3"
        role="radiogroup"
        aria-label="Workspace data setup"
      >
        {dataChoices.map((item) => {
          const Icon = item.icon;
          const selected = choice === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChoiceChange(item.id)}
              className={cn(
                "relative rounded-2xl border p-5 text-left transition",
                selected
                  ? "border-teal-500 bg-teal-50 ring-2 ring-teal-500/15"
                  : "border-ink-200 hover:border-ink-300 hover:bg-ink-50"
              )}
            >
              <span
                className={cn(
                  "grid size-10 place-items-center rounded-xl",
                  selected
                    ? "bg-teal-600 text-white"
                    : "bg-ink-100 text-ink-600"
                )}
              >
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="text-ink-950 mt-5 font-bold">{item.title}</h3>
              <p className="text-ink-600 mt-2 text-sm leading-6">
                {item.description}
              </p>
              <p className="text-ink-500 mt-4 text-xs font-medium">
                {item.note}
              </p>
              {selected ? (
                <span className="absolute top-4 right-4 grid size-6 place-items-center rounded-full bg-teal-600 text-white">
                  <Check className="size-3.5" aria-hidden="true" />
                  <span className="sr-only">Selected</span>
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" /> Back
        </Button>
        <Button disabled={!choice || pending} onClick={onContinue}>
          Continue <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </Card>
  );
}

export function ProfileOnboardingStep({
  displayName,
  preferences,
  pending,
  onDisplayNameChange,
  onPreferencesChange,
  onBack,
  onSubmit
}: {
  displayName: string;
  preferences: AccountPreferences;
  pending: boolean;
  onDisplayNameChange: (value: string) => void;
  onPreferencesChange: (preferences: AccountPreferences) => void;
  onBack: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="grid lg:grid-cols-[0.75fr_1.25fr]">
        <StepIntroduction
          icon={UserRound}
          title="Set your working preferences"
          description="Your display name helps collaborators identify you. Notification and table preferences can be changed later."
          points={[
            "Your email remains protected",
            "Notification preferences are stored per account",
            "Every visible date remains in English"
          ]}
        />
        <form onSubmit={onSubmit} className="p-5 sm:p-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <label>
              <span className="text-ink-700 text-xs font-semibold">
                Display name
              </span>
              <input
                required
                minLength={2}
                value={displayName}
                onChange={(event) => onDisplayNameChange(event.target.value)}
                className={fieldClassName}
                autoComplete="name"
              />
            </label>
            <PreferenceFields
              preferences={preferences}
              onChange={onPreferencesChange}
            />
          </div>
          <div className="mt-7 flex flex-wrap items-center justify-between gap-3">
            <Button variant="ghost" onClick={onBack}>
              <ArrowLeft className="size-4" aria-hidden="true" /> Back
            </Button>
            <Button type="submit" disabled={pending}>
              Save and review
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
}

function PreferenceFields({
  preferences,
  onChange
}: {
  preferences: AccountPreferences;
  onChange: (preferences: AccountPreferences) => void;
}) {
  const options: Array<{
    key: keyof AccountPreferences;
    label: string;
    description: string;
  }> = [
    {
      key: "weekly_summary_email",
      label: "Weekly summary email",
      description: "Receive the generated weekly business summary."
    },
    {
      key: "insight_alert_email",
      label: "Insight alerts",
      description: "Receive important analytics and anomaly alerts."
    },
    {
      key: "product_updates_email",
      label: "Product updates",
      description: "Receive occasional InsightForge product announcements."
    },
    {
      key: "compact_tables",
      label: "Compact tables",
      description: "Show more business records in each table view."
    }
  ];
  return (
    <>
      {options.map((option) => (
        <label
          key={option.key}
          className="border-ink-200 flex items-start gap-3 rounded-xl border p-4"
        >
          <input
            type="checkbox"
            checked={preferences[option.key]}
            onChange={(event) =>
              onChange({ ...preferences, [option.key]: event.target.checked })
            }
            className="mt-1 size-4 accent-teal-600"
          />
          <span>
            <span className="text-ink-800 block text-sm font-semibold">
              {option.label}
            </span>
            <span className="text-ink-500 mt-1 block text-xs leading-5">
              {option.description}
            </span>
          </span>
        </label>
      ))}
    </>
  );
}

export function CompleteOnboardingStep({
  snapshot,
  organization,
  completed,
  pending,
  onBack,
  onComplete
}: {
  snapshot: OnboardingSnapshot;
  organization: OrganizationSummary;
  completed: boolean;
  pending: boolean;
  onBack: () => void;
  onComplete: () => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="bg-ink-950 p-6 text-white sm:p-8">
        <span className="grid size-12 place-items-center rounded-2xl bg-teal-500/15 text-teal-300">
          <CheckCircle2 className="size-6" aria-hidden="true" />
        </span>
        <h2 className="mt-5 text-2xl font-bold">
          {completed ? "Your workspace is ready" : "Review the setup"}
        </h2>
        <p className="text-ink-300 mt-2 max-w-2xl text-sm leading-6">
          {completed
            ? "Setup is complete. You can still revisit any step without losing the deterministic demo workspace."
            : "Nothing below triggers external services. Complete setup to continue with the selected data path."}
        </p>
      </div>
      <div className="bg-ink-100 grid gap-px sm:grid-cols-3">
        <ReviewItem
          label="Organization"
          value={snapshot.organization.name}
          detail={`${snapshot.organization.slug} · ${snapshot.organization.timezone}`}
        />
        <ReviewItem
          label="Data path"
          value={
            dataChoices.find((choice) => choice.id === snapshot.data_choice)
              ?.title ?? "Not selected"
          }
          detail="Can be changed from Data Sources"
        />
        <ReviewItem
          label="Profile"
          value={snapshot.profile.display_name}
          detail={snapshot.profile.time_zone}
        />
      </div>
      <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-7">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" /> Back
        </Button>
        {completed ? (
          <div className="flex flex-wrap gap-3">
            {snapshot.data_choice === "csv" ? (
              <Link
                href={`/app/${organization.slug}/data-sources`}
                className={buttonStyles({ variant: "secondary" })}
              >
                Open Data Sources
                <Upload className="size-4" aria-hidden="true" />
              </Link>
            ) : null}
            <Link
              href={`/app/${organization.slug}/overview`}
              className={buttonStyles()}
            >
              Open overview
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {snapshot.data_choice === "csv" ? (
              <Link
                href={`/app/${organization.slug}/data-sources`}
                className={buttonStyles({ variant: "secondary" })}
              >
                Import CSV data
                <Upload className="size-4" aria-hidden="true" />
              </Link>
            ) : null}
            <Button
              disabled={!snapshot.data_choice || pending}
              onClick={onComplete}
            >
              {pending ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : null}
              {snapshot.data_choice === "csv"
                ? "Complete after import"
                : "Complete setup"}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

function StepIntroduction({
  icon: Icon,
  title,
  description,
  points
}: {
  icon: typeof Building2;
  title: string;
  description: string;
  points: string[];
}) {
  return (
    <div className="bg-ink-950 p-6 text-white sm:p-7">
      <span className="grid size-11 place-items-center rounded-xl bg-teal-500/15 text-teal-300">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <h2 className="mt-5 text-xl font-bold">{title}</h2>
      <p className="text-ink-300 mt-2 text-sm leading-6">{description}</p>
      <ul className="mt-6 space-y-3">
        {points.map((point) => (
          <li key={point} className="text-ink-300 flex gap-2 text-xs leading-5">
            <Check
              className="mt-0.5 size-3.5 shrink-0 text-teal-300"
              aria-hidden="true"
            />
            {point}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ReviewItem({
  label,
  value,
  detail
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="bg-white p-5 sm:p-6">
      <p className="text-ink-400 text-[10px] font-bold tracking-[0.12em] uppercase">
        {label}
      </p>
      <p className="text-ink-950 mt-2 font-bold">{value}</p>
      <p className="text-ink-500 mt-1 text-xs leading-5">{detail}</p>
    </div>
  );
}
