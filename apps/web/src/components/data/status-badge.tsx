import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";

const toneByStatus: Record<string, string> = {
  active: "border-teal-500/20 bg-teal-50 text-teal-700",
  ready: "border-teal-500/20 bg-teal-50 text-teal-700",
  completed: "border-teal-500/20 bg-teal-50 text-teal-700",
  paid: "border-sky-500/20 bg-sky-50 text-sky-700",
  processing: "border-indigo-500/20 bg-indigo-50 text-indigo-700",
  pending: "border-amber-500/20 bg-amber-50 text-amber-700",
  generating: "border-indigo-500/20 bg-indigo-50 text-indigo-700",
  validating: "border-indigo-500/20 bg-indigo-50 text-indigo-700",
  importing: "border-indigo-500/20 bg-indigo-50 text-indigo-700",
  uploaded: "border-sky-500/20 bg-sky-50 text-sky-700",
  validation_failed: "border-coral-500/20 bg-coral-50 text-coral-700",
  failed: "border-coral-500/20 bg-coral-50 text-coral-700",
  import_failed: "border-coral-500/20 bg-coral-50 text-coral-700",
  at_risk: "border-amber-500/20 bg-amber-50 text-amber-700",
  low_stock: "border-amber-500/20 bg-amber-50 text-amber-700",
  cancelled: "border-ink-300 bg-ink-100 text-ink-600",
  inactive: "border-ink-300 bg-ink-100 text-ink-600",
  archived: "border-ink-300 bg-ink-100 text-ink-600",
  expired: "border-ink-300 bg-ink-100 text-ink-600",
  revoked: "border-ink-300 bg-ink-100 text-ink-600",
  void: "border-ink-300 bg-ink-100 text-ink-600",
  refunded: "border-coral-500/20 bg-coral-50 text-coral-700"
};

function statusLabel(status: string): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function StatusBadge({
  status,
  className
}: {
  status: string;
  className?: string;
}) {
  return (
    <Badge className={cn(toneByStatus[status] ?? "", className)}>
      <span
        className="size-1.5 rounded-full bg-current opacity-70"
        aria-hidden="true"
      />
      {statusLabel(status)}
    </Badge>
  );
}
