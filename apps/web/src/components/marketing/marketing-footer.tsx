import Link from "next/link";
import { BrandMark } from "@/components/brand/brand-mark";

export function MarketingFooter() {
  return (
    <footer className="border-ink-200 border-t bg-white">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 sm:px-8 md:grid-cols-[1.2fr_1fr] lg:px-10">
        <div>
          <BrandMark />
          <p className="text-ink-600 mt-4 max-w-md text-sm leading-6">
            A full-stack SaaS analytics product that turns trustworthy business
            metrics into clear, grounded decisions.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          <div>
            <p className="text-ink-500 text-xs font-bold tracking-[0.14em] uppercase">
              Product
            </p>
            <div className="text-ink-600 mt-4 grid gap-3 text-sm">
              <Link href="/#features" className="hover:text-ink-950">
                Features
              </Link>
              <Link href="/#pricing" className="hover:text-ink-950">
                Pricing
              </Link>
              <Link href="/login" className="hover:text-ink-950">
                Demo
              </Link>
            </div>
          </div>
          <div>
            <p className="text-ink-500 text-xs font-bold tracking-[0.14em] uppercase">
              Company
            </p>
            <div className="text-ink-600 mt-4 grid gap-3 text-sm">
              <Link href="/privacy" className="hover:text-ink-950">
                Privacy
              </Link>
              <Link href="/terms" className="hover:text-ink-950">
                Terms
              </Link>
            </div>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-ink-500 text-xs font-bold tracking-[0.14em] uppercase">
              Built with
            </p>
            <p className="text-ink-600 mt-4 text-sm leading-6">
              Next.js, FastAPI, PostgreSQL, and responsible AI.
            </p>
          </div>
        </div>
      </div>
      <div className="border-ink-100 text-ink-500 border-t px-5 py-5 text-center text-xs">
        © 2026 InsightForge AI. Portfolio demonstration with no-charge demo
        billing.
      </div>
    </footer>
  );
}
