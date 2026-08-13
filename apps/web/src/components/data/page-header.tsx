import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  badge
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  badge?: string;
}) {
  return (
    <header className="mb-6 flex flex-col gap-5 lg:mb-8 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-ink-400 text-[10px] font-bold tracking-[0.15em] uppercase">
            {eyebrow}
          </p>
          {badge ? (
            <Badge className="border-teal-500/20 bg-teal-50 text-teal-700">
              {badge}
            </Badge>
          ) : null}
        </div>
        <h1 className="text-ink-950 mt-2.5 text-3xl font-bold tracking-[-0.055em] sm:text-4xl">
          {title}
        </h1>
        <p className="text-ink-600 mt-2 max-w-2xl text-sm leading-6">
          {description}
        </p>
      </div>
      {actions ? (
        <div className="flex flex-wrap items-center gap-3">{actions}</div>
      ) : null}
    </header>
  );
}
