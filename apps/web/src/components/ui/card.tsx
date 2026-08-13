import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "border-ink-200/80 rounded-2xl border bg-white shadow-[var(--shadow-panel)]",
        className
      )}
      {...props}
    />
  );
}
