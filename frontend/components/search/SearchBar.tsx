"use client";

// The main product interaction on the public site (DESIGN.md). A single large
// research field: 60px, 4px radius, one rule, paper-raised. On focus the rule
// darkens and a thin accent inset appears. No pill, no glow, no growth.
// Query/dropdown/keyboard behaviour lives in useCompanySearch.

import type { ReactNode } from "react";
import {
  SearchResultsDropdown,
  useCompanySearch,
} from "@/components/search/useCompanySearch";

interface SearchBarProps {
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
  /** Optional trailing slot (kept for callers that pass shortcuts). */
  footer?: ReactNode;
}

function SearchGlyph() {
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
      <circle cx="7" cy="7" r="4.25" />
      <path d="M10.2 10.2 14 14" />
    </svg>
  );
}

export default function SearchBar({
  className = "",
  placeholder = "Search by company name or ticker",
  autoFocus = false,
}: SearchBarProps) {
  const search = useCompanySearch();

  return (
    <div ref={search.containerRef} className={`relative ${className}`}>
      <div className="glass flex h-[60px] items-center gap-3 rounded-[4px] border border-line-strong px-4 transition-colors duration-150 focus-within:border-ink-secondary focus-within:ring-2 focus-within:ring-inset focus-within:ring-accent">
        <span className="shrink-0 text-ink-muted">
          <SearchGlyph />
        </span>
        <input
          ref={search.inputRef}
          type="text"
          role="combobox"
          aria-expanded={search.showDropdown}
          aria-controls="company-search-results"
          aria-autocomplete="list"
          autoFocus={autoFocus}
          className="min-w-0 flex-1 bg-transparent text-[1.0625rem] text-ink outline-none placeholder:text-ink-muted"
          placeholder={placeholder}
          value={search.query}
          onChange={(event) => search.onQueryChange(event.target.value)}
          onFocus={search.onFocus}
          onKeyDown={search.onKeyDown}
        />
        {search.loading ? (
          <span
            className="h-3.5 w-3.5 shrink-0 animate-spin rounded-circle border border-line-strong border-t-brand"
            role="status"
            aria-label="Searching"
          />
        ) : search.query.trim() !== "" ? (
          <button
            type="button"
            onClick={search.submitTop}
            className="shrink-0 rounded-[3px] px-1.5 py-1 font-mono text-[11px] text-ink-muted transition-colors hover:text-brand-text"
          >
            return &crarr;
          </button>
        ) : null}
      </div>

      <SearchResultsDropdown search={search} id="company-search-results" />
    </div>
  );
}
