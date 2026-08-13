"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Bot,
  ChevronDown,
  CreditCard,
  DatabaseZap,
  FileBarChart,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  ShoppingBag,
  Sparkles,
  Settings,
  UsersRound,
  X
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { BrandMark } from "@/components/brand/brand-mark";
import { WorkspaceSearch } from "@/components/product/workspace-search";
import { Badge } from "@/components/ui/badge";
import type { OrganizationSummary, UserSummary } from "@/lib/api/contracts";
import { insightForgeApi } from "@runtime-api";
import { cn } from "@/lib/cn";

const workspaceSections = [
  { label: "Overview", path: "overview", icon: LayoutDashboard },
  { label: "Analytics", path: "analytics", icon: BarChart3 },
  { label: "Sales", path: "sales", icon: ShoppingBag },
  { label: "Customers", path: "customers", icon: UsersRound },
  { label: "Products", path: "products", icon: PackageSearch },
  { label: "AI Insights", path: "ai-insights", icon: Sparkles },
  { label: "Ask Your Data", path: "ask-your-data", icon: Bot },
  { label: "Reports", path: "reports", icon: FileBarChart },
  { label: "Data Sources", path: "data-sources", icon: DatabaseZap },
  { label: "Onboarding", path: "onboarding", icon: Sparkles },
  { label: "Team", path: "team", icon: UsersRound },
  { label: "Billing", path: "billing", icon: CreditCard },
  { label: "Settings", path: "settings", icon: Settings }
];

const roleLabels: Record<OrganizationSummary["role"], string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member"
};

function SidebarContent({
  pathname,
  organization,
  onNavigate
}: {
  pathname: string;
  organization: OrganizationSummary;
  onNavigate?: () => void;
}) {
  const organizationInitials = organization.name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="scrollbar-subtle flex h-full flex-col overflow-y-auto">
      <div className="px-5 pt-5 pb-6">
        <BrandMark inverse />
      </div>
      <div className="px-4">
        <div className="rounded-2xl border border-white/10 bg-white/[0.055] p-3">
          <div className="flex items-center gap-3">
            <span className="bg-coral-500 text-ink-950 grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold">
              {organizationInitials}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">
                {organization.name}
              </p>
              <p className="text-ink-300 mt-0.5 text-[11px]">
                {roleLabels[organization.role]} ·{" "}
                {organization.is_demo ? "Demo workspace" : "Live workspace"}
              </p>
            </div>
          </div>
        </div>
      </div>
      <nav className="mt-7 px-3" aria-label="Workspace pages">
        <p className="text-ink-300 px-3 text-[10px] font-bold tracking-[0.16em] uppercase">
          Workspace
        </p>
        <ul className="mt-2 space-y-1">
          {workspaceSections.map((item) => {
            const Icon = item.icon;
            const href = `/app/${organization.slug}/${item.path}`;
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={item.label}>
                <Link
                  href={href}
                  onClick={onNavigate}
                  className={cn(
                    "flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                    active
                      ? "bg-white/10 text-white"
                      : "text-ink-300 hover:bg-white/[0.06] hover:text-white"
                  )}
                >
                  <Icon className="size-[17px]" aria-hidden="true" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="mt-auto p-4">
        <div className="rounded-2xl border border-teal-400/15 bg-teal-400/[0.08] p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-300">
            <Sparkles className="size-3.5" aria-hidden="true" /> Deterministic
            AI
          </div>
          <p className="text-ink-300 mt-2 text-[11px] leading-5">
            Insights remain available without an external provider key.
          </p>
        </div>
      </div>
    </div>
  );
}

export function ProductShell({
  children,
  organization,
  organizations,
  user
}: {
  children: ReactNode;
  organization: OrganizationSummary;
  organizations: OrganizationSummary[];
  user: UserSummary;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const mobileCloseRef = useRef<HTMLButtonElement>(null);
  const mobileMenuRef = useRef<HTMLButtonElement>(null);
  const mobileAsideRef = useRef<HTMLElement>(null);
  const activeSection = workspaceSections.find((section) =>
    pathname.startsWith(`/app/${organization.slug}/${section.path}`)
  );
  const userInitials = user.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    if (!mobileOpen) return;
    mobileCloseRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        globalThis.requestAnimationFrame(() => mobileMenuRef.current?.focus());
      }
      if (event.key === "Tab" && mobileAsideRef.current) {
        const focusable = Array.from(
          mobileAsideRef.current.querySelectorAll<HTMLElement>(
            "a[href], button:not([disabled])"
          )
        );
        const first = focusable[0];
        const last = focusable.at(-1);
        if (
          first &&
          last &&
          event.shiftKey &&
          document.activeElement === first
        ) {
          event.preventDefault();
          last.focus();
        } else if (
          first &&
          last &&
          !event.shiftKey &&
          document.activeElement === last
        ) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [mobileOpen]);

  function closeMobileNavigation() {
    setMobileOpen(false);
    globalThis.requestAnimationFrame(() => mobileMenuRef.current?.focus());
  }

  async function switchOrganization(slug: string) {
    if (slug === organization.slug) return;
    await queryClient.cancelQueries({ queryKey: ["organization"] });
    queryClient.removeQueries({ queryKey: ["organization"] });
    router.push(`/app/${slug}/${activeSection?.path ?? "overview"}`);
  }

  async function signOut() {
    setSigningOut(true);
    try {
      await insightForgeApi.auth.signOut();
      queryClient.clear();
      setUserMenuOpen(false);
      router.push("/login");
      router.refresh();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="bg-ink-50 min-h-screen">
      <aside className="bg-ink-950 fixed inset-y-0 left-0 z-40 hidden w-[17rem] xl:block">
        <SidebarContent pathname={pathname} organization={organization} />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-[100] xl:hidden" role="presentation">
          <button
            type="button"
            className="bg-ink-950/60 absolute inset-0 backdrop-blur-sm"
            aria-label="Close navigation"
            onClick={closeMobileNavigation}
          />
          <aside
            ref={mobileAsideRef}
            className="bg-ink-950 absolute inset-y-0 left-0 w-[min(86vw,19rem)] shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Workspace navigation"
          >
            <button
              ref={mobileCloseRef}
              type="button"
              onClick={closeMobileNavigation}
              className="text-ink-300 absolute top-4 right-3 z-10 grid size-10 place-items-center rounded-xl hover:bg-white/10 hover:text-white"
              aria-label="Close navigation"
            >
              <X className="size-5" aria-hidden="true" />
            </button>
            <SidebarContent
              pathname={pathname}
              organization={organization}
              onNavigate={closeMobileNavigation}
            />
          </aside>
        </div>
      ) : null}

      <div className="xl:pl-[17rem]">
        <header className="border-ink-200/80 sticky top-0 z-30 border-b bg-white/92 backdrop-blur-xl">
          <div className="flex h-18 items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              ref={mobileMenuRef}
              type="button"
              className="border-ink-200 text-ink-700 grid size-10 shrink-0 place-items-center rounded-xl border xl:hidden"
              aria-label="Open navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="size-5" aria-hidden="true" />
            </button>
            <div className="hidden min-w-0 items-center gap-2 md:flex">
              <span className="text-ink-400 text-sm">Workspace</span>
              <span className="text-ink-300">/</span>
              <span className="text-ink-800 text-sm font-semibold">
                {activeSection?.label ?? "Workspace"}
              </span>
            </div>
            <div className="mx-auto flex min-w-0 flex-1 items-center justify-center sm:max-w-sm lg:max-w-md">
              <WorkspaceSearch organizationSlug={organization.slug} />
            </div>
            {organization.is_demo ? (
              <Badge className="border-coral-500/20 bg-coral-50 text-coral-700 hidden lg:inline-flex">
                <span className="bg-coral-500 size-1.5 rounded-full" /> Demo
                mode
              </Badge>
            ) : null}
            <label className="relative hidden sm:block">
              <span className="sr-only">Active organization</span>
              <select
                value={organization.slug}
                onChange={(event) =>
                  void switchOrganization(event.target.value)
                }
                className="border-ink-200 text-ink-800 h-10 max-w-48 appearance-none rounded-xl border bg-white pr-9 pl-3 text-sm font-semibold shadow-sm"
              >
                {organizations.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name}
                  </option>
                ))}
              </select>
              <ChevronDown
                className="text-ink-500 pointer-events-none absolute top-3 right-3 size-4"
                aria-hidden="true"
              />
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => setUserMenuOpen((open) => !open)}
                className="bg-ink-950 flex size-10 items-center justify-center rounded-xl text-xs font-bold text-white"
                aria-label="Open user menu"
                aria-expanded={userMenuOpen}
                aria-haspopup="menu"
              >
                {userInitials}
              </button>
              {userMenuOpen ? (
                <div
                  className="border-ink-200 absolute top-12 right-0 w-64 rounded-2xl border bg-white p-2 shadow-[var(--shadow-soft)]"
                  role="menu"
                >
                  <div className="border-ink-100 border-b px-3 py-3">
                    <p className="text-ink-950 text-sm font-semibold">
                      {user.display_name}
                    </p>
                    <p className="text-ink-500 mt-0.5 truncate text-xs">
                      {user.email}
                    </p>
                  </div>
                  <div className="text-ink-500 px-3 py-3 text-xs leading-5">
                    <span className="text-ink-700 font-semibold">
                      {organization.is_demo ? "Demo " : ""}
                      {roleLabels[organization.role]}
                    </span>
                    <br />
                    {organization.is_demo
                      ? "Sensitive account actions are disabled in this isolated workspace."
                      : "Manage your profile and workspace access from settings."}
                  </div>
                  <Link
                    href={`/app/${organization.slug}/settings`}
                    role="menuitem"
                    className="text-ink-700 hover:bg-ink-50 flex min-h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold"
                  >
                    <Settings className="size-4" aria-hidden="true" /> Settings
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    disabled={signingOut}
                    onClick={() => void signOut()}
                    className="text-ink-700 hover:bg-ink-50 flex min-h-10 w-full items-center gap-2 rounded-xl px-3 text-sm font-semibold disabled:opacity-60"
                  >
                    <LogOut className="size-4" aria-hidden="true" />
                    {signingOut ? "Signing out" : "Sign out"}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>
        <main
          id="main-content"
          className="mx-auto w-full max-w-[100rem] px-4 py-6 sm:px-6 lg:px-8 lg:py-8"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
