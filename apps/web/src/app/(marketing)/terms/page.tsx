import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms" };

export default function TermsPage() {
  return (
    <main id="main-content" className="bg-white px-5 py-20 sm:px-8 lg:py-28">
      <article className="mx-auto max-w-3xl">
        <p className="text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
          Terms
        </p>
        <h1 className="text-ink-950 mt-4 text-5xl font-bold tracking-[-0.06em]">
          Portfolio demonstration terms.
        </h1>
        <p className="text-ink-600 mt-6 text-lg leading-8">
          InsightForge AI demonstrates a production-oriented SaaS architecture.
          Public demo workspaces are temporary and contain fictional business
          data.
        </p>
        <div className="text-ink-600 mt-10 space-y-8 text-sm leading-7">
          <section>
            <h2 className="text-ink-950 text-xl font-bold">Demo access</h2>
            <p className="mt-2">
              Demo access may be rate-limited, reset, or expired to protect
              availability. It does not provide reusable privileged credentials
              or access to any non-demo organization.
            </p>
          </section>
          <section>
            <h2 className="text-ink-950 text-xl font-bold">Billing</h2>
            <p className="mt-2">
              Public portfolio evaluation uses a no-charge demo billing adapter.
              Plan changes are simulations and do not initiate a real or test
              payment.
            </p>
          </section>
          <section>
            <h2 className="text-ink-950 text-xl font-bold">
              Analytics guidance
            </h2>
            <p className="mt-2">
              Insights support business analysis but do not replace financial,
              legal, or professional advice. Users remain responsible for
              validating decisions against their source records.
            </p>
          </section>
        </div>
      </article>
    </main>
  );
}
