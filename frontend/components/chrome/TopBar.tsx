"use client";

// Persistent top bar (BUILD_SPEC section 19.8 app chrome): sticky h-12
// surface bar with a hairline bottom on every page. Left: a quiet ticker
// crumb when in /company/* context. Right: the compact pill variant of the
// global company search (same useCompanySearch behavior as the landing
// hero), focusable with "/" anywhere outside a text input.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  SearchResultsDropdown,
  useCompanySearch,
} from "@/components/search/useCompanySearch";

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
    <header className="sticky top-0 z-30 flex h-12 shrink-0 items-center gap-4 border-b border-line bg-surface px-4 sm:px-6">
      {ticker !== null && (
        <Link
          href={`/company/${encodeURIComponent(ticker)}/dashboard`}
          className="min-w-0 truncate text-xs font-medium tabular-nums text-ink-muted transition-colors duration-150 hover:text-ink"
          title={`${ticker} pages`}
        >
          {ticker}
        </Link>
      )}

      <div
        ref={search.containerRef}
        className="relative ml-auto w-full max-w-[18rem]"
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
          className="h-8 w-full rounded-full border border-line bg-surface-sunken pl-8 pr-8 text-sm text-ink transition-colors duration-150 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand-soft"
          placeholder="Search companies"
          value={search.query}
          onChange={(event) => search.onQueryChange(event.target.value)}
          onFocus={search.onFocus}
          onKeyDown={search.onKeyDown}
        />
        <kbd
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-line px-1 font-sans text-[10px] leading-4 text-ink-muted"
        >
          /
        </kbd>
        <SearchResultsDropdown
          search={search}
          id="topbar-search-results"
          className="absolute right-0 top-full z-40 mt-2 w-full min-w-[20rem]"
        />
      </div>
    </header>
  );
}
