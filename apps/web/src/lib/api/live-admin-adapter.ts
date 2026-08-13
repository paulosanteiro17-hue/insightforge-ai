import type * as Backend from "@/lib/api/backend-contracts";
import {
  ApiProblemError,
  type BillingOverview,
  type InsightForgeApi,
  type OnboardingDataChoice,
  type OnboardingSnapshot,
  type SettingsSnapshot,
  type TeamInvitation,
  type TeamMember
} from "@/lib/api/contracts";
import { ApiHttpClient, pollUntil } from "@/lib/api/http-client";

interface InvitationDeliveryView extends Backend.InvitationView {
  acceptance_token: string;
}

interface OnboardingChoiceState {
  choice: OnboardingDataChoice;
  sourceJobId: string | null;
}

function onboardingStorageKey(organizationId: string): string {
  return `insightforge:onboarding-choice:${organizationId}`;
}

function readOnboardingChoice(
  organizationId: string
): OnboardingChoiceState | undefined {
  try {
    const value = globalThis.sessionStorage?.getItem(
      onboardingStorageKey(organizationId)
    );
    if (!value) return undefined;
    const parsed = JSON.parse(value) as Partial<OnboardingChoiceState>;
    if (!parsed.choice || !["demo", "csv", "empty"].includes(parsed.choice)) {
      return undefined;
    }
    return {
      choice: parsed.choice,
      sourceJobId:
        typeof parsed.sourceJobId === "string" ? parsed.sourceJobId : null
    };
  } catch {
    return undefined;
  }
}

function storeOnboardingChoice(
  organizationId: string,
  state: OnboardingChoiceState
): void {
  try {
    globalThis.sessionStorage?.setItem(
      onboardingStorageKey(organizationId),
      JSON.stringify(state)
    );
  } catch {
    // A blocked session store should not prevent onboarding in the active tab.
  }
}

function clientProblem(
  detail: string,
  code = "invalid_state"
): ApiProblemError {
  return new ApiProblemError({
    title: "Action unavailable",
    detail,
    status: 409,
    code,
    request_id: "client"
  });
}

function teamMember(
  value: Backend.TeamMemberView,
  currentUserId: string
): TeamMember {
  return { ...value, is_current_user: value.user_id === currentUserId };
}

function invitation(value: Backend.InvitationView): TeamInvitation {
  return { ...value };
}

export function createLiveAdminApi(
  client: ApiHttpClient
): Pick<InsightForgeApi, "onboarding" | "team" | "billing" | "settings"> {
  const onboardingChoices = new Map<string, OnboardingChoiceState>();

  async function currentOrganization(
    organizationId: string,
    signal?: AbortSignal
  ) {
    return client.request<Backend.CurrentOrganizationView>(
      "/organizations/current",
      { organizationId, signal }
    );
  }

  async function currentUser(signal?: AbortSignal) {
    return client.request<Backend.CurrentUserView>("/users/me", { signal });
  }

  async function onboardingSnapshot(
    organizationId: string,
    signal?: AbortSignal
  ): Promise<OnboardingSnapshot> {
    const [organization, user] = await Promise.all([
      currentOrganization(organizationId, signal),
      currentUser(signal)
    ]);
    const storedChoice =
      onboardingChoices.get(organizationId) ??
      readOnboardingChoice(organizationId);
    if (storedChoice) onboardingChoices.set(organizationId, storedChoice);
    const choice = storedChoice?.choice ?? null;
    return {
      organization_id: organizationId,
      current_step: organization.data.onboarding_state,
      completed_at:
        organization.data.onboarding_state === "complete"
          ? new Date().toISOString()
          : null,
      organization: {
        name: organization.data.name,
        slug: organization.data.slug,
        timezone: organization.data.timezone,
        reporting_currency: organization.data.reporting_currency,
        industry: organization.data.industry
      },
      data_choice: choice,
      profile: {
        display_name: user.data.display_name,
        locale: user.data.locale,
        time_zone: user.data.time_zone
      },
      preferences: { ...user.data.preferences }
    };
  }

  async function settingsSnapshot(
    organizationId: string,
    signal?: AbortSignal
  ): Promise<SettingsSnapshot> {
    const [organization, user] = await Promise.all([
      currentOrganization(organizationId, signal),
      currentUser(signal)
    ]);
    const demoMessage = organization.data.is_demo
      ? "Sensitive account actions are unavailable in demo workspaces."
      : "Account changes are protected by your current authenticated session.";
    return {
      organization_id: organizationId,
      profile: {
        display_name: user.data.display_name,
        email: user.data.email,
        locale: user.data.locale,
        time_zone: user.data.time_zone
      },
      organization: {
        name: organization.data.name,
        slug: organization.data.slug,
        timezone: organization.data.timezone,
        reporting_currency: organization.data.reporting_currency,
        industry: organization.data.industry,
        etag: organization.etag ?? `"${organization.data.version}"`
      },
      preferences: { ...user.data.preferences },
      security: {
        password_change_allowed: !organization.data.is_demo,
        demo_message: demoMessage
      },
      data_controls: {
        export_available: !organization.data.is_demo,
        deletion_allowed:
          !organization.data.is_demo && organization.data.role === "owner",
        demo_message: demoMessage
      }
    };
  }

  return {
    onboarding: {
      get: onboardingSnapshot,
      async saveOrganization(organizationId, input, signal) {
        const current = await currentOrganization(organizationId, signal);
        await client.request<Backend.CurrentOrganizationView>(
          "/organizations/current",
          {
            method: "PATCH",
            organizationId,
            ifMatch: current.etag ?? `"${current.data.version}"`,
            json: input,
            signal
          }
        );
        return onboardingSnapshot(organizationId, signal);
      },
      async chooseData(organizationId, input, signal) {
        let sourceJobId: string | null = null;
        if (input.choice === "demo") {
          const created = await client.request<Backend.OrganizationJobView>(
            "/organizations/current/demo-data-jobs",
            {
              method: "POST",
              organizationId,
              idempotent: true,
              json: {},
              signal
            }
          );
          const completed = await pollUntil(
            async (pollSignal) =>
              (
                await client.request<Backend.OrganizationJobView>(
                  `/organizations/current/demo-data-jobs/${created.data.id}`,
                  { organizationId, signal: pollSignal }
                )
              ).data,
            {
              signal,
              isComplete: (value) => value.status === "succeeded",
              isFailed: (value) =>
                value.status === "failed" || value.status === "cancelled"
            }
          );
          if (completed.status !== "succeeded") {
            throw clientProblem(
              "Demo data generation did not complete. Try again or start with an empty workspace.",
              "job_failed"
            );
          }
          sourceJobId = completed.id;
        }
        const choiceState = {
          choice: input.choice,
          sourceJobId
        };
        onboardingChoices.set(organizationId, choiceState);
        storeOnboardingChoice(organizationId, choiceState);
        return onboardingSnapshot(organizationId, signal);
      },
      async saveProfile(organizationId, input, signal) {
        await Promise.all([
          client.request<Backend.CurrentUserView>("/users/me", {
            method: "PATCH",
            json: input.profile,
            signal
          }),
          client.request<Backend.PreferenceView>("/users/me/preferences", {
            method: "PATCH",
            json: input.preferences,
            signal
          })
        ]);
        return onboardingSnapshot(organizationId, signal);
      },
      async complete(organizationId, signal) {
        const choice =
          onboardingChoices.get(organizationId) ??
          readOnboardingChoice(organizationId);
        if (!choice) {
          throw clientProblem(
            "Choose demo data or an empty workspace before continuing."
          );
        }
        await client.request<Backend.CurrentOrganizationView>(
          "/organizations/current/onboarding/complete",
          {
            method: "POST",
            organizationId,
            json: {
              source_job_id: choice.sourceJobId,
              empty_workspace: choice.choice === "empty"
            },
            signal
          }
        );
        return onboardingSnapshot(organizationId, signal);
      }
    },
    team: {
      async previewInvitation(token, signal) {
        const response = await client.request<Backend.InvitationPreviewView>(
          `/team/invitations/accept/${encodeURIComponent(token)}`,
          { signal }
        );
        return response.data;
      },
      async acceptInvitation(token, signal) {
        const response = await client.request<Backend.InvitationAcceptedView>(
          `/team/invitations/accept/${encodeURIComponent(token)}`,
          { method: "POST", idempotent: true, json: {}, signal }
        );
        return {
          ...response.data,
          member: { ...response.data.member, is_current_user: true }
        };
      },
      async getOverview(organizationId, signal) {
        const [members, invitations, organization, user] = await Promise.all([
          client.collection<Backend.TeamMemberView>("/team/members", {
            organizationId,
            query: { page: 1, page_size: 100 },
            signal
          }),
          client.collection<Backend.InvitationView>("/team/invitations", {
            organizationId,
            query: { page: 1, page_size: 100 },
            signal
          }),
          currentOrganization(organizationId, signal),
          currentUser(signal)
        ]);
        return {
          organization_id: organizationId,
          current_user_role: organization.data.role,
          can_manage_members:
            organization.data.permissions.includes("invite_members"),
          demo_policy: organization.data.is_demo
            ? "Team changes are unavailable in demo workspaces."
            : "Invitations create a one-time acceptance link for secure sharing.",
          members: members.data.map((member) =>
            teamMember(member, user.data.id)
          ),
          invitations: invitations.data.map(invitation)
        };
      },
      async invite(organizationId, input, signal) {
        const response = await client.request<InvitationDeliveryView>(
          "/team/invitations",
          {
            method: "POST",
            organizationId,
            idempotent: true,
            json: input,
            signal
          }
        );
        return {
          ...invitation(response.data),
          acceptance_token: response.data.acceptance_token
        };
      },
      async changeRole(organizationId, memberId, role, signal) {
        if (role === "owner") {
          throw clientProblem(
            "Ownership cannot be assigned from the member role control."
          );
        }
        const [response, user] = await Promise.all([
          client.request<Backend.TeamMemberView>(`/team/members/${memberId}`, {
            method: "PATCH",
            organizationId,
            json: { role },
            signal
          }),
          currentUser(signal)
        ]);
        return teamMember(response.data, user.data.id);
      },
      async removeMember(organizationId, memberId, signal) {
        await client.request<void>(`/team/members/${memberId}`, {
          method: "DELETE",
          organizationId,
          signal
        });
      },
      async resendInvitation(organizationId, invitationId, signal) {
        const response = await client.request<InvitationDeliveryView>(
          `/team/invitations/${invitationId}/resend`,
          { method: "POST", organizationId, signal }
        );
        return {
          ...invitation(response.data),
          acceptance_token: response.data.acceptance_token
        };
      },
      async revokeInvitation(organizationId, invitationId, signal) {
        await client.request<void>(`/team/invitations/${invitationId}`, {
          method: "DELETE",
          organizationId,
          signal
        });
      }
    },
    billing: {
      async getOverview(organizationId, signal) {
        const [plans, subscription, invoices] = await Promise.all([
          client.request<Backend.PlanView[]>("/billing/plans", { signal }),
          client.request<Backend.SubscriptionView>("/billing/subscription", {
            organizationId,
            signal
          }),
          client.collection<Backend.InvoiceView>("/billing/invoices", {
            organizationId,
            query: { page: 1, page_size: 100 },
            signal
          })
        ]);
        const usageLabels = {
          members: "Members",
          customers: "Customers",
          products: "Products",
          orders: "Orders"
        } as const;
        const usage = Object.entries(subscription.data.usage).map(
          ([id, metric]) => ({
            id: id as keyof typeof usageLabels,
            label: usageLabels[id as keyof typeof usageLabels],
            used: metric.used,
            limit: metric.limit,
            unit: "records"
          })
        );
        return {
          organization_id: organizationId,
          subscription: {
            plan: subscription.data.plan as "free" | "pro" | "business",
            status: subscription.data.status,
            provider: subscription.data.provider,
            current_period_start: subscription.data.current_period_start,
            current_period_end: subscription.data.current_period_end,
            cancel_at_period_end: subscription.data.cancel_at_period_end
          },
          plans: plans.data,
          usage,
          invoices: invoices.data,
          demo_notice:
            subscription.data.provider === "demo"
              ? "Plan changes are simulated and never collect payment."
              : "Billing is managed by the configured payment provider.",
          can_manage_billing: true
        } satisfies BillingOverview;
      },
      async changePlan(organizationId, planId, signal) {
        const intent = await client.request<Backend.BillingIntentView>(
          "/billing/upgrade-intents",
          {
            method: "POST",
            organizationId,
            idempotent: true,
            json: { plan: planId },
            signal
          }
        );
        const overview = await this.getOverview(organizationId, signal);
        return {
          subscription: overview.subscription,
          feedback: intent.data.message,
          charged_amount_minor: 0
        };
      }
    },
    settings: {
      get: settingsSnapshot,
      async updateProfile(organizationId, input, signal) {
        await client.request<Backend.CurrentUserView>("/users/me", {
          method: "PATCH",
          json: input,
          signal
        });
        return settingsSnapshot(organizationId, signal);
      },
      async updateOrganization(organizationId, input, signal) {
        const { if_match, ...payload } = input;
        await client.request<Backend.CurrentOrganizationView>(
          "/organizations/current",
          {
            method: "PATCH",
            organizationId,
            ifMatch: if_match,
            json: payload,
            signal
          }
        );
        return settingsSnapshot(organizationId, signal);
      },
      async updatePreferences(organizationId, input, signal) {
        await client.request<Backend.PreferenceView>("/users/me/preferences", {
          method: "PATCH",
          json: input,
          signal
        });
        return settingsSnapshot(organizationId, signal);
      },
      async changePassword(_organizationId, input, signal) {
        await client.request<void>("/users/me/password", {
          method: "PATCH",
          json: input,
          signal
        });
      },
      async requestExport(organizationId, signal) {
        const created = await client.request<Backend.DataExportView>(
          "/organizations/current/data-exports",
          {
            method: "POST",
            organizationId,
            idempotent: true,
            json: { format: "json" },
            signal
          }
        );
        const completed = await pollUntil(
          async (pollSignal) =>
            (
              await client.request<Backend.DataExportView>(
                `/organizations/current/data-exports/${created.data.id}`,
                { organizationId, signal: pollSignal }
              )
            ).data,
          {
            signal,
            isComplete: (value) => value.status === "succeeded",
            isFailed: (value) =>
              value.status === "failed" || value.status === "expired"
          }
        );
        if (completed.status !== "succeeded") {
          throw clientProblem(
            "The data export did not complete.",
            "export_failed"
          );
        }
        const artifact = await client.download(
          `/organizations/current/data-exports/${completed.id}/download`,
          { organizationId, signal }
        );
        return {
          filename:
            artifact.filename ?? completed.filename ?? "workspace-export.json",
          mime_type: "application/json",
          content: await artifact.blob.text(),
          generated_at: completed.created_at
        };
      },
      async deleteOrganization(organizationId, confirmation, signal) {
        await client.request<unknown>("/organizations/current", {
          method: "DELETE",
          organizationId,
          json: { organization_name: confirmation },
          signal
        });
      }
    }
  };
}
