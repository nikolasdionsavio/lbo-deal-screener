"use client";

// Deal screen: filter every US-listed filer on figures taken from their own
// SEC filings. The index behind it is built from the SEC XBRL frames API, so
// this is one indexed query rather than thousands of per-company fetches.
//
// The coverage strip above the table is not decoration. Roughly four in ten
// filers do not tag D&A separately, so their EBITDA cannot be calculated at
// all, and saying so is what keeps an EBITDA screen honest.

import { useCallback, useEffect, useMemo, useState } from "react";
import ScreenFilters, {
  EMPTY_FILTERS,
  type ScreenFilterState,
} from "@/components/screen/ScreenFilters";
import ScreenTable from "@/components/screen/ScreenTable";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { getScreen, getScreenSectors } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { ScreenQuery, ScreenResponse } from "@/lib/types";

const PAGE_SIZE = 50;

/** Millions in the input, full units at the API boundary. */
function toUnits(millions: string): number | null {
  const n = Number.parseFloat(millions);
  return Number.isFinite(n) ? n * 1e6 : null;
}

function toFraction(percent: string): number | null {
  const n = Number.parseFloat(percent);
  return Number.isFinite(n) ? n / 100 : null;
}

export default function ScreenPage() {
  const [filters, setFilters] = useState<ScreenFilterState>(EMPTY_FILTERS);
  const [sort, setSort] = useState("revenue");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const sectors = useApi(() => getScreenSectors(), []);

  const query = useMemo<ScreenQuery>(
    () => ({
      revenue_min: toUnits(filters.revenueMinM),
      revenue_max: toUnits(filters.revenueMaxM),
      ebitda_positive: filters.ebitdaPositive || undefined,
      margin_min: toFraction(filters.marginMinPct),
      sector: filters.sector || null,
      q: filters.q.trim() || null,
      exclude_flagged: filters.excludeFlagged || undefined,
      sort,
      direction,
      limit: PAGE_SIZE,
      offset,
    }),
    [filters, sort, direction, offset],
  );

  const run = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    getScreen(query)
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not run the screen.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [query]);

  // Debounced so typing in the revenue or search fields does not fire a
  // request per keystroke.
  useEffect(() => {
    const timer = setTimeout(run, 250);
    return () => clearTimeout(timer);
  }, [run]);

  // Any filter change invalidates the current page position.
  useEffect(() => setOffset(0), [filters, sort, direction]);

  const onSort = (key: string) => {
    if (key === sort) {
      setDirection((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSort(key);
      setDirection(key === "entity_name" ? "asc" : "desc");
    }
  };

  const coverage = data?.coverage;
  const indexEmpty = coverage !== undefined && coverage.total === 0;
  const shown = data ? data.rows.length : 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto w-full max-w-[80rem] px-4 py-8 sm:px-6">
      <header className="border-b border-line pb-5">
        <h1 className="text-[1.375rem] font-medium text-ink">Deal screen</h1>
        <p className="mt-1 max-w-[68ch] text-[0.875rem] leading-snug text-ink-secondary">
          Filter every US-listed filer on figures taken from their own SEC
          filings. Revenue and operating income are as reported. EBITDA is
          calculated as operating income plus depreciation and amortisation, and
          is left blank where a company does not report D&amp;A separately.
        </p>
        {coverage && !indexEmpty && (
          <p className="mt-3 font-mono text-[11px] leading-relaxed text-ink-muted">
            {coverage.total.toLocaleString()} US-listed filers indexed ·{" "}
            {coverage.with_ebitda.toLocaleString()} with a calculable EBITDA ·{" "}
            {coverage.ebit_only.toLocaleString()} do not disclose D&amp;A ·{" "}
            {coverage.revenue_only.toLocaleString()} revenue only
            {coverage.refreshed_at
              ? ` · indexed ${coverage.refreshed_at.slice(0, 10)}`
              : ""}
          </p>
        )}
      </header>

      <div className="mt-6 grid gap-8 lg:grid-cols-[15rem_1fr]">
        <aside className="lg:border-r lg:border-line lg:pr-6">
          <ScreenFilters
            value={filters}
            onChange={setFilters}
            sectors={sectors.data ?? []}
            onReset={() => setFilters(EMPTY_FILTERS)}
          />
        </aside>

        <section className="min-w-0">
          {indexEmpty ? (
            <p className="border border-line bg-surface px-4 py-8 text-center text-[0.875rem] text-ink-secondary">
              The screening index has not been built yet, so there is nothing to
              filter. It is populated from SEC filings by a separate refresh
              step.
            </p>
          ) : error !== null ? (
            <ErrorState message={error} onRetry={run} />
          ) : loading && data === null ? (
            <LoadingState lines={10} />
          ) : data ? (
            <>
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 pb-3">
                <p className="text-[0.875rem] text-ink">
                  <span className="font-mono tabular-nums">
                    {data.total.toLocaleString()}
                  </span>{" "}
                  {data.total === 1 ? "company" : "companies"} match
                </p>
                <p className="font-mono text-[11px] text-ink-muted">
                  {data.source}
                </p>
              </div>

              <ScreenTable
                rows={data.rows}
                sort={sort}
                direction={direction}
                onSort={onSort}
              />

              <p className="mt-3 max-w-[74ch] text-[11px] leading-relaxed text-ink-muted">
                {data.note}
              </p>

              {data.total > PAGE_SIZE && (
                <div className="mt-5 flex items-center justify-between border-t border-line pt-3">
                  <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                    className="text-[0.8125rem] text-link disabled:cursor-not-allowed disabled:text-ink-muted"
                  >
                    ← Previous
                  </button>
                  <span className="font-mono text-[11px] text-ink-muted">
                    {page} of {pages}
                  </span>
                  <button
                    type="button"
                    disabled={offset + shown >= data.total}
                    onClick={() => setOffset((o) => o + PAGE_SIZE)}
                    className="text-[0.8125rem] text-link disabled:cursor-not-allowed disabled:text-ink-muted"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}
