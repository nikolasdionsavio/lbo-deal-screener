"use client";

// Persistent top bar (BUILD_SPEC section 19.8 app chrome): sticky h-12
// surface bar with a hairline bottom on every page. Left: the mobile nav
// hamburger (below lg) and a quiet ticker crumb when in /company/* context.
// Right: the compact pill variant of the global company search (same
// useCompanySearch behavior as the landing hero), focusable with "/"
// anywhere outside a text input; at narrow widths the pill flexes and the
// "/" hint hides.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import Logo from "@/components/Logo";
import MobileNav from "@/components/chrome/MobileNav";
import {
  SearchResultsDropdown,
  useCompanySearch,
} from "@/components/search/useCompanySearch";
import { useAuth } from "@/lib/auth";

// Account CTAs. Teal (the brand accent) deliberately stands apart from the
// navy app chrome so a logged-out visitor notices them. Register is the filled
// primary (brand green fill); Log in is the lighter outline.
const REGISTER_CTA =
  "inline-flex items-center justify-center rounded bg-action px-4 py-1.5 " +
  "text-sm font-semibold text-action-ink transition-colors duration-150 " +
  "hover:bg-action-hover active:translate-y-px " +
  "focus-visible:ring-2 focus-visible:ring-accent";

const LOGIN_CTA =
  "hidden items-center justify-center rounded border border-line-strong " +
  "px-3.5 py-1.5 text-sm font-medium text-brand-text transition-colors duration-150 " +
  "hover:border-brand hover:bg-brand-soft " +
  "focus-visible:ring-2 focus-visible:ring-accent sm:inline-flex";

function SearchIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="7" cy="7" r="4.25" />
      <path d="M10.2 10.2 14 14" />
    </svg>
  );
}

/** True when the keystroke originated in an editable element. */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

export default function TopBar() {
  const pathname = usePathname();
  const search = useCompanySearch();
  const { user } = useAuth();
  const { inputRef } = search;

  const match = pathname ? /^\/company\/([^/]+)/.exec(pathname) : null;
  const ticker = match ? decodeURIComponent(match[1]).toUpperCase() : null;

  // "/" focuses the global search unless the user is typing somewhere.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey)
        return;
      if (isTypingTarget(event.target)) return;
      event.preventDefault();
      inputRef.current?.focus();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [inputRef]);

  return (
    <header className="glass-chrome sticky top-0 z-30 flex h-12 shrink-0 items-center gap-3 border-b border-line px-4 sm:gap-4 sm:px-6">
      <MobileNav />
      <Link
        href="/"
        aria-label="Investment Intelligence home"
        title="Investment Intelligence"
        className="shrink-0 lg:hidden"
      >
        <Logo size={20} />
      </Link>
      {ticker !== null && (
        <Link
          href={`/company/${encodeURIComponent(ticker)}/dashboard`}
          className="min-w-0 truncate text-xs font-medium tabular-nums text-ink-muted transition-colors duration-150 hover:text-ink"
          title={`${ticker} pages`}
        >
          {ticker}
        </Link>
      )}

      <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-2 sm:flex-none sm:gap-3">
        <div
          ref={search.containerRef}
          className="relative min-w-0 flex-1 sm:w-72 sm:flex-none lg:w-80"
        >
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">
            <SearchIcon />
          </span>
          <input
            ref={search.inputRef}
            type="text"
            role="combobox"
            aria-label="Search companies"
            aria-expanded={search.showDropdown}
            aria-controls="topbar-search-results"
            aria-autocomplete="list"
            className="glass-thin h-9 w-full rounded-md border border-line-strong pl-8 pr-3 text-sm text-ink transition-colors duration-150 placeholder:text-ink-muted hover:border-brand focus:border-brand focus:ring-2 focus:ring-brand-soft md:pr-8"
            placeholder="Search companies"
            value={search.query}
            onChange={(event) => search.onQueryChange(event.target.value)}
            onFocus={search.onFocus}
            onKeyDown={search.onKeyDown}
          />
          <kbd
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-line px-1 font-sans text-[10px] leading-4 text-ink-muted md:block"
          >
            /
          </kbd>
          <SearchResultsDropdown search={search} id="topbar-search-results" />
        </div>

        {!user && (
          <nav
            aria-label="Account"
            className="flex shrink-0 items-center gap-2 sm:gap-2.5"
          >
            <Link href="/login" className={LOGIN_CTA}>
              Log in
            </Link>
            <Link href="/register" className={REGISTER_CTA}>
              Register
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
