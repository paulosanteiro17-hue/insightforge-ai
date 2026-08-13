"use client";

import { LoaderCircle, MailPlus, RefreshCw, X } from "lucide-react";
import type { FormEvent } from "react";
import { fieldClassName } from "@/components/administration/admin-utils";
import { StatusBadge } from "@/components/data/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import type {
  InvitationRole,
  TeamInvitation,
  TeamMemberRole
} from "@/lib/api/contracts";
import { formatLongDate } from "@/lib/format";

const roleLabels: Record<TeamMemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member"
};

export function InviteTeamMemberPanel({
  email,
  role,
  canManage,
  isOwner,
  pending,
  demoPolicy,
  onEmailChange,
  onRoleChange,
  onSubmit
}: {
  email: string;
  role: InvitationRole;
  canManage: boolean;
  isOwner: boolean;
  pending: boolean;
  demoPolicy: string;
  onEmailChange: (email: string) => void;
  onRoleChange: (role: InvitationRole) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="mb-5 overflow-hidden">
      <div className="grid lg:grid-cols-[0.8fr_1.2fr]">
        <div className="bg-ink-950 p-5 text-white sm:p-6">
          <span className="bg-coral-500/15 text-coral-300 grid size-10 place-items-center rounded-xl">
            <MailPlus className="size-5" aria-hidden="true" />
          </span>
          <h2 className="mt-5 text-xl font-bold">Invite a teammate</h2>
          <p className="text-ink-300 mt-2 text-sm leading-6">{demoPolicy}</p>
          <Badge className="mt-5 border-amber-300/20 bg-amber-300/10 text-amber-200">
            Manual delivery
          </Badge>
        </div>
        <form onSubmit={onSubmit} className="p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-[1fr_10rem]">
            <label>
              <span className="text-ink-700 text-xs font-semibold">
                Work email
              </span>
              <input
                required
                type="email"
                value={email}
                onChange={(event) => onEmailChange(event.target.value)}
                className={fieldClassName}
                placeholder="teammate@company.com"
                autoComplete="email"
                disabled={!canManage}
              />
            </label>
            <label>
              <span className="text-ink-700 text-xs font-semibold">Role</span>
              <select
                value={role}
                onChange={(event) =>
                  onRoleChange(event.target.value as InvitationRole)
                }
                className={fieldClassName}
                disabled={!canManage}
              >
                <option value="member">Member</option>
                {isOwner ? <option value="admin">Admin</option> : null}
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-ink-500 max-w-md text-xs leading-5">
              A one-time acceptance link will be shown after creation. Copy it
              and share it through a trusted channel.
            </p>
            <Button type="submit" disabled={!canManage || pending}>
              {pending ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <MailPlus className="size-4" aria-hidden="true" />
              )}
              Create invitation link
            </Button>
          </div>
        </form>
      </div>
    </Card>
  );
}

export function TeamInvitationsSection({
  invitations,
  canManage,
  busyInvitationId,
  onResend,
  onRevoke
}: {
  invitations: TeamInvitation[];
  canManage: boolean;
  busyInvitationId: string | null;
  onResend: (invitation: TeamInvitation) => void;
  onRevoke: (invitation: TeamInvitation) => void;
}) {
  return (
    <section aria-labelledby="invitations-heading">
      <div className="mb-3">
        <h2 id="invitations-heading" className="text-ink-950 text-lg font-bold">
          Invitations
        </h2>
        <p className="text-ink-500 mt-1 text-xs">
          Pending, expired, accepted, and revoked invitation records are kept
          visible without exposing their one-time tokens.
        </p>
      </div>
      {invitations.length ? (
        <Card className="divide-ink-100 divide-y overflow-hidden">
          {invitations.map((invitation) => (
            <InvitationRow
              key={invitation.id}
              invitation={invitation}
              canManage={canManage}
              busy={busyInvitationId === invitation.id}
              onResend={() => onResend(invitation)}
              onRevoke={() => onRevoke(invitation)}
            />
          ))}
        </Card>
      ) : (
        <EmptyState
          title="No invitation history"
          message="Pending and recently revoked invitations will appear here."
        />
      )}
    </section>
  );
}

function InvitationRow({
  invitation,
  canManage,
  busy,
  onResend,
  onRevoke
}: {
  invitation: TeamInvitation;
  canManage: boolean;
  busy: boolean;
  onResend: () => void;
  onRevoke: () => void;
}) {
  const active = invitation.status !== "revoked";
  return (
    <article className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-ink-950 truncate text-sm font-semibold">
            {invitation.email}
          </p>
          <StatusBadge status={invitation.status} />
          <Badge>{roleLabels[invitation.role]}</Badge>
        </div>
        <p className="text-ink-500 mt-1 text-xs">
          Created {formatLongDate(invitation.created_at)} · Expires{" "}
          {formatLongDate(invitation.expires_at)}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={!canManage || !active || busy}
          onClick={onResend}
        >
          {busy ? (
            <LoaderCircle
              className="size-3.5 animate-spin"
              aria-hidden="true"
            />
          ) : (
            <RefreshCw className="size-3.5" aria-hidden="true" />
          )}
          Resend
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={!canManage || !active || busy}
          onClick={onRevoke}
        >
          <X className="size-3.5" aria-hidden="true" /> Revoke
        </Button>
      </div>
    </article>
  );
}
