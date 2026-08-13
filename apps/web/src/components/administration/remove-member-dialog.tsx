"use client";

import { LoaderCircle, Trash2, UserMinus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { TeamMember } from "@/lib/api/contracts";

export function RemoveMemberDialog({
  member,
  pending,
  onCancel,
  onConfirm
}: {
  member: TeamMember;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="bg-ink-950/55 fixed inset-0 z-[130] grid place-items-center p-4 backdrop-blur-sm"
      role="presentation"
    >
      <button
        type="button"
        className="absolute inset-0"
        aria-label="Cancel member removal"
        onClick={onCancel}
      />
      <Card
        className="relative w-full max-w-md p-6 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-member-title"
      >
        <button
          type="button"
          className="text-ink-500 hover:bg-ink-100 absolute top-3 right-3 grid size-9 place-items-center rounded-lg"
          aria-label="Cancel member removal"
          onClick={onCancel}
        >
          <X className="size-4" aria-hidden="true" />
        </button>
        <span className="bg-coral-50 text-coral-700 grid size-11 place-items-center rounded-xl">
          <UserMinus className="size-5" aria-hidden="true" />
        </span>
        <h2
          id="remove-member-title"
          className="text-ink-950 mt-5 text-xl font-bold"
        >
          Remove {member.display_name}?
        </h2>
        <p className="text-ink-600 mt-2 text-sm leading-6">
          Their access to this workspace will end immediately. Existing audit
          records remain tenant-scoped.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" disabled={pending} onClick={onConfirm}>
            {pending ? (
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
            ) : (
              <Trash2 className="size-4" aria-hidden="true" />
            )}
            Remove member
          </Button>
        </div>
      </Card>
    </div>
  );
}
