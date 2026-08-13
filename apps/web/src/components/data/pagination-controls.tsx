"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PaginationControls({
  page,
  totalPages,
  totalItems,
  itemLabel
}: {
  page: number;
  totalPages: number;
  totalItems: number;
  itemLabel: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  function goToPage(nextPage: number) {
    const next = new URLSearchParams(searchParams.toString());
    if (nextPage <= 1) next.delete("page");
    else next.set("page", String(nextPage));
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false
    });
  }

  return (
    <nav
      className="border-ink-100 flex flex-col gap-3 border-t px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5"
      aria-label={`${itemLabel} pagination`}
    >
      <p className="text-ink-500 text-xs">
        {totalItems.toLocaleString("en-US")} {itemLabel} · Page {page} of{" "}
        {totalPages}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => goToPage(page - 1)}
        >
          <ChevronLeft className="size-4" aria-hidden="true" /> Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => goToPage(page + 1)}
        >
          Next <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
