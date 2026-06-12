"use client";

// Debounced company search styled as a large prompt box (DESIGN.md
// Aesthetic v2 hero): a surface card with a borderless input, a footer row
// for sample-ticker chips (passed in via `footer`), and a circular ink-pill
// submit button. Queries /api/search 300ms after typing settles; Enter,
// click, or the submit button navigates to /company/<ticker>/dashboard.

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { searchCompanies } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import type { SearchResult } from "@/lib/types";

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
  const router = useRouter();
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounced(query.trim(), 300);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (debouncedQuery === "") {
      setResults(null);
      setSearchError(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setSearchError(null);
    searchCompanies(debouncedQuery)
      .then((items) => {
        if (cancelled) return;
        setResults(items);
        setActiveIndex(items.length > 0 ? 0 : -1);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setResults(null);
        setSearchError(
          err instanceof Error ? err.message : "Search failed.",
        );
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  // Close the dropdown when clicking outside the component.
  useEffect(() => {
    function onMouseDown(event: MouseEvent) {
      if (
        containerRef.current !== null &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  function select(result: SearchResult) {
    setOpen(false);
    setQuery("");
    setResults(null);
    router.push(`/company/${encodeURIComponent(result.ticker)}/dashboard`);
  }

  /** Submit affordance: open the highlighted (or first) result; with
   *  nothing to submit, return focus to the input instead. */
  function submitTop() {
    if (results !== null && results.length > 0) {
      const index = activeIndex >= 0 && activeIndex < results.length
        ? activeIndex
        : 0;
      select(results[index]);
      return;
    }
    inputRef.current?.focus();
    setOpen(true);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open || results === null || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (i + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (i - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0 && activeIndex < results.length) {
        select(results[activeIndex]);
      }
    }
  }

  const hasDropdownContent =
    searchError !== null || loading || results !== null;
  const showDropdown = open && query.trim() !== "" && hasDropdownContent;

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-card transition-shadow duration-150 focus-within:shadow-card-hover sm:p-5">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls="company-search-results"
          aria-autocomplete="list"
          autoFocus={autoFocus}
          className="w-full bg-transparent px-1 py-1.5 text-base text-ink outline-none"
          placeholder={placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
        />

        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {footer}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {loading && (
              <span
                className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-brand"
                role="status"
                aria-label="Searching"
              />
            )}
            <button
              type="button"
              onClick={submitTop}
              aria-label="Open the top search result"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-surface transition duration-150 hover:-translate-y-px hover:shadow-card-hover active:translate-y-0 active:shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            >
              <ArrowIcon />
            </button>
          </div>
        </div>
      </div>

      {showDropdown && (
        <ul
          id="company-search-results"
          role="listbox"
          className="absolute left-0 right-0 top-full z-20 mt-2 max-h-80 overflow-y-auto rounded border border-line-strong bg-surface py-1 shadow-card-hover"
        >
          {searchError !== null && (
            <li className="px-4 py-2.5 text-sm text-negative-text">
              {searchError}
            </li>
          )}
          {searchError === null && loading && results === null && (
            <li className="px-4 py-2.5 text-sm text-ink-muted">Searching</li>
          )}
          {searchError === null &&
            !loading &&
            results !== null &&
            results.length === 0 && (
              <li className="px-4 py-2.5 text-sm text-ink-muted">
                No matches
              </li>
            )}
          {searchError === null &&
            results !== null &&
            results.map((result, index) => (
              <li
                key={`${result.ticker}-${result.source}`}
                role="option"
                aria-selected={index === activeIndex}
                className={`cursor-pointer px-4 py-2 text-sm ${
                  index === activeIndex ? "bg-brand-soft" : ""
                }`}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => select(result)}
              >
                <span className="font-semibold tabular-nums text-ink">
                  {result.ticker}
                </span>
                <span className="ml-2 text-ink-secondary">{result.name}</span>
                {result.exchange !== null && result.exchange !== "" && (
                  <span className="ml-2 text-xs text-ink-muted">
                    {result.exchange}
                  </span>
                )}
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
