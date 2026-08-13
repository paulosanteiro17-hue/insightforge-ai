"use client";

import { Crown, ShieldCheck, UserMinus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import type { TeamMember, TeamMemberRole } from "@/lib/api/contracts";
import { formatLongDate } from "@/lib/format";

const roleLabels: Record<TeamMemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member"
};

export function TeamMembersSection({
  members,
  currentRole,
  rolePending,
  onRoleChange,
  onRemove
}: {
  members: TeamMember[];
  currentRole: TeamMemberRole;
  rolePending: boolean;
  onRoleChange: (memberId: string, role: TeamMemberRole) => void;
  onRemove: (member: TeamMember) => void;
}) {
  return (
    <section aria-labelledby="members-heading" className="mb-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 id="members-heading" className="text-ink-950 text-lg font-bold">
            Members
          </h2>
          <p className="text-ink-500 mt-1 text-xs">
            {members.length} active{" "}
            {members.length === 1 ? "member" : "members"}
          </p>
        </div>
        <Badge>
          <ShieldCheck className="size-3.5" aria-hidden="true" /> Final-owner
          protection
        </Badge>
      </div>
      {members.length ? (
        <MembersTable
          members={members}
          currentRole={currentRole}
          rolePending={rolePending}
          onRoleChange={onRoleChange}
          onRemove={onRemove}
        />
      ) : (
        <EmptyState
          title="No team members"
          message="The organization owner will appear here once access is restored."
        />
      )}
    </section>
  );
}

function MembersTable({
  members,
  currentRole,
  rolePending,
  onRoleChange,
  onRemove
}: {
  members: TeamMember[];
  currentRole: TeamMemberRole;
  rolePending: boolean;
  onRoleChange: (memberId: string, role: TeamMemberRole) => void;
  onRemove: (member: TeamMember) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Workspace members and roles</caption>
          <thead className="bg-ink-50/80 text-ink-500 text-[10px] font-bold tracking-[0.11em] uppercase">
            <tr>
              <th className="px-5 py-3.5">Member</th>
              <th className="px-5 py-3.5">Joined</th>
              <th className="px-5 py-3.5">Role</th>
              <th className="px-5 py-3.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-ink-100 divide-y">
            {members.map((member) => (
              <tr key={member.id}>
                <td className="px-5 py-4">
                  <MemberIdentity member={member} />
                </td>
                <td className="text-ink-500 px-5 py-4 text-xs">
                  {formatLongDate(member.joined_at)}
                </td>
                <td className="px-5 py-4">
                  <RoleControl
                    member={member}
                    currentRole={currentRole}
                    pending={rolePending}
                    onChange={onRoleChange}
                  />
                </td>
                <td className="px-5 py-4 text-right">
                  <RemoveControl
                    member={member}
                    currentRole={currentRole}
                    onRemove={onRemove}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-ink-100 divide-y md:hidden">
        {members.map((member) => (
          <article key={member.id} className="p-4">
            <MemberIdentity member={member} />
            <div className="mt-4 flex items-end justify-between gap-3">
              <RoleControl
                member={member}
                currentRole={currentRole}
                pending={rolePending}
                onChange={onRoleChange}
              />
              <RemoveControl
                member={member}
                currentRole={currentRole}
                onRemove={onRemove}
              />
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}

function MemberIdentity({ member }: { member: TeamMember }) {
  const initials = member.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <div className="flex items-center gap-3">
      <span className="bg-ink-950 grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold text-white">
        {initials}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-ink-950 font-semibold">{member.display_name}</p>
          {member.is_current_user ? <Badge>You</Badge> : null}
          {member.role === "owner" ? (
            <Badge className="border-amber-300 bg-amber-50 text-amber-800">
              <Crown className="size-3" aria-hidden="true" /> Final owner
            </Badge>
          ) : null}
        </div>
        <p className="text-ink-500 mt-0.5 truncate text-xs">{member.email}</p>
      </div>
    </div>
  );
}

function RoleControl({
  member,
  currentRole,
  pending,
  onChange
}: {
  member: TeamMember;
  currentRole: TeamMemberRole;
  pending: boolean;
  onChange: (memberId: string, role: TeamMemberRole) => void;
}) {
  const editable = currentRole === "owner" && member.role !== "owner";
  if (!editable) {
    return (
      <span className="text-ink-700 inline-flex min-h-9 items-center text-sm font-semibold">
        {roleLabels[member.role]}
      </span>
    );
  }
  return (
    <label className="block min-w-32">
      <span className="sr-only">Role for {member.display_name}</span>
      <select
        aria-label={`Role for ${member.display_name}`}
        value={member.role}
        disabled={pending}
        onChange={(event) =>
          onChange(member.id, event.target.value as TeamMemberRole)
        }
        className="border-ink-200 text-ink-800 h-9 w-full rounded-lg border bg-white px-2.5 text-xs font-semibold"
      >
        <option value="admin">Admin</option>
        <option value="member">Member</option>
      </select>
    </label>
  );
}

function RemoveControl({
  member,
  currentRole,
  onRemove
}: {
  member: TeamMember;
  currentRole: TeamMemberRole;
  onRemove: (member: TeamMember) => void;
}) {
  const allowed =
    member.role !== "owner" &&
    !member.is_current_user &&
    (currentRole === "owner" ||
      (currentRole === "admin" && member.role === "member"));
  return (
    <Button
      size="sm"
      variant="ghost"
      disabled={!allowed}
      title={
        member.role === "owner"
          ? "The final owner cannot be removed"
          : !allowed
            ? "You do not have permission to remove this member"
            : undefined
      }
      onClick={() => onRemove(member)}
    >
      <UserMinus className="size-3.5" aria-hidden="true" /> Remove
    </Button>
  );
}
