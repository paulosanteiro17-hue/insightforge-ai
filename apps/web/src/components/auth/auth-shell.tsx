import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowLeft, CheckCircle2, Sparkles } from "lucide-react";
import { BrandMark } from "@/components/brand/brand-mark";

export function AuthShell({
  eyebrow,
  title,
  description,
  children
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main
      id="main-content"
      className="bg-ink-50 min-h-screen lg:grid lg:grid-cols-[minmax(0,0.9fr)_minmax(600px,1.1fr)]"
    >
      <aside className="bg-ink-950 relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col">
        <div className="fine-noise pointer-events-none absolute inset-0 opacity-20" />
        <div className="relative">
          <BrandMark inverse />
        </div>
        <div className="relative my-auto max-w-xl py-16">
          <span className="grid size-12 place-items-center rounded-2xl bg-teal-400/12 text-teal-300">
            <Sparkles className="size-5" aria-hidden="true" />
          </span>
          <blockquote className="mt-7 text-3xl leading-[1.18] font-semibold tracking-[-0.045em]">
            “The clearest dashboards do more than report movement—they explain
            what deserves attention next.”
          </blockquote>
          <div className="text-ink-300 mt-10 grid gap-4 text-sm">
            {[
              "12 months of realistic demo analytics",
              "Grounded insight with a deterministic fallback",
              "Organization-scoped access from UI to database"
            ].map((item) => (
              <div key={item} className="flex items-center gap-3">
                <CheckCircle2
                  className="size-4 text-teal-400"
                  aria-hidden="true"
                />
                {item}
              </div>
            ))}
          </div>
        </div>
        <p className="text-ink-500 relative text-xs leading-5">
          Portfolio demo · No real payment is required
        </p>
      </aside>

      <section className="flex min-h-screen flex-col px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between lg:hidden">
          <BrandMark />
          <Link
            href="/"
            className="text-ink-600 hover:text-ink-950 inline-flex items-center gap-1.5 rounded-lg text-sm font-semibold"
          >
            <ArrowLeft className="size-4" aria-hidden="true" /> Home
          </Link>
        </div>
        <div className="hidden justify-end lg:flex">
          <Link
            href="/"
            className="text-ink-600 hover:text-ink-950 inline-flex items-center gap-1.5 rounded-lg text-sm font-semibold"
          >
            <ArrowLeft className="size-4" aria-hidden="true" /> Back to home
          </Link>
        </div>
        <div className="my-auto w-full max-w-[31rem] self-center py-12">
          <p className="text-sm font-bold tracking-[0.15em] text-teal-700 uppercase">
            {eyebrow}
          </p>
          <h1 className="text-ink-950 mt-3 text-4xl font-bold tracking-[-0.055em] sm:text-[2.8rem]">
            {title}
          </h1>
          <p className="text-ink-600 mt-3 text-sm leading-6">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </main>
  );
}
