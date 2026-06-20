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
// primary; Log in is the lighter outline. Literal teal-* (not the --accent
// token) so opacity modifiers and per-theme tuning behave predictably.
const REGISTER_CTA =
  "inline-flex items-center justify-center rounded-full bg-teal-600 px-4 py-1.5 " +
  "text-sm font-semibold text-white shadow-sm transition-all duration-150 " +
  "hover:-translate-y-px hover:bg-teal-700 hover:shadow-md active:translate-y-0 " +
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 " +
  "dark:bg-teal-400 dark:text-teal-950 dark:hover:bg-teal-300";

const LOGIN_CTA =
  "hidden items-center justify-center rounded-full border border-teal-600/40 " +
  "px-3.5 py-1.5 text-sm font-medium text-teal-700 transition-colors duration-150 " +
  "hover:border-teal-600 hover:bg-teal-50 focus:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-teal-500 sm:inline-flex " +
  "dark:border-teal-400/40 dark:text-teal-300 dark:hover:bg-teal-400/10";

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
    <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center gap-3 border-b border-line bg-surface px-4 sm:gap-4 sm:px-6">
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
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-teal-600 dark:text-teal-400">
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
            className="h-9 w-full rounded-full border border-line-strong bg-surface pl-8 pr-3 text-sm text-ink shadow-sm ring-1 ring-inset ring-teal-500/10 transition-all duration-150 placeholder:text-ink-muted hover:border-teal-500/60 hover:shadow focus:border-teal-500 focus:shadow-md focus:outline-none focus:ring-2 focus:ring-teal-500/40 md:pr-8"
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
