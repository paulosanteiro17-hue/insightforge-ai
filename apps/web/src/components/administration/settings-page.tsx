"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  ChevronRight,
  Database,
  KeyRound,
  SlidersHorizontal,
  UserRound
} from "lucide-react";
import { useState } from "react";
import {
  downloadTextArtifact,
  getApiErrorMessage
} from "@/components/administration/admin-utils";
import {
  DataSettingsSection,
  OrganizationSettingsSection,
  PreferencesSettingsSection,
  ProfileSettingsSection,
  SecuritySettingsSection
} from "@/components/administration/settings-sections";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import type {
  AccountPreferences,
  ChangePasswordInput,
  OrganizationSummary,
  SettingsSnapshot,
  UpdateOrganizationInput,
  UpdateProfileInput
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { insightForgeApi } from "@runtime-api";

export type SettingsSection =
  "profile" | "organization" | "preferences" | "security" | "data";

const sections: Array<{
  id: SettingsSection;
  label: string;
  description: string;
  icon: typeof UserRound;
}> = [
  {
    id: "profile",
    label: "Profile",
    description: "Identity and email",
    icon: UserRound
  },
  {
    id: "organization",
    label: "Organization",
    description: "Workspace details",
    icon: Building2
  },
  {
    id: "preferences",
    label: "Preferences",
    description: "Dates and summaries",
    icon: SlidersHorizontal
  },
  {
    id: "security",
    label: "Security",
    description: "Password and sessions",
    icon: KeyRound
  },
  {
    id: "data",
    label: "Data controls",
    description: "Export and deletion",
    icon: Database
  }
];

export function parseSettingsSection(value: string | null): SettingsSection {
  return sections.some((section) => section.id === value)
    ? (value as SettingsSection)
    : "profile";
}

type Feedback = { tone: "success" | "error"; message: string };

export function SettingsPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const activeSection = parseSettingsSection(searchParams.get("section"));
  const queryKey = ["organization", organization.id, "settings"];
  const settingsQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      insightForgeApi.settings.get(organization.id, signal)
  });
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  function updateSnapshot(snapshot: SettingsSnapshot) {
    queryClient.setQueryData(queryKey, snapshot);
  }
  const profileMutation = useMutation({
    mutationFn: (input: UpdateProfileInput) =>
      insightForgeApi.settings.updateProfile(organization.id, input),
    onSuccess: (snapshot) => {
      updateSnapshot(snapshot);
      setFeedback({ tone: "success", message: "Profile saved successfully." });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(error, "The profile could not be saved.")
      })
  });
  const organizationMutation = useMutation({
    mutationFn: (input: UpdateOrganizationInput) =>
      insightForgeApi.settings.updateOrganization(organization.id, input),
    onSuccess: (snapshot) => {
      updateSnapshot(snapshot);
      setFeedback({
        tone: "success",
        message: "Organization details saved successfully."
      });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "Organization details could not be saved."
        )
      })
  });
  const preferencesMutation = useMutation({
    mutationFn: (input: AccountPreferences) =>
      insightForgeApi.settings.updatePreferences(organization.id, input),
    onSuccess: (snapshot) => {
      updateSnapshot(snapshot);
      setFeedback({
        tone: "success",
        message: "Preferences saved successfully."
      });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(error, "Preferences could not be saved.")
      })
  });
  const passwordMutation = useMutation({
    mutationFn: (input: ChangePasswordInput) =>
      insightForgeApi.settings.changePassword(organization.id, input),
    onSuccess: () =>
      setFeedback({
        tone: "success",
        message: "Password changed successfully."
      }),
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(error, "The password could not be changed.")
      })
  });
  const exportMutation = useMutation({
    mutationFn: () => insightForgeApi.settings.requestExport(organization.id),
    onSuccess: (artifact) => {
      downloadTextArtifact(artifact);
      setFeedback({
        tone: "success",
        message: `${artifact.filename} downloaded successfully.`
      });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The workspace export could not be created."
        )
      })
  });
  const deleteMutation = useMutation({
    mutationFn: (confirmation: string) =>
      insightForgeApi.settings.deleteOrganization(
        organization.id,
        confirmation
      ),
    onSuccess: () =>
      setFeedback({ tone: "success", message: "Organization deleted." }),
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The organization could not be deleted."
        )
      })
  });

  if (settingsQuery.isPending) return <ListSkeleton />;
  if (settingsQuery.isError) {
    return (
      <ErrorState
        title="Settings could not be loaded"
        message={getApiErrorMessage(
          settingsQuery.error,
          "Account settings are temporarily unavailable."
        )}
        onRetry={() => void settingsQuery.refetch()}
      />
    );
  }

  const settings = settingsQuery.data;
  const activeLabel =
    sections.find((section) => section.id === activeSection)?.label ??
    "Profile";
  function clearFeedback() {
    setFeedback(null);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Account and workspace"
        title="Settings"
        description={`Manage profile, organization, preferences, security, and data controls for ${organization.name}.`}
        badge={activeLabel}
      />

      {feedback ? (
        <div
          role={feedback.tone === "error" ? "alert" : "status"}
          className={cn(
            "mb-5 rounded-xl border px-4 py-3 text-sm font-medium",
            feedback.tone === "success"
              ? "border-teal-200 bg-teal-50 text-teal-800"
              : "border-coral-200 bg-coral-50 text-coral-800"
          )}
        >
          {feedback.message}
        </div>
      ) : null}

      <label className="mb-4 block lg:hidden">
        <span className="text-ink-700 text-xs font-semibold">
          Settings section
        </span>
        <select
          value={activeSection}
          onChange={(event) => {
            clearFeedback();
            router.replace(
              `/app/${organization.slug}/settings?section=${event.target.value}`
            );
          }}
          className="border-ink-200 text-ink-900 mt-2 h-11 w-full rounded-xl border bg-white px-3 text-sm"
        >
          {sections.map((section) => (
            <option key={section.id} value={section.id}>
              {section.label}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-5 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <Card className="hidden h-fit p-2 lg:block">
          <nav aria-label="Settings sections">
            <ul className="space-y-1">
              {sections.map((section) => {
                const Icon = section.icon;
                const active = section.id === activeSection;
                return (
                  <li key={section.id}>
                    <Link
                      href={`/app/${organization.slug}/settings?section=${section.id}`}
                      onClick={clearFeedback}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex min-h-14 items-center gap-3 rounded-xl px-3 transition-colors",
                        active
                          ? "bg-ink-950 text-white"
                          : "text-ink-700 hover:bg-ink-50"
                      )}
                    >
                      <Icon className="size-4 shrink-0" aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold">
                          {section.label}
                        </span>
                        <span
                          className={cn(
                            "mt-0.5 block text-[10px]",
                            active ? "text-ink-300" : "text-ink-400"
                          )}
                        >
                          {section.description}
                        </span>
                      </span>
                      <ChevronRight className="size-3.5" aria-hidden="true" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </Card>

        <div>
          {activeSection === "profile" ? (
            <ProfileSettingsSection
              profile={settings.profile}
              saving={profileMutation.isPending}
              onSubmit={(input) => {
                clearFeedback();
                profileMutation.mutate(input);
              }}
            />
          ) : null}
          {activeSection === "organization" ? (
            <OrganizationSettingsSection
              organization={settings.organization}
              saving={organizationMutation.isPending}
              canEdit={organization.role !== "member"}
              onSubmit={(input) => {
                clearFeedback();
                organizationMutation.mutate(input);
              }}
            />
          ) : null}
          {activeSection === "preferences" ? (
            <PreferencesSettingsSection
              preferences={settings.preferences}
              saving={preferencesMutation.isPending}
              onSubmit={(input) => {
                clearFeedback();
                preferencesMutation.mutate(input);
              }}
            />
          ) : null}
          {activeSection === "security" ? (
            <SecuritySettingsSection
              security={settings.security}
              saving={passwordMutation.isPending}
              onChangePassword={(input) => {
                clearFeedback();
                passwordMutation.mutate(input);
              }}
            />
          ) : null}
          {activeSection === "data" ? (
            <DataSettingsSection
              dataControls={settings.data_controls}
              organizationName={settings.organization.name}
              exporting={exportMutation.isPending}
              deleting={deleteMutation.isPending}
              canDelete={organization.role === "owner"}
              onExport={() => {
                clearFeedback();
                exportMutation.mutate();
              }}
              onDelete={(confirmation) => {
                clearFeedback();
                deleteMutation.mutate(confirmation);
              }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
