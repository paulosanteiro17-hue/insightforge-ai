"use client";

import Link from "next/link";
import { Search, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const searchTargets = [
  {
    label: "Overview",
    keywords: "dashboard business performance kpi",
    path: "overview"
  },
  {
    label: "Analytics",
    keywords: "revenue trends metrics comparisons performance",
    path: "analytics"
  },
  {
    label: "Sales & orders",
    keywords: "orders transactions status payments revenue",
    path: "sales"
  },
  {
    label: "Customers",
    keywords: "customers companies segments lifetime value growth",
    path: "customers"
  },
  {
    label: "Products",
    keywords: "catalog sku units revenue price inventory performance",
    path: "products"
  },
  {
    label: "AI Insights",
    keywords: "ai insights growth warning opportunity anomaly grounded metrics",
    path: "ai-insights"
  },
  {
    label: "Ask Your Data",
    keywords: "assistant questions answers citations safe analytics",
    path: "ask-your-data"
  },
  {
    label: "Reports",
    keywords: "reports exports csv json monthly sales customer product",
    path: "reports"
  },
  {
    label: "Data Sources",
    keywords: "data sources csv import upload validation history templates",
    path: "data-sources"
  },
  {
    label: "Onboarding",
    keywords: "setup organization demo data csv profile preferences complete",
    path: "onboarding"
  },
  {
    label: "Team",
    keywords: "members invitations roles access owner admin permissions",
    path: "team"
  },
  {
    label: "Billing",
    keywords: "plan usage invoices pricing demo payment capacity",
    path: "billing"
  },
  {
    label: "Settings",
    keywords:
      "profile organization preferences security password export delete",
    path: "settings"
  }
];

export function WorkspaceSearch({
  organizationSlug
}: {
  organizationSlug: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const openSearch = useCallback(() => {
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    setIsOpen(true);
  }, []);

  const closeSearch = useCallback(() => {
    setIsOpen(false);
    setQuery("");
    globalThis.requestAnimationFrame(() => previousFocusRef.current?.focus());
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (!isOpen) {
          openSearch();
        }
      }
      if (event.key === "Escape" && isOpen) {
        closeSearch();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [closeSearch, isOpen, openSearch]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !dialogRef.current) return;
    const dialog = dialogRef.current;
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), input:not([disabled])"
        )
      );
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    dialog.addEventListener("keydown", trapFocus);
    return () => dialog.removeEventListener("keydown", trapFocus);
  }, [isOpen]);

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return searchTargets;
    }
    return searchTargets.filter((item) =>
      `${item.label} ${item.keywords}`.toLowerCase().includes(normalized)
    );
  }, [query]);

  return (
    <>
      <button
        type="button"
        onClick={openSearch}
        className="border-ink-200 bg-ink-50 text-ink-500 hover:border-ink-300 hidden h-10 w-full max-w-xs items-center gap-2 rounded-xl border px-3 text-left text-sm transition-colors hover:bg-white sm:flex"
        aria-label="Search this workspace"
      >
        <Search className="size-4" aria-hidden="true" />
        <span className="flex-1">Search this workspace</span>
        <kbd className="border-ink-200 text-ink-500 rounded border bg-white px-1.5 py-0.5 font-mono text-[10px]">
          Ctrl K
        </kbd>
      </button>
      <button
        type="button"
        onClick={openSearch}
        className="border-ink-200 text-ink-600 grid size-10 place-items-center rounded-xl border sm:hidden"
        aria-label="Search this workspace"
      >
        <Search className="size-4" aria-hidden="true" />
      </button>

      {isOpen ? (
        <div
          className="bg-ink-950/55 fixed inset-0 z-[120] flex items-start justify-center px-4 pt-[12vh] backdrop-blur-sm"
          role="presentation"
        >
          <button
            type="button"
            className="absolute inset-0"
            aria-label="Close search"
            onClick={closeSearch}
          />
          <div
            ref={dialogRef}
            className="border-ink-200 relative w-full max-w-xl overflow-hidden rounded-2xl border bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Search workspace"
          >
            <div className="border-ink-100 flex items-center gap-3 border-b px-4">
              <Search className="text-ink-400 size-5" aria-hidden="true" />
              <label htmlFor="workspace-search" className="sr-only">
                Search workspace pages
              </label>
              <input
                ref={inputRef}
                id="workspace-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="text-ink-950 placeholder:text-ink-400 h-14 min-w-0 flex-1 border-0 bg-transparent text-sm outline-none"
                placeholder="Search pages and metrics"
              />
              <button
                type="button"
                className="text-ink-500 hover:bg-ink-100 grid size-9 place-items-center rounded-lg"
                aria-label="Close search"
                onClick={closeSearch}
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto p-2">
              {results.length ? (
                <ul>
                  {results.map((item) => (
                    <li key={item.label}>
                      <Link
                        href={`/app/${organizationSlug}/${item.path}`}
                        onClick={closeSearch}
                        className="text-ink-700 hover:bg-ink-50 hover:text-ink-950 flex min-h-11 items-center rounded-xl px-3 text-sm font-medium"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-ink-500 px-3 py-8 text-center text-sm">
                  No workspace pages match “{query}”.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
