"use client";

// Debounced company search with a keyboard-navigable dropdown.
// Queries /api/search 300ms after typing settles; Enter or click navigates
// to /company/<ticker>/dashboard.

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { searchCompanies } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import type { SearchResult } from "@/lib/types";

interface SearchBarProps {
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
}

export default function SearchBar({
  className = "",
  placeholder = "Search by ticker or company name",
  autoFocus = false,
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
      <div className="flex items-center rounded-lg border border-line bg-surface-sunken transition-colors duration-150 focus-within:border-brand focus-within:ring-2 focus-within:ring-brand-soft">
        <input
          type="text"
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls="company-search-results"
          aria-autocomplete="list"
          autoFocus={autoFocus}
          className="w-full rounded-lg bg-transparent px-4 py-3 text-sm text-ink outline-none"
          placeholder={placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
        />
        {loading && (
          <span
            className="mr-4 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-brand"
            role="status"
            aria-label="Searching"
          />
        )}
      </div>

      {showDropdown && (
        <ul
          id="company-search-results"
          role="listbox"
          className="absolute left-0 right-0 top-full z-20 mt-1 max-h-80 overflow-y-auto rounded-lg border border-line-strong bg-surface py-1 shadow-card-hover"
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
