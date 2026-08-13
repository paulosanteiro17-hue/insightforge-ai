"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { getApiErrorMessage } from "@/components/administration/admin-utils";
import {
  CompleteOnboardingStep,
  DataOnboardingStep,
  onboardingSteps,
  OnboardingProgress,
  OrganizationOnboardingStep,
  ProfileOnboardingStep
} from "@/components/administration/onboarding-steps";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { ErrorState } from "@/components/ui/states";
import type {
  OnboardingDataChoice,
  OnboardingSnapshot,
  OnboardingStep,
  OrganizationSummary
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { insightForgeApi } from "@runtime-api";

export function parseOnboardingStep(value: string | null): OnboardingStep {
  return onboardingSteps.some((step) => step.id === value)
    ? (value as OnboardingStep)
    : "organization";
}

export function OnboardingPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const queryKey = ["organization", organization.id, "onboarding"];
  const onboardingQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      insightForgeApi.onboarding.get(organization.id, signal)
  });

  if (onboardingQuery.isPending) return <ListSkeleton />;
  if (onboardingQuery.isError) {
    return (
      <ErrorState
        title="Onboarding could not be loaded"
        message={getApiErrorMessage(
          onboardingQuery.error,
          "The setup state is temporarily unavailable."
        )}
        onRetry={() => void onboardingQuery.refetch()}
      />
    );
  }

  return (
    <OnboardingCoordinator
      organization={organization}
      snapshot={onboardingQuery.data}
    />
  );
}

function OnboardingCoordinator({
  organization,
  snapshot
}: {
  organization: OrganizationSummary;
  snapshot: OnboardingSnapshot;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const activeStep = parseOnboardingStep(searchParams.get("step"));
  const queryKey = ["organization", organization.id, "onboarding"];
  const [organizationName, setOrganizationName] = useState(
    snapshot.organization.name
  );
  const [organizationSlug, setOrganizationSlug] = useState(
    snapshot.organization.slug
  );
  const [organizationTimeZone, setOrganizationTimeZone] = useState(
    snapshot.organization.timezone
  );
  const [dataChoice, setDataChoice] = useState<OnboardingDataChoice | null>(
    snapshot.data_choice
  );
  const [displayName, setDisplayName] = useState(snapshot.profile.display_name);
  const [preferences, setPreferences] = useState(snapshot.preferences);
  const [feedback, setFeedback] = useState<string | null>(null);

  function navigate(step: OnboardingStep) {
    setFeedback(null);
    router.replace(`/app/${organization.slug}/onboarding?step=${step}`, {
      scroll: false
    });
  }

  const organizationMutation = useMutation({
    mutationFn: () =>
      insightForgeApi.onboarding.saveOrganization(organization.id, {
        name: organizationName,
        slug: organizationSlug,
        timezone: organizationTimeZone,
        reporting_currency: snapshot.organization.reporting_currency,
        industry: snapshot.organization.industry
      }),
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKey, snapshot);
      navigate("data");
    },
    onError: (error) =>
      setFeedback(
        getApiErrorMessage(error, "Organization details could not be saved.")
      )
  });
  const dataMutation = useMutation({
    mutationFn: () => {
      if (!dataChoice) throw new Error("Choose a data setup option.");
      return insightForgeApi.onboarding.chooseData(organization.id, {
        choice: dataChoice
      });
    },
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKey, snapshot);
      navigate("profile");
    },
    onError: (error) =>
      setFeedback(
        getApiErrorMessage(error, "Choose a data setup option to continue.")
      )
  });
  const profileMutation = useMutation({
    mutationFn: () =>
      insightForgeApi.onboarding.saveProfile(organization.id, {
        profile: {
          display_name: displayName,
          locale: snapshot.profile.locale,
          time_zone: snapshot.profile.time_zone
        },
        preferences
      }),
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKey, snapshot);
      navigate("complete");
    },
    onError: (error) =>
      setFeedback(
        getApiErrorMessage(error, "Profile details could not be saved.")
      )
  });
  const completeMutation = useMutation({
    mutationFn: () => insightForgeApi.onboarding.complete(organization.id),
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKey, snapshot);
      setFeedback("Workspace setup is complete.");
    },
    onError: (error) =>
      setFeedback(
        getApiErrorMessage(error, "Workspace setup could not be completed.")
      )
  });

  const completed = Boolean(snapshot.completed_at);
  const stepIndex = onboardingSteps.findIndex((step) => step.id === activeStep);
  const mutationPending =
    organizationMutation.isPending ||
    dataMutation.isPending ||
    profileMutation.isPending ||
    completeMutation.isPending;

  function submitOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    organizationMutation.mutate();
  }

  function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    profileMutation.mutate();
  }

  return (
    <div>
      <PageHeader
        eyebrow="Workspace setup"
        title="Make InsightForge yours"
        description="Confirm the organization, choose a safe data path, and set the preferences that shape your workspace. You can revisit every setting later."
        badge={completed ? "Setup complete" : `Step ${stepIndex + 1} of 4`}
      />
      <OnboardingProgress
        activeStep={activeStep}
        completed={completed}
        onNavigate={navigate}
      />
      {feedback ? (
        <div
          className={cn(
            "mb-5 rounded-xl border px-4 py-3 text-sm font-medium",
            completed
              ? "border-teal-200 bg-teal-50 text-teal-800"
              : "border-coral-200 bg-coral-50 text-coral-800"
          )}
          role="status"
        >
          {feedback}
        </div>
      ) : null}
      {activeStep === "organization" ? (
        <OrganizationOnboardingStep
          name={organizationName}
          slug={organizationSlug}
          timeZone={organizationTimeZone}
          pending={organizationMutation.isPending}
          onNameChange={setOrganizationName}
          onSlugChange={setOrganizationSlug}
          onTimeZoneChange={setOrganizationTimeZone}
          onSubmit={submitOrganization}
        />
      ) : null}
      {activeStep === "data" ? (
        <DataOnboardingStep
          choice={dataChoice}
          pending={dataMutation.isPending}
          onChoiceChange={setDataChoice}
          onBack={() => navigate("organization")}
          onContinue={() => {
            setFeedback(null);
            dataMutation.mutate();
          }}
        />
      ) : null}
      {activeStep === "profile" ? (
        <ProfileOnboardingStep
          displayName={displayName}
          preferences={preferences}
          pending={profileMutation.isPending}
          onDisplayNameChange={setDisplayName}
          onPreferencesChange={setPreferences}
          onBack={() => navigate("data")}
          onSubmit={submitProfile}
        />
      ) : null}
      {activeStep === "complete" ? (
        <CompleteOnboardingStep
          snapshot={snapshot}
          organization={organization}
          completed={completed}
          pending={completeMutation.isPending}
          onBack={() => navigate("profile")}
          onComplete={() => {
            setFeedback(null);
            completeMutation.mutate();
          }}
        />
      ) : null}
      {mutationPending ? (
        <span className="sr-only" role="status">
          Saving onboarding progress.
        </span>
      ) : null}
    </div>
  );
}
