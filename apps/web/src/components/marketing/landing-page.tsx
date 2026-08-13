import Link from "next/link";
import {
  ArrowRight,
  Check,
  CircleCheck,
  DatabaseZap,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  TrendingUp
} from "lucide-react";
import { DashboardPreview } from "@/components/marketing/dashboard-preview";
import { Badge } from "@/components/ui/badge";
import { buttonStyles } from "@/components/ui/button";
import {
  benefitItems,
  featureItems,
  plans,
  workflowSteps
} from "@/content/marketing";

export function LandingPage() {
  return (
    <main id="main-content" className="overflow-hidden bg-white">
      <section className="border-ink-100 bg-ink-50 relative border-b">
        <div className="marketing-grid pointer-events-none absolute inset-0" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 pt-20 pb-16 sm:px-8 sm:pt-24 lg:grid-cols-[0.92fr_1.08fr] lg:px-10 lg:pt-28 lg:pb-24">
          <div>
            <Badge className="border-teal-500/20 bg-teal-50 text-teal-700">
              <span className="size-1.5 rounded-full bg-teal-500" />
              Analytics that explains the signal
            </Badge>
            <h1 className="text-ink-950 mt-7 max-w-3xl text-[clamp(3.2rem,8vw,6.5rem)] leading-[0.92] font-bold tracking-[-0.075em] lg:text-[5.6rem]">
              Turn business data into{" "}
              <span className="text-teal-600">decisions.</span>
            </h1>
            <p className="text-ink-600 mt-7 max-w-xl text-lg leading-8">
              Monitor performance, uncover trends, and get grounded AI guidance
              in one focused analytics workspace built for growing businesses.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/signup"
                className={buttonStyles({ size: "lg", className: "group" })}
              >
                Build your dashboard
                <ArrowRight
                  className="size-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Link>
              <Link
                href="/login"
                className={buttonStyles({ variant: "outline", size: "lg" })}
              >
                Explore the live demo
              </Link>
            </div>
            <div className="text-ink-500 mt-7 flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium">
              {[
                "No credit card",
                "Demo ready in seconds",
                "Works without an AI key"
              ].map((item) => (
                <span key={item} className="inline-flex items-center gap-1.5">
                  <CircleCheck
                    className="size-3.5 text-teal-600"
                    aria-hidden="true"
                  />
                  {item}
                </span>
              ))}
            </div>
          </div>
          <div className="relative lg:translate-x-8">
            <div className="bg-coral-100/70 absolute -top-10 -right-16 size-48 rounded-full blur-3xl" />
            <div className="absolute -bottom-16 -left-12 size-56 rounded-full bg-teal-100 blur-3xl" />
            <div className="bg-ink-950 relative rotate-[0.7deg] rounded-[1.8rem] p-2.5 shadow-[0_45px_100px_-45px_rgba(7,17,31,0.7)] sm:p-3.5">
              <DashboardPreview />
            </div>
            <div className="border-ink-200 absolute -bottom-5 -left-3 flex items-center gap-3 rounded-2xl border bg-white px-4 py-3 shadow-[var(--shadow-soft)] sm:-left-8">
              <span className="grid size-9 place-items-center rounded-xl bg-teal-50 text-teal-700">
                <TrendingUp className="size-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-ink-500 text-[10px] font-semibold">
                  Revenue signal
                </p>
                <p className="text-ink-950 text-sm font-bold">
                  18.4% above prior period
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="border-ink-200/70 text-ink-500 relative mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-10 gap-y-4 border-t px-5 py-6 text-xs font-semibold tracking-[0.06em] uppercase sm:px-8">
          <span className="text-ink-400">Designed for</span>
          <span>Commerce teams</span>
          <span>Service businesses</span>
          <span>Subscription products</span>
          <span>Growing operators</span>
        </div>
      </section>

      <section
        id="product"
        className="scroll-mt-24 px-5 py-24 sm:px-8 lg:py-32"
      >
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
              From data to direction
            </p>
            <h2 className="text-ink-950 mt-4 text-4xl leading-tight font-bold tracking-[-0.055em] sm:text-5xl">
              Less dashboard noise. More operating clarity.
            </h2>
          </div>
          <div className="mt-14 grid gap-5 md:grid-cols-3">
            {benefitItems.map((item, index) => {
              const Icon = item.icon;
              return (
                <article
                  key={item.title}
                  className="group border-ink-200 rounded-3xl border bg-white p-7 shadow-[var(--shadow-panel)]"
                >
                  <div className="flex items-start justify-between">
                    <span className="bg-ink-950 grid size-12 place-items-center rounded-2xl text-white transition-transform group-hover:-translate-y-0.5">
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="text-ink-400 font-mono text-xs">
                      0{index + 1}
                    </span>
                  </div>
                  <h3 className="text-ink-950 mt-8 text-xl font-bold tracking-[-0.03em]">
                    {item.title}
                  </h3>
                  <p className="text-ink-600 mt-3 text-sm leading-6">
                    {item.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section
        id="features"
        className="bg-ink-50 scroll-mt-24 px-5 py-24 sm:px-8 lg:py-32"
      >
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
            <div>
              <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
                Product system
              </p>
              <h2 className="text-ink-950 mt-4 text-4xl font-bold tracking-[-0.055em] sm:text-5xl">
                One source of analytical truth.
              </h2>
            </div>
            <p className="text-ink-600 max-w-2xl text-base leading-7 lg:justify-self-end">
              Dashboards, reports, AI insights, and questions all use the same
              controlled analytics engine, so your numbers stay consistent
              wherever the conversation begins.
            </p>
          </div>
          <div className="border-ink-200 bg-ink-200 mt-14 grid gap-px overflow-hidden rounded-3xl border md:grid-cols-2 lg:grid-cols-3">
            {featureItems.map((item) => {
              const Icon = item.icon;
              const iconStyle =
                item.accent === "teal"
                  ? "bg-teal-50 text-teal-700"
                  : item.accent === "coral"
                    ? "bg-coral-50 text-coral-700"
                    : "bg-ink-100 text-ink-700";
              return (
                <article key={item.title} className="bg-white p-7 sm:p-8">
                  <span
                    className={`grid size-11 place-items-center rounded-2xl ${iconStyle}`}
                  >
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="text-ink-950 mt-6 text-lg font-bold tracking-[-0.025em]">
                    {item.title}
                  </h3>
                  <p className="text-ink-600 mt-2 text-sm leading-6">
                    {item.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-5 py-24 sm:px-8 lg:py-32">
        <div className="bg-ink-950 mx-auto max-w-7xl rounded-[2rem] p-5 sm:p-8 lg:p-12">
          <div className="mb-9 grid gap-6 lg:grid-cols-[1fr_0.75fr] lg:items-end">
            <div>
              <p className="text-sm font-bold tracking-[0.16em] text-teal-400 uppercase">
                The operating view
              </p>
              <h2 className="mt-4 max-w-2xl text-4xl font-bold tracking-[-0.055em] text-white sm:text-5xl">
                Performance at a glance. Evidence one step deeper.
              </h2>
            </div>
            <p className="text-ink-300 max-w-xl text-sm leading-7 lg:justify-self-end">
              Every trend stays attached to its period, source revision,
              comparison, and supporting metric—without asking leaders to decode
              a wall of charts.
            </p>
          </div>
          <DashboardPreview expanded />
        </div>
      </section>

      <section className="bg-ink-950 relative overflow-hidden px-5 py-24 text-white sm:px-8 lg:py-32">
        <div className="fine-noise pointer-events-none absolute inset-0 opacity-30" />
        <div className="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <Badge className="border-teal-400/20! bg-teal-400/10! text-teal-300!">
              <Sparkles className="size-3" aria-hidden="true" /> Grounded
              business intelligence
            </Badge>
            <h2 className="mt-6 text-4xl leading-tight font-bold tracking-[-0.055em] sm:text-5xl">
              AI that starts with the numbers.
            </h2>
            <p className="text-ink-300 mt-5 max-w-xl text-base leading-7">
              InsightForge calculates the business statistics first, then asks
              an AI provider to explain only the bounded, sanitized result.
              Without a provider key, the same product remains useful through
              deterministic insight rules.
            </p>
            <div className="text-ink-200 mt-7 grid gap-3 text-sm">
              {(
                [
                  [
                    LockKeyhole,
                    "No model-authored SQL or database credentials"
                  ],
                  [
                    DatabaseZap,
                    "Aggregated context instead of raw customer records"
                  ],
                  [
                    ShieldCheck,
                    "Strict schemas, tenant boundaries, and safe fallback"
                  ]
                ] as const
              ).map(([Icon, text]) => (
                <div key={String(text)} className="flex items-center gap-3">
                  <span className="grid size-8 place-items-center rounded-lg bg-white/8 text-teal-300">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span>{text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-white/[0.055] p-6 backdrop-blur-sm sm:translate-y-8">
              <p className="text-xs font-semibold text-teal-300">
                Growth · High confidence
              </p>
              <h3 className="mt-4 text-xl font-bold">
                Revenue accelerated 18.4%
              </h3>
              <p className="text-ink-300 mt-3 text-sm leading-6">
                Atlas Suite and advisory services contributed 61% of the
                period-over-period gain.
              </p>
              <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="h-full w-[82%] rounded-full bg-teal-400" />
              </div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.055] p-6 backdrop-blur-sm">
              <p className="text-coral-300 text-xs font-semibold">
                Opportunity · Medium priority
              </p>
              <h3 className="mt-4 text-xl font-bold">
                Protect service bundle pricing
              </h3>
              <p className="text-ink-300 mt-3 text-sm leading-6">
                Acquisition grew while average order value slipped 2.4%,
                concentrated in discounted bundles.
              </p>
              <div className="text-ink-300 mt-6 flex items-center justify-between text-xs">
                <span>Supporting metric</span>
                <span className="font-mono text-white">AOV -2.4%</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="scroll-mt-24 px-5 py-24 sm:px-8 lg:py-32"
      >
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
              How it works
            </p>
            <h2 className="text-ink-950 mt-4 text-4xl font-bold tracking-[-0.055em] sm:text-5xl">
              A clear path from source to signal.
            </h2>
          </div>
          <div className="mt-14 grid gap-8 lg:grid-cols-3">
            {workflowSteps.map((step, index) => (
              <article
                key={step.number}
                className="border-ink-300 relative border-t pt-7"
              >
                <div className="absolute -top-2 left-0 size-4 rounded-full border-4 border-white bg-teal-500" />
                <p className="text-ink-400 font-mono text-xs font-semibold">
                  {step.number}
                </p>
                <h3 className="text-ink-950 mt-4 text-xl font-bold tracking-[-0.03em]">
                  {step.title}
                </h3>
                <p className="text-ink-600 mt-3 text-sm leading-6">
                  {step.description}
                </p>
                {index < workflowSteps.length - 1 ? (
                  <span className="sr-only">Then</span>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        id="pricing"
        className="bg-ink-50 scroll-mt-24 px-5 py-24 sm:px-8 lg:py-32"
      >
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
              Simple plans
            </p>
            <h2 className="text-ink-950 mt-4 text-4xl font-bold tracking-[-0.055em] sm:text-5xl">
              Start with clarity. Scale with confidence.
            </h2>
            <p className="text-ink-600 mt-4 text-sm leading-6">
              Portfolio evaluation always uses the no-charge demo billing
              adapter.
            </p>
          </div>
          <div className="mx-auto mt-14 grid max-w-5xl gap-5 lg:grid-cols-3">
            {plans.map((plan) => (
              <article
                key={plan.name}
                className={`relative rounded-3xl border p-7 ${plan.featured ? "border-ink-950 bg-ink-950 text-white shadow-[var(--shadow-soft)]" : "border-ink-200 text-ink-950 bg-white"}`}
              >
                {plan.featured ? (
                  <span className="absolute -top-3 left-6 rounded-full bg-teal-500 px-3 py-1 text-[10px] font-bold tracking-[0.12em] text-white uppercase">
                    Most popular
                  </span>
                ) : null}
                <h3 className="text-lg font-bold">{plan.name}</h3>
                <p className="mt-5 text-4xl font-bold tracking-[-0.05em]">
                  {plan.price}
                  <span
                    className={`ml-1 text-sm font-medium ${plan.featured ? "text-ink-300" : "text-ink-500"}`}
                  >
                    /month
                  </span>
                </p>
                <p
                  className={`mt-3 min-h-12 text-sm leading-6 ${plan.featured ? "text-ink-300" : "text-ink-600"}`}
                >
                  {plan.description}
                </p>
                <ul className="mt-7 grid gap-3">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-center gap-2.5 text-sm"
                    >
                      <Check
                        className={`size-4 ${plan.featured ? "text-teal-300" : "text-teal-600"}`}
                        aria-hidden="true"
                      />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/signup"
                  className={buttonStyles({
                    variant: plan.featured ? "secondary" : "outline",
                    className: "mt-8 w-full"
                  })}
                >
                  Choose {plan.name}
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-20 sm:px-8 lg:py-28">
        <div className="bg-coral-500 relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] px-6 py-14 text-center sm:px-12 sm:py-18">
          <div className="absolute -top-24 -left-20 size-64 rounded-full border-[36px] border-white/10" />
          <div className="border-ink-950/10 absolute -right-20 -bottom-28 size-72 rounded-full border-[42px]" />
          <div className="relative mx-auto max-w-3xl">
            <p className="text-ink-950 text-sm font-bold tracking-[0.15em] uppercase">
              Your next operating rhythm
            </p>
            <h2 className="text-ink-950 mt-4 text-4xl font-bold tracking-[-0.055em] sm:text-5xl">
              Give every business decision a clearer signal.
            </h2>
            <p className="text-ink-900/80 mx-auto mt-5 max-w-xl text-base leading-7">
              Open a realistic demo workspace now, or create an account and
              shape your own analytics foundation.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link href="/signup" className={buttonStyles({ size: "lg" })}>
                Get started <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link
                href="/login"
                className={buttonStyles({
                  variant: "outline",
                  size: "lg",
                  className: "border-white/40 bg-white/90"
                })}
              >
                Explore demo
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
