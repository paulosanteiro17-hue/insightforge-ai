import type { Metadata } from "next";
import Link from "next/link";
import { Check } from "lucide-react";
import { buttonStyles } from "@/components/ui/button";
import { plans } from "@/content/marketing";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Compare InsightForge AI plans for growing businesses."
};

export default function PricingPage() {
  return (
    <main id="main-content" className="bg-ink-50 px-5 py-20 sm:px-8 lg:py-28">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
            Pricing
          </p>
          <h1 className="text-ink-950 mt-4 text-5xl font-bold tracking-[-0.06em]">
            A plan for every stage of clarity.
          </h1>
          <p className="text-ink-600 mt-5 text-base leading-7">
            All portfolio demo billing is simulated and never creates a real
            charge.
          </p>
        </div>
        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {plans.map((plan) => (
            <article
              key={plan.name}
              className={`rounded-3xl border p-8 ${plan.featured ? "border-ink-950 bg-ink-950 text-white" : "border-ink-200 text-ink-950 bg-white"}`}
            >
              <h2 className="text-xl font-bold">{plan.name}</h2>
              <p className="mt-5 text-4xl font-bold tracking-[-0.05em]">
                {plan.price}
                <span className="ml-1 text-sm font-medium opacity-60">
                  /month
                </span>
              </p>
              <p className="mt-4 min-h-14 text-sm leading-6 opacity-75">
                {plan.description}
              </p>
              <ul className="mt-7 grid gap-3 text-sm">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check
                      className="size-4 text-teal-500"
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
                Start with {plan.name}
              </Link>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
