"use client";

// Shared company-search behavior (BUILD_SPEC section 19.8 app chrome):
// the debounced /api/search query, dropdown open/close, outside-click
// dismissal, and roving keyboard selection extracted from SearchBar so the
// landing hero box and the top-bar pill drive one implementation.

import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { searchCompanies } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import type { SearchResult } from "@/lib/types";

export interface CompanySearch {
  query: string;
  results: SearchResult[] | null;
  loading: boolean;
  searchError: string | null;
  activeIndex: number;
  /** True when the dropdown should be rendered. */
  showDropdown: boolean;
  containerRef: RefObject<HTMLDivElement>;
  inputRef: RefObject<HTMLInputElement>;
  /** The portaled results list, so outside-click dismissal ignores clicks
   *  inside it even though it renders outside the container in the DOM. */
  dropdownRef: RefObject<HTMLUListElement>;
  setActiveIndex: (index: number) => void;
  onQueryChange: (value: string) => void;
  onFocus: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  select: (result: SearchResult) => void;
  /** Submit affordance: open the highlighted (or first) result; with
   *  nothing to submit, return focus to the input instead. */
  submitTop: () => void;
}

export function useCompanySearch(): CompanySearch {
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
  const dropdownRef = useRef<HTMLUListElement | null>(null);

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
        setSearchError(err instanceof Error ? err.message : "Search failed.");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  // Close the dropdown when clicking outside the input AND the (portaled) list.
  useEffect(() => {
    function onMouseDown(event: MouseEvent) {
      const target = event.target as Node;
      if (
        containerRef.current?.contains(target) ||
        dropdownRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  function select(result: SearchResult) {
    setOpen(false);
    setQuery("");
    setResults(null);
    inputRef.current?.blur();
    router.push(`/company/${encodeURIComponent(result.ticker)}/dashboard`);
  }

  function submitTop() {
    if (results !== null && results.length > 0) {
      const index =
        activeIndex >= 0 && activeIndex < results.length ? activeIndex : 0;
      select(results[index]);
      return;
    }
    inputRef.current?.focus();
    setOpen(true);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
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

  return {
    query,
    results,
    loading,
    searchError,
    activeIndex,
    showDropdown,
    containerRef,
    inputRef,
    dropdownRef,
    setActiveIndex,
    onQueryChange: (value: string) => {
      setQuery(value);
      setOpen(true);
    },
    onFocus: () => setOpen(true),
    onKeyDown,
    select,
    submitTop,
  };
}

interface DropdownPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

/** The results listbox shared by both search variants. Rendered in a portal
 *  with fixed positioning so it escapes any clipping ancestor (the landing
 *  hero is `overflow-hidden`) and is never trimmed. Height is dynamic: it
 *  grows with the result count and only scrolls past ~10 rows, capped to the
 *  viewport so it never runs off-screen. */
export function SearchResultsDropdown({
  search,
  id,
}: {
  search: CompanySearch;
  id: string;
}) {
  const {
    searchError,
    loading,
    results,
    activeIndex,
    containerRef,
    dropdownRef,
  } = search;
  const [pos, setPos] = useState<DropdownPosition | null>(null);

  // Anchor the fixed dropdown to the search container, recomputing on scroll
  // and resize while it is open.
  useEffect(() => {
    if (!search.showDropdown) {
      setPos(null);
      return;
    }
    const update = () => {
      const el = containerRef.current;
      if (el === null) return;
      const r = el.getBoundingClientRect();
      const gap = 8;
      const top = r.bottom + gap;
      // Room for ~11 rows (~420px), but never past the viewport bottom.
      const maxHeight = Math.max(
        180,
        Math.min(420, window.innerHeight - top - 16),
      );
      setPos({ top, left: r.left, width: r.width, maxHeight });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [search.showDropdown, results, loading, searchError, containerRef]);

  if (!search.showDropdown || pos === null || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <ul
      id={id}
      ref={dropdownRef}
      role="listbox"
      style={{
        position: "fixed",
        top: pos.top,
        left: pos.left,
        width: pos.width,
        maxHeight: pos.maxHeight,
      }}
      className="glass-thick pop-in z-50 overflow-y-auto rounded-lg border border-line-strong py-1"
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
          <li className="px-4 py-2.5 text-sm text-ink-muted">No matches</li>
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
            onMouseEnter={() => search.setActiveIndex(index)}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => search.select(result)}
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
    </ul>,
    document.body,
  );
}
