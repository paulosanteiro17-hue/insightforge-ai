import { ArrowUpRight, Sparkles } from "lucide-react";

const chartHeights = [38, 46, 42, 58, 51, 67, 73, 69, 84, 92, 88, 100];

export function DashboardPreview({ expanded = false }: { expanded?: boolean }) {
  return (
    <div className="overflow-hidden rounded-[1.4rem] border border-white/15 bg-white shadow-[0_35px_90px_-42px_rgba(7,17,31,0.65)]">
      <div className="border-ink-100 flex items-center justify-between border-b px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <span className="bg-coral-500 size-2.5 rounded-full" />
          <span className="size-2.5 rounded-full bg-[#f2c14e]" />
          <span className="size-2.5 rounded-full bg-teal-500" />
        </div>
        <div className="bg-ink-50 text-ink-500 rounded-md px-3 py-1 text-[10px] font-semibold">
          Northstar Commerce · Last 30 days
        </div>
      </div>
      <div className="bg-ink-50/70 grid grid-cols-[44px_1fr]">
        <div className="border-ink-100 bg-ink-950 flex flex-col items-center gap-3 border-r py-5">
          <span className="grid size-6 place-items-center rounded-lg bg-teal-500 text-[9px] font-bold text-white">
            IF
          </span>
          {[0, 1, 2, 3, 4].map((item) => (
            <span
              key={item}
              className={`h-1.5 rounded-full ${item === 0 ? "w-5 bg-teal-400" : "bg-ink-600 w-3"}`}
            />
          ))}
        </div>
        <div className="min-w-0 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-ink-400 text-[9px] font-bold tracking-[0.14em] uppercase">
                Overview
              </p>
              <p className="text-ink-950 mt-1 text-sm font-bold tracking-tight">
                Business momentum
              </p>
            </div>
            <span className="border-ink-200 text-ink-600 rounded-lg border bg-white px-2 py-1 text-[9px] font-semibold">
              Export
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["Revenue", "$81.8k", "+18.4%"],
              ["Orders", "304", "+5.4%"],
              ["Customers", "142", "+8.1%"],
              ["MRR", "$18.6k", "+7.1%"]
            ].map(([label, value, change]) => (
              <div
                key={label}
                className="border-ink-100 rounded-xl border bg-white p-2.5"
              >
                <p className="text-ink-500 text-[8px] font-medium">{label}</p>
                <div className="mt-1 flex items-end justify-between gap-1">
                  <p className="text-ink-950 text-[13px] font-bold tracking-tight">
                    {value}
                  </p>
                  <p className="text-[8px] font-semibold text-teal-700">
                    {change}
                  </p>
                </div>
              </div>
            ))}
          </div>
          <div
            className={`mt-3 grid gap-3 ${expanded ? "sm:grid-cols-[1.5fr_1fr]" : "grid-cols-1"}`}
          >
            <div className="border-ink-100 rounded-xl border bg-white p-3">
              <div className="flex items-center justify-between">
                <p className="text-ink-700 text-[9px] font-semibold">
                  Revenue trend
                </p>
                <p className="text-ink-400 text-[8px]">USD</p>
              </div>
              <div className="border-ink-100 mt-3 flex h-24 items-end gap-1.5 border-b">
                {chartHeights.map((height, index) => (
                  <span
                    key={index}
                    className="min-w-1 flex-1 rounded-t-sm bg-teal-500/75"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
              <div className="text-ink-400 mt-2 flex justify-between text-[7px]">
                <span>Jul 12</span>
                <span>Jul 26</span>
                <span>Aug 10</span>
              </div>
            </div>
            {expanded ? (
              <div className="bg-ink-950 rounded-xl p-3 text-white">
                <span className="grid size-6 place-items-center rounded-lg bg-teal-500/20 text-teal-300">
                  <Sparkles className="size-3" aria-hidden="true" />
                </span>
                <p className="mt-3 text-[10px] font-semibold">Weekly signal</p>
                <p className="text-ink-300 mt-1 text-[8px] leading-4">
                  Atlas Suite and advisory services drove revenue above the
                  four-week baseline.
                </p>
                <p className="mt-3 inline-flex items-center text-[8px] font-semibold text-teal-300">
                  View evidence{" "}
                  <ArrowUpRight className="ml-1 size-2.5" aria-hidden="true" />
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
