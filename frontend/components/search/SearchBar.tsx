"use client";

// Debounced company search styled as a large prompt box (DESIGN.md
// Aesthetic v2 hero): a surface card with a borderless input, a footer row
// for sample-ticker chips (passed in via `footer`), and a circular ink-pill
// submit button. The query/dropdown/keyboard behavior lives in
// useCompanySearch, shared with the top-bar pill variant.

import type { ReactNode } from "react";
import {
  SearchResultsDropdown,
  useCompanySearch,
} from "@/components/search/useCompanySearch";

interface SearchBarProps {
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
  /** Left side of the footer row inside the box (e.g. sample-ticker chips). */
  footer?: ReactNode;
}

function ArrowIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2.5 8h11M9 3.5 13.5 8 9 12.5" />
    </svg>
  );
}

export default function SearchBar({
  className = "",
  placeholder = "Search by ticker or company name",
  autoFocus = false,
  footer,
}: SearchBarProps) {
  const search = useCompanySearch();

  return (
    <div ref={search.containerRef} className={`relative ${className}`}>
      <div className="rounded-md border border-line-strong bg-surface-raised p-3.5 transition-colors duration-150 focus-within:border-brand sm:p-4">
        <input
          ref={search.inputRef}
          type="text"
          role="combobox"
          aria-expanded={search.showDropdown}
          aria-controls="company-search-results"
          aria-autocomplete="list"
          autoFocus={autoFocus}
          className="w-full bg-transparent px-1 py-1.5 text-base text-ink outline-none"
          placeholder={placeholder}
          value={search.query}
          onChange={(event) => search.onQueryChange(event.target.value)}
          onFocus={search.onFocus}
          onKeyDown={search.onKeyDown}
        />

        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {footer}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {search.loading && (
              <span
                className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-brand"
                role="status"
                aria-label="Searching"
              />
            )}
            <button
              type="button"
              onClick={search.submitTop}
              aria-label="Open the top search result"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-brand text-white transition duration-150 hover:bg-brand-hover active:translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            >
              <ArrowIcon />
            </button>
          </div>
        </div>
      </div>

      <SearchResultsDropdown search={search} id="company-search-results" />
    </div>
  );
}
