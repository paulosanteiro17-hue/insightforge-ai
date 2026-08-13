import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Badge({
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "border-ink-200 text-ink-600 inline-flex items-center gap-1.5 rounded-full border bg-white px-2.5 py-1 text-xs font-semibold",
        className
      )}
      {...props}
    />
  );
}
