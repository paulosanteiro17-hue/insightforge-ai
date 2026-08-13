"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy } from "lucide-react";
import { useState, type FormEvent } from "react";
import { getApiErrorMessage } from "@/components/administration/admin-utils";
import { RemoveMemberDialog } from "@/components/administration/remove-member-dialog";
import {
  InviteTeamMemberPanel,
  TeamInvitationsSection
} from "@/components/administration/team-invitations";
import { TeamMembersSection } from "@/components/administration/team-members";
import { ListSkeleton } from "@/components/data/list-states";
import { PageHeader } from "@/components/data/page-header";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/states";
import type {
  InvitationRole,
  OrganizationSummary,
  TeamMember,
  TeamMemberRole
} from "@/lib/api/contracts";
import { cn } from "@/lib/cn";
import { insightForgeApi } from "@runtime-api";

type Feedback = { tone: "success" | "error"; message: string };

const roleLabels: Record<TeamMemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member"
};

export function TeamPage({
  organization
}: {
  organization: OrganizationSummary;
}) {
  const queryClient = useQueryClient();
  const queryKey = ["organization", organization.id, "team"];
  const teamQuery = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      insightForgeApi.team.getOverview(organization.id, signal)
  });
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InvitationRole>("member");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [removeTarget, setRemoveTarget] = useState<TeamMember | null>(null);
  const [busyInvitationId, setBusyInvitationId] = useState<string | null>(null);
  const [deliveryLink, setDeliveryLink] = useState<{
    email: string;
    url: string;
  } | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);

  function rememberDeliveryLink(invitation: {
    email: string;
    acceptance_token?: string;
  }) {
    if (!invitation.acceptance_token) return;
    setDeliveryLink({
      email: invitation.email,
      url: `${window.location.origin}/accept-invitation/${encodeURIComponent(invitation.acceptance_token)}`
    });
    setLinkCopied(false);
  }

  async function refreshTeam() {
    await queryClient.invalidateQueries({ queryKey });
  }

  const inviteMutation = useMutation({
    mutationFn: () =>
      insightForgeApi.team.invite(organization.id, {
        email: inviteEmail,
        role: inviteRole
      }),
    onSuccess: async (invitation) => {
      setInviteEmail("");
      rememberDeliveryLink(invitation);
      setFeedback({
        tone: "success",
        message: "Invitation created. Copy the one-time link below."
      });
      await refreshTeam();
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(error, "The invitation could not be sent.")
      })
  });
  const roleMutation = useMutation({
    mutationFn: ({
      memberId,
      role
    }: {
      memberId: string;
      role: TeamMemberRole;
    }) => insightForgeApi.team.changeRole(organization.id, memberId, role),
    onSuccess: async (member) => {
      const article = member.role === "admin" ? "an" : "a";
      setFeedback({
        tone: "success",
        message: `${member.display_name} is now ${article} ${roleLabels[member.role].toLowerCase()}.`
      });
      await refreshTeam();
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The member role could not be changed."
        )
      })
  });
  const removeMutation = useMutation({
    mutationFn: (memberId: string) =>
      insightForgeApi.team.removeMember(organization.id, memberId),
    onSuccess: async () => {
      const removedName = removeTarget?.display_name ?? "The member";
      setRemoveTarget(null);
      setFeedback({
        tone: "success",
        message: `${removedName} was removed from the workspace.`
      });
      await refreshTeam();
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(error, "The member could not be removed.")
      })
  });
  const resendMutation = useMutation({
    mutationFn: (invitationId: string) =>
      insightForgeApi.team.resendInvitation(organization.id, invitationId),
    onSuccess: (invitation) => {
      rememberDeliveryLink(invitation);
      setFeedback({
        tone: "success",
        message: "Invitation renewed. Copy the new one-time link below."
      });
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The invitation could not be resent."
        )
      }),
    onSettled: () => setBusyInvitationId(null)
  });
  const revokeMutation = useMutation({
    mutationFn: ({ invitationId }: { invitationId: string; email: string }) =>
      insightForgeApi.team.revokeInvitation(organization.id, invitationId),
    onSuccess: async (_result, variables) => {
      setFeedback({
        tone: "success",
        message: `The invitation for ${variables.email} was revoked.`
      });
      await refreshTeam();
    },
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: getApiErrorMessage(
          error,
          "The invitation could not be revoked."
        )
      }),
    onSettled: () => setBusyInvitationId(null)
  });

  function submitInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    inviteMutation.mutate();
  }

  if (teamQuery.isPending) return <ListSkeleton />;
  if (teamQuery.isError) {
    return (
      <ErrorState
        title="Team access could not be loaded"
        message={getApiErrorMessage(
          teamQuery.error,
          "Team membership is temporarily unavailable."
        )}
        onRetry={() => void teamQuery.refetch()}
      />
    );
  }

  const team = teamQuery.data;
  const isOwner = team.current_user_role === "owner";

  return (
    <div>
      <PageHeader
        eyebrow="Access management"
        title="Team"
        description={`Manage roles and workspace access for ${organization.name}. Every action is enforced by tenant-scoped API permissions.`}
        badge={`${roleLabels[team.current_user_role]} access`}
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
      {deliveryLink ? (
        <div className="mb-5 rounded-2xl border border-teal-200 bg-teal-50 p-4">
          <p className="text-ink-950 text-sm font-bold">
            One-time link for {deliveryLink.email}
          </p>
          <p className="text-ink-600 mt-1 text-xs leading-5">
            This token is shown only in this response. Copy it now and share it
            securely.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input
              readOnly
              value={deliveryLink.url}
              aria-label="One-time invitation link"
              className="border-ink-200 h-10 min-w-0 flex-1 rounded-lg border bg-white px-3 text-xs"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={async () => {
                await navigator.clipboard.writeText(deliveryLink.url);
                setLinkCopied(true);
              }}
            >
              {linkCopied ? (
                <Check className="size-4" aria-hidden="true" />
              ) : (
                <Copy className="size-4" aria-hidden="true" />
              )}
              {linkCopied ? "Copied" : "Copy link"}
            </Button>
          </div>
        </div>
      ) : null}
      <InviteTeamMemberPanel
        email={inviteEmail}
        role={inviteRole}
        canManage={team.can_manage_members}
        isOwner={isOwner}
        pending={inviteMutation.isPending}
        demoPolicy={team.demo_policy}
        onEmailChange={setInviteEmail}
        onRoleChange={setInviteRole}
        onSubmit={submitInvitation}
      />
      <TeamMembersSection
        members={team.members}
        currentRole={team.current_user_role}
        rolePending={roleMutation.isPending}
        onRoleChange={(memberId, role) => {
          setFeedback(null);
          roleMutation.mutate({ memberId, role });
        }}
        onRemove={setRemoveTarget}
      />
      <TeamInvitationsSection
        invitations={team.invitations}
        canManage={team.can_manage_members}
        busyInvitationId={busyInvitationId}
        onResend={(invitation) => {
          setFeedback(null);
          setBusyInvitationId(invitation.id);
          resendMutation.mutate(invitation.id);
        }}
        onRevoke={(invitation) => {
          setFeedback(null);
          setBusyInvitationId(invitation.id);
          revokeMutation.mutate({
            invitationId: invitation.id,
            email: invitation.email
          });
        }}
      />
      {removeTarget ? (
        <RemoveMemberDialog
          member={removeTarget}
          pending={removeMutation.isPending}
          onCancel={() => setRemoveTarget(null)}
          onConfirm={() => removeMutation.mutate(removeTarget.id)}
        />
      ) : null}
    </div>
  );
}
