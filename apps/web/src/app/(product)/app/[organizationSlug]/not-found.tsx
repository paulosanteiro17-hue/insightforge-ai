import Link from "next/link";
import { SearchX } from "lucide-react";
import { buttonStyles } from "@/components/ui/button";

export default function OrganizationNotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center px-4 text-center">
      <div className="max-w-md">
        <span className="bg-ink-100 text-ink-600 mx-auto grid size-12 place-items-center rounded-2xl">
          <SearchX className="size-5" aria-hidden="true" />
        </span>
        <h1 className="text-ink-950 mt-5 text-3xl font-bold tracking-[-0.045em]">
          Workspace not found
        </h1>
        <p className="text-ink-600 mt-3 text-sm leading-6">
          This workspace is unavailable or your session does not include access
          to it.
        </p>
        <Link href="/app" className={buttonStyles({ className: "mt-6" })}>
          Return to your workspace
        </Link>
      </div>
    </div>
  );
}
