import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <main id="main-content" className="bg-white px-5 py-20 sm:px-8 lg:py-28">
      <article className="mx-auto max-w-3xl">
        <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
          Privacy
        </p>
        <h1 className="text-ink-950 mt-4 text-5xl font-bold tracking-[-0.06em]">
          Privacy by product boundary.
        </h1>
        <p className="text-ink-600 mt-6 text-lg leading-8">
          InsightForge AI is a portfolio demonstration. Demo data is fictional,
          resettable, and isolated from non-demo organizations.
        </p>
        <div className="text-ink-600 mt-10 space-y-8 text-sm leading-7">
          <section>
            <h2 className="text-ink-950 text-xl font-bold">Data we process</h2>
            <p className="mt-2">
              Account details, organization settings, uploaded business records,
              and derived analytics are processed only to provide requested
              product features. Private upload objects expire under a documented
              retention policy.
            </p>
          </section>
          <section>
            <h2 className="text-ink-950 text-xl font-bold">AI provider use</h2>
            <p className="mt-2">
              External AI providers receive bounded, organization-scoped
              aggregates rather than raw order or customer records.
              Deterministic insight mode requires no provider key.
            </p>
          </section>
          <section>
            <h2 className="text-ink-950 text-xl font-bold">
              Security and retention
            </h2>
            <p className="mt-2">
              Sessions use revocable server-side records, tenant access is
              checked by the API, and diagnostic logs exclude passwords,
              cookies, tokens, and unnecessary customer details.
            </p>
          </section>
        </div>
      </article>
    </main>
  );
}
