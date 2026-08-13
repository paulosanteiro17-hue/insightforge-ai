import { AlertTriangle, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { WeeklySummary } from "@/lib/api/contracts";

export function WeeklySummaryCard({
  summary,
  onRegenerate,
  isRegenerating = false
}: {
  summary: WeeklySummary;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
}) {
  return (
    <Card
      id="ai-summary"
      className="border-ink-800! bg-ink-950! scroll-mt-28 overflow-hidden text-white"
    >
      <div className="grid lg:grid-cols-[0.75fr_1.25fr]">
        <div className="relative overflow-hidden border-b border-white/10 p-6 sm:p-8 lg:border-r lg:border-b-0">
          <div className="fine-noise pointer-events-none absolute inset-0 opacity-20" />
          <div className="relative">
            <span className="grid size-11 place-items-center rounded-2xl bg-teal-400/12 text-teal-300">
              <Sparkles className="size-5" aria-hidden="true" />
            </span>
            <p className="mt-7 text-xs font-bold tracking-[0.14em] text-teal-300 uppercase">
              {summary.eyebrow ?? "Weekly summary"} ·{" "}
              {summary.week_start ?? "Current week"}
              {summary.week_end ? ` to ${summary.week_end}` : ""}
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-[-0.04em]">
              {summary.headline ?? summary.title}
            </h2>
            <div className="text-ink-300 mt-6 flex items-center gap-2 text-[10px]">
              <ShieldCheck
                className="size-3.5 text-teal-400"
                aria-hidden="true"
              />{" "}
              Grounded in calculated metrics · {summary.provider} ·{" "}
              {summary.generation_mode} mode
            </div>
          </div>
        </div>
        <div className="p-6 sm:p-8">
          <p className="text-ink-200 text-sm leading-7">
            {summary.overview ?? summary.body}
          </p>
          <ul className="mt-7 grid gap-3 sm:grid-cols-2">
            {summary.highlights.map((item) => (
              <li
                key={typeof item === "string" ? item : item.label}
                className="rounded-2xl border border-teal-400/20 bg-teal-400/10 p-4 text-sm leading-6 text-teal-100"
              >
                {typeof item === "string"
                  ? item
                  : `${item.label}: ${item.value}`}
              </li>
            ))}
          </ul>
          {summary.watch_items?.length ? (
            <div className="border-coral-400/20 bg-coral-400/10 mt-5 rounded-2xl border p-4">
              <p className="text-coral-100 flex items-center gap-2 text-xs font-bold">
                <AlertTriangle className="size-4" aria-hidden="true" /> Watch
                items
              </p>
              <ul className="text-coral-100/90 mt-2 space-y-1 text-xs leading-5">
                {summary.watch_items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-semibold text-teal-300">
              {summary.source_revision
                ? `Source revision ${summary.source_revision}`
                : "Generated from the current analytics snapshot"}
            </p>
            {onRegenerate ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={isRegenerating}
                onClick={onRegenerate}
                className="border-white/30! bg-transparent! text-white! hover:bg-white/10!"
              >
                <RefreshCw
                  className={
                    isRegenerating ? "size-3.5 animate-spin" : "size-3.5"
                  }
                  aria-hidden="true"
                />
                {isRegenerating ? "Regenerating" : "Regenerate"}
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </Card>
  );
}
