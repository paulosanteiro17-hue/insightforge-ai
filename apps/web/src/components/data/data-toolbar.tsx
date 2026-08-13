"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { useRef, type FormEvent } from "react";
import { Button } from "@/components/ui/button";

export interface ToolbarOption {
  value: string;
  label: string;
}

export interface ToolbarFilter {
  param: string;
  label: string;
  allLabel: string;
  options: ToolbarOption[];
}

export function DataToolbar({
  searchLabel,
  searchPlaceholder,
  filters = [],
  sortOptions
}: {
  searchLabel: string;
  searchPlaceholder: string;
  filters?: ToolbarFilter[];
  sortOptions: ToolbarOption[];
}) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchInputRef = useRef<HTMLInputElement>(null);

  function replaceParam(param: string, value: string) {
    const next = new URLSearchParams(searchParams.toString());
    if (value) next.set(param, value);
    else next.delete(param);
    next.set("page", "1");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    replaceParam("q", searchInputRef.current?.value.trim() ?? "");
  }

  function clearAll() {
    const next = new URLSearchParams(searchParams.toString());
    next.delete("q");
    next.delete("page");
    filters.forEach((filter) => next.delete(filter.param));
    next.delete("sort");
    if (searchInputRef.current) searchInputRef.current.value = "";
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, {
      scroll: false
    });
  }

  const hasActiveFilters =
    Boolean(searchParams.get("q")) ||
    Boolean(searchParams.get("sort")) ||
    filters.some((filter) => Boolean(searchParams.get(filter.param)));

  return (
    <div className="border-ink-200/80 rounded-2xl border bg-white p-3 shadow-[var(--shadow-panel)]">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <form
          className="flex min-w-0 flex-1 gap-2"
          role="search"
          onSubmit={submitSearch}
        >
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">{searchLabel}</span>
            <Search
              className="text-ink-400 pointer-events-none absolute top-3 left-3 size-4"
              aria-hidden="true"
            />
            <input
              type="search"
              ref={searchInputRef}
              key={searchParams.get("q") ?? ""}
              defaultValue={searchParams.get("q") ?? ""}
              placeholder={searchPlaceholder}
              className="border-ink-200 text-ink-900 placeholder:text-ink-400 h-10 w-full rounded-xl border bg-white pr-3 pl-9 text-sm transition outline-none focus:border-teal-500 focus:ring-3 focus:ring-teal-500/10"
            />
          </label>
          <Button type="submit" variant="outline" className="shrink-0">
            Search
          </Button>
        </form>
        <div
          className="flex flex-wrap items-center gap-2"
          aria-label="List filters"
        >
          <SlidersHorizontal
            className="text-ink-400 hidden size-4 sm:block"
            aria-hidden="true"
          />
          {filters.map((filter) => (
            <label key={filter.param} className="min-w-0 flex-1 sm:flex-none">
              <span className="sr-only">{filter.label}</span>
              <select
                aria-label={filter.label}
                value={searchParams.get(filter.param) ?? ""}
                onChange={(event) =>
                  replaceParam(filter.param, event.target.value)
                }
                className="border-ink-200 text-ink-700 h-10 w-full rounded-xl border bg-white px-3 text-sm font-medium sm:w-auto"
              >
                <option value="">{filter.allLabel}</option>
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <label className="min-w-0 flex-1 sm:flex-none">
            <span className="sr-only">Sort results</span>
            <select
              aria-label="Sort results"
              value={searchParams.get("sort") ?? ""}
              onChange={(event) => replaceParam("sort", event.target.value)}
              className="border-ink-200 text-ink-700 h-10 w-full rounded-xl border bg-white px-3 text-sm font-medium sm:w-auto"
            >
              {sortOptions.map((option, index) => (
                <option
                  key={option.value}
                  value={index === 0 ? "" : option.value}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {hasActiveFilters ? (
            <button
              type="button"
              onClick={clearAll}
              className="text-ink-500 hover:bg-ink-50 hover:text-ink-900 inline-flex h-10 items-center gap-1.5 rounded-xl px-3 text-xs font-semibold"
            >
              <X className="size-3.5" aria-hidden="true" /> Clear
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
