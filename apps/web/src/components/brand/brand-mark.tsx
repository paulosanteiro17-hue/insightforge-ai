import Link from "next/link";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/cn";

export function BrandMark({
  href = "/",
  compact = false,
  inverse = false,
  className
}: {
  href?: string;
  compact?: boolean;
  inverse?: boolean;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn("inline-flex items-center gap-2.5 rounded-lg", className)}
      aria-label="InsightForge AI home"
    >
      <span className="relative grid size-9 place-items-center overflow-hidden rounded-xl bg-teal-500 text-white shadow-sm">
        <span className="bg-coral-500/80 absolute -right-2 -bottom-3 size-7 rounded-full" />
        <Sparkles
          className="relative size-[18px]"
          strokeWidth={2.2}
          aria-hidden="true"
        />
      </span>
      {compact ? null : (
        <span
          className={cn(
            "text-[1.05rem] font-bold tracking-[-0.035em]",
            inverse ? "text-white" : "text-ink-950"
          )}
        >
          InsightForge{" "}
          <span className={inverse ? "text-teal-400" : "text-teal-600"}>
            AI
          </span>
        </span>
      )}
    </Link>
  );
}
