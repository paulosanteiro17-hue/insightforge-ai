"use client";

import {
  AlertTriangle,
  Building2,
  Download,
  KeyRound,
  LoaderCircle,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UserRound
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { fieldClassName } from "@/components/administration/admin-utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type {
  AccountPreferences,
  ChangePasswordInput,
  SettingsOrganization,
  SettingsProfile,
  SettingsSnapshot,
  UpdateOrganizationInput,
  UpdateProfileInput
} from "@/lib/api/contracts";

function SectionHeading({
  icon: Icon,
  title,
  description,
  badge
}: {
  icon: typeof UserRound;
  title: string;
  description: string;
  badge?: string;
}) {
  return (
    <div className="border-ink-100 border-b p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="bg-ink-100 text-ink-700 grid size-10 shrink-0 place-items-center rounded-xl">
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-ink-950 text-lg font-bold">{title}</h2>
            {badge ? <Badge>{badge}</Badge> : null}
          </div>
          <p className="text-ink-500 mt-1 text-sm leading-6">{description}</p>
        </div>
      </div>
    </div>
  );
}

export function ProfileSettingsSection({
  profile,
  saving,
  onSubmit
}: {
  profile: SettingsProfile;
  saving: boolean;
  onSubmit: (input: UpdateProfileInput) => void;
}) {
  const [displayName, setDisplayName] = useState(profile.display_name);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      display_name: displayName,
      locale: profile.locale,
      time_zone: profile.time_zone
    });
  }
  return (
    <Card className="overflow-hidden">
      <SectionHeading
        icon={UserRound}
        title="Profile"
        description="Update the identity teammates see across reports, invitations, and workspace activity."
      />
      <form onSubmit={submit} className="p-5 sm:p-6">
        <div className="grid gap-5 sm:grid-cols-2">
          <label>
            <span className="text-ink-700 text-xs font-semibold">
              Display name
            </span>
            <input
              required
              minLength={2}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className={fieldClassName}
              autoComplete="name"
            />
          </label>
          <label className="sm:col-span-2">
            <span className="text-ink-700 text-xs font-semibold">
              Email address
            </span>
            <input
              type="email"
              value={profile.email}
              disabled
              className={fieldClassName}
              aria-describedby="email-protection-note"
            />
            <span
              id="email-protection-note"
              className="text-ink-500 mt-1.5 block text-xs"
            >
              Email changes require identity verification and are disabled in
              demo mode.
            </span>
          </label>
        </div>
        <div className="mt-6 flex justify-end">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : null}
            Save profile
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function OrganizationSettingsSection({
  organization,
  saving,
  canEdit,
  onSubmit
}: {
  organization: SettingsOrganization;
  saving: boolean;
  canEdit: boolean;
  onSubmit: (input: UpdateOrganizationInput) => void;
}) {
  const [name, setName] = useState(organization.name);
  const [timeZone, setTimeZone] = useState(organization.timezone);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      name,
      timezone: timeZone,
      reporting_currency: organization.reporting_currency,
      industry: organization.industry,
      if_match: organization.etag
    });
  }
  return (
    <Card className="overflow-hidden">
      <SectionHeading
        icon={Building2}
        title="Organization"
        description="Manage workspace identity and the reporting boundary used by business metrics."
        badge={canEdit ? "Editable" : "View only"}
      />
      <form onSubmit={submit} className="p-5 sm:p-6">
        {!canEdit ? (
          <div
            className="mb-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
            role="note"
          >
            <ShieldCheck
              className="mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
            <p className="text-xs leading-5">
              Owner or admin permission is required to edit organization
              details.
            </p>
          </div>
        ) : null}
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="text-ink-700 text-xs font-semibold">
              Organization name
            </span>
            <input
              required
              minLength={2}
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={!canEdit}
              className={fieldClassName}
              autoComplete="organization"
            />
          </label>
          <label>
            <span className="text-ink-700 text-xs font-semibold">
              Workspace slug
            </span>
            <input
              value={organization.slug}
              disabled
              className={fieldClassName}
            />
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
              Reporting time zone
            </span>
            <select
              value={timeZone}
              onChange={(event) => setTimeZone(event.target.value)}
              disabled={!canEdit}
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
          <Button type="submit" disabled={!canEdit || saving}>
            {saving ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : null}
            Save organization
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function PreferencesSettingsSection({
  preferences: initialPreferences,
  saving,
  onSubmit
}: {
  preferences: AccountPreferences;
  saving: boolean;
  onSubmit: (preferences: AccountPreferences) => void;
}) {
  const [preferences, setPreferences] = useState(initialPreferences);
  const options: Array<{
    key: keyof AccountPreferences;
    label: string;
    description: string;
  }> = [
    {
      key: "weekly_summary_email",
      label: "Weekly summary email",
      description: "Receive the weekly business summary by email."
    },
    {
      key: "insight_alert_email",
      label: "Insight alerts",
      description: "Receive important analytics and anomaly alerts."
    },
    {
      key: "product_updates_email",
      label: "Product updates",
      description: "Receive occasional product announcements."
    },
    {
      key: "compact_tables",
      label: "Compact tables",
      description: "Fit more rows into business data tables."
    }
  ];
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(preferences);
  }
  return (
    <Card className="overflow-hidden">
      <SectionHeading
        icon={SlidersHorizontal}
        title="Preferences"
        description="Control account notifications and the density of business data tables."
      />
      <form onSubmit={submit} className="p-5 sm:p-6">
        <div className="grid gap-5 sm:grid-cols-2">
          {options.map((option) => (
            <label
              key={option.key}
              className="border-ink-200 flex items-start gap-3 rounded-xl border p-4"
            >
              <input
                type="checkbox"
                checked={preferences[option.key]}
                onChange={(event) =>
                  setPreferences((value) => ({
                    ...value,
                    [option.key]: event.target.checked
                  }))
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
        </div>
        <div className="mt-6 flex justify-end">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : null}
            Save preferences
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function SecuritySettingsSection({
  security,
  saving,
  onChangePassword
}: {
  security: SettingsSnapshot["security"];
  saving: boolean;
  onChangePassword: (input: ChangePasswordInput) => void;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword.length < 12) {
      setLocalError("Use at least 12 characters for the new password.");
      return;
    }
    if (newPassword !== confirmation) {
      setLocalError("The new password confirmation does not match.");
      return;
    }
    setLocalError(null);
    onChangePassword({
      current_password: currentPassword,
      new_password: newPassword
    });
  }
  return (
    <Card className="overflow-hidden">
      <SectionHeading
        icon={KeyRound}
        title="Password"
        description="Change your password and revoke every other active session in one protected operation."
        badge={
          security.password_change_allowed ? "Protected action" : "Unavailable"
        }
      />
      <form onSubmit={submit} className="p-5 sm:p-6">
        <div
          className="mb-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
          role="note"
        >
          <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p className="text-xs leading-5">{security.demo_message}</p>
        </div>
        {localError ? (
          <p
            className="border-coral-200 bg-coral-50 text-coral-800 mb-4 rounded-xl border px-4 py-3 text-sm"
            role="alert"
          >
            {localError}
          </p>
        ) : null}
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="text-ink-700 text-xs font-semibold">
              Current password
            </span>
            <input
              required
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className={fieldClassName}
              autoComplete="current-password"
            />
          </label>
          <label>
            <span className="text-ink-700 text-xs font-semibold">
              New password
            </span>
            <input
              required
              type="password"
              minLength={12}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className={fieldClassName}
              autoComplete="new-password"
            />
          </label>
          <label>
            <span className="text-ink-700 text-xs font-semibold">
              Confirm new password
            </span>
            <input
              required
              type="password"
              minLength={12}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              className={fieldClassName}
              autoComplete="new-password"
            />
          </label>
        </div>
        <div className="mt-6 flex justify-end">
          <Button
            type="submit"
            variant="outline"
            disabled={saving || !security.password_change_allowed}
          >
            {saving ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : (
              <ShieldCheck className="size-4" aria-hidden="true" />
            )}
            Change password
          </Button>
        </div>
      </form>
    </Card>
  );
}

export function DataSettingsSection({
  dataControls,
  organizationName,
  exporting,
  deleting,
  canDelete,
  onExport,
  onDelete
}: {
  dataControls: SettingsSnapshot["data_controls"];
  organizationName: string;
  exporting: boolean;
  deleting: boolean;
  canDelete: boolean;
  onExport: () => void;
  onDelete: (confirmation: string) => void;
}) {
  const [confirmation, setConfirmation] = useState("");
  const confirmationMatches = confirmation === organizationName;
  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <SectionHeading
          icon={Download}
          title="Export workspace data"
          description="Create a tenant-scoped JSON export with a verified SHA-256 digest."
          badge="Time-limited download"
        />
        <div className="p-5 sm:p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-ink-950 text-sm font-semibold">
                Portable JSON export
              </p>
              <p className="text-ink-500 mt-1 max-w-xl text-xs leading-5">
                Exports include this workspace&apos;s portable business data and
                settings, but never credentials, session tokens, or
                cross-workspace data.
              </p>
            </div>
            <Button
              variant="outline"
              disabled={!dataControls.export_available || exporting}
              onClick={onExport}
            >
              {exporting ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <Download className="size-4" aria-hidden="true" />
              )}
              Download export
            </Button>
          </div>
        </div>
      </Card>

      <Card className="border-coral-200 overflow-hidden">
        <SectionHeading
          icon={Trash2}
          title="Delete organization"
          description="Schedule organization deletion after a protected grace period."
          badge="Protected action"
        />
        <div className="p-5 sm:p-6">
          <div
            className="border-coral-200 bg-coral-50 text-coral-900 flex gap-3 rounded-xl border p-4"
            role="note"
          >
            <AlertTriangle
              className="mt-0.5 size-4 shrink-0"
              aria-hidden="true"
            />
            <p className="text-xs leading-5">{dataControls.demo_message}</p>
          </div>
          <label className="mt-5 block">
            <span className="text-ink-700 text-xs font-semibold">
              Type {organizationName} to verify the deletion safeguard
            </span>
            <input
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              className={fieldClassName}
              aria-describedby="delete-safeguard-note"
            />
            <span
              id="delete-safeguard-note"
              className="text-ink-500 mt-1.5 block text-xs"
            >
              A matching value enables the protected deletion request. Demo
              workspaces cannot be deleted from this control.
            </span>
          </label>
          <div className="mt-5 flex justify-end">
            <Button
              variant="danger"
              disabled={
                !confirmationMatches ||
                !canDelete ||
                !dataControls.deletion_allowed ||
                deleting
              }
              onClick={() => onDelete(confirmation)}
            >
              {deleting ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <ShieldCheck className="size-4" aria-hidden="true" />
              )}
              Verify deletion safeguard
            </Button>
          </div>
          {!canDelete ? (
            <p className="text-ink-500 mt-2 text-right text-xs">
              Owner permission is required.
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
