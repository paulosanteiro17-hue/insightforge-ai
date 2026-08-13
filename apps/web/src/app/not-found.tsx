import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BrandMark } from "@/components/brand/brand-mark";
import { buttonStyles } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main
      id="main-content"
      className="bg-ink-50 grid min-h-screen place-items-center px-6"
    >
      <div className="max-w-lg text-center">
        <BrandMark className="justify-center" />
        <p className="mt-12 text-sm font-bold tracking-[0.16em] text-teal-700 uppercase">
          404
        </p>
        <h1 className="text-ink-950 mt-3 text-4xl font-bold tracking-[-0.045em]">
          This page is outside the map.
        </h1>
        <p className="text-ink-600 mt-4 text-base leading-7">
          The link may have changed, or you may not have access to this
          workspace.
        </p>
        <Link href="/" className={buttonStyles({ className: "mt-7" })}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Return home
        </Link>
      </div>
    </main>
  );
}
