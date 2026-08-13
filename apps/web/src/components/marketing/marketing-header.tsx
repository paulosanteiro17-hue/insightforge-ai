"use client";

import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { BrandMark } from "@/components/brand/brand-mark";
import { buttonStyles } from "@/components/ui/button";

const navItems = [
  { label: "Product", href: "/#product" },
  { label: "Features", href: "/#features" },
  { label: "How it works", href: "/#how-it-works" },
  { label: "Pricing", href: "/#pricing" }
];

export function MarketingHeader() {
  const [isOpen, setIsOpen] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        menuButtonRef.current?.focus();
        return;
      }

      if (event.key !== "Tab" || !drawerRef.current) {
        return;
      }

      const focusable = Array.from(
        drawerRef.current.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), input:not([disabled])"
        )
      );
      const first = focusable[0];
      const last = focusable.at(-1);

      if (!first || !last) {
        return;
      }

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const closeMenu = () => setIsOpen(false);

  return (
    <header className="border-ink-200/70 sticky top-0 z-50 border-b bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-10">
        <BrandMark />
        <nav
          className="hidden items-center gap-7 lg:flex"
          aria-label="Primary navigation"
        >
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="text-ink-600 hover:text-ink-950 rounded-md text-sm font-medium transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <Link href="/login" className={buttonStyles({ variant: "ghost" })}>
            Sign in
          </Link>
          <Link href="/signup" className={buttonStyles()}>
            Get started
          </Link>
        </div>
        <button
          ref={menuButtonRef}
          type="button"
          className="border-ink-200 text-ink-800 grid size-11 place-items-center rounded-xl border lg:hidden"
          aria-label="Open navigation menu"
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          onClick={() => setIsOpen(true)}
        >
          <Menu className="size-5" aria-hidden="true" />
        </button>
      </div>

      {isOpen ? (
        <div className="fixed inset-0 z-[80] lg:hidden" role="presentation">
          <button
            type="button"
            className="bg-ink-950/55 absolute inset-0 backdrop-blur-sm"
            aria-label="Close navigation menu"
            onClick={closeMenu}
          />
          <div
            ref={drawerRef}
            className="absolute top-0 right-0 flex h-dvh w-[min(88vw,380px)] flex-col bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
          >
            <div className="flex items-center justify-between">
              <BrandMark />
              <button
                ref={closeButtonRef}
                type="button"
                className="border-ink-200 text-ink-800 grid size-11 place-items-center rounded-xl border"
                aria-label="Close navigation menu"
                onClick={closeMenu}
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
            <nav className="mt-10 flex flex-col" aria-label="Mobile navigation">
              {navItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className="border-ink-100 text-ink-900 border-b py-4 text-lg font-semibold"
                  onClick={closeMenu}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="mt-auto grid gap-3 pb-[max(0px,env(safe-area-inset-bottom))]">
              <Link
                href="/login"
                className={buttonStyles({
                  variant: "outline",
                  size: "lg",
                  className: "w-full"
                })}
                onClick={closeMenu}
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className={buttonStyles({ size: "lg", className: "w-full" })}
                onClick={closeMenu}
              >
                Get started
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
