"use client";

// Deal screen: filter every US-listed filer on figures taken from their own SEC
// filings. The index behind it is built from the SEC XBRL frames API, so this
// is one indexed query rather than thousands of per-company fetches.
//
// The coverage strip above the table is not decoration. Roughly four in ten
// filers do not tag D&A separately, so their EBITDA cannot be calculated at
// all, and saying so is what keeps an EBITDA screen honest.

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import AppliedFilters from "@/components/screen/AppliedFilters";
import ScreenFilters from "@/components/screen/ScreenFilters";
import ScreenTable, {
  leverageTone,
  money,
  multiple,
  type Column,
} from "@/components/screen/ScreenTable";
import {
  EMPTY_FILTERS,
  fromSearchParams,
  toQuery,
  toSearchParams,
  withoutChip,
  type ScreenFilterState,
} from "@/components/screen/filterSpec";
import { buildRecord } from "@/components/screen/screenSource";
import CopyLink from "@/components/ui/CopyLink";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import { getScreen, getScreenFacets } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { ScreenResponse, ScreenRow } from "@/lib/types";

const PAGE_SIZE = 50;

/** A figure that opens its own source record when clicked. */
function Figure({
  row,
  metric,
  ctx,
  text,
  tone,
}: {
  row: ScreenRow;
  metric: Parameters<typeof buildRecord>[1];
  ctx: { openSource: (r: ReturnType<typeof buildRecord>) => void };
  text: string;
  tone?: string;
}) {
  const undisclosed = text === "—" || text === "not disclosed";
  return (
    <button
      type="button"
      onClick={() => ctx.openSource(buildRecord(row, metric))}
      title="Show where this figure came from"
      className={`figure press-tint hit-target inspectable w-full text-right ${
        tone ?? (undisclosed ? "!text-ink-muted !font-normal" : "")
      }`}
    >
      {text}
    </button>
  );
}

const COLUMNS: Column[] = [
  {
    key: "company",
    label: "Company",
    sortKey: "entity_name",
    align: "left",
    render: (row) => (
      <div className="flex items-baseline gap-2">
        {row.ticker ? (
          <Link
            href={`/company/${encodeURIComponent(row.ticker)}/dashboard`}
            className="font-mono text-[0.8125rem] font-semibold text-link underline-offset-2 hover:underline"
          >
            {row.ticker}
          </Link>
        ) : (
          <span className="font-mono text-[0.8125rem] text-ink-muted">—</span>
        )}
        <span
          title={row.name}
          className="max-w-[11rem] truncate text-[0.8125rem] font-medium text-ink"
        >
          {row.name}
        </span>
        {row.quality_flag && (
          <span
            title={row.quality_note ?? undefined}
            className="whitespace-nowrap border border-assumption bg-assumption-soft px-1 font-mono text-[0.625rem] font-semibold leading-4 text-assumption"
          >
            one-off gain
          </span>
        )}
      </div>
    ),
  },
  {
    key: "revenue",
    label: "Revenue",
    sortKey: "revenue",
    align: "right",
    domain: "size",
    render: (row, ctx) => (
      <Figure row={row} metric="revenue" ctx={ctx} text={money(row.revenue)} />
    ),
  },
  {
    key: "ebitda",
    label: "EBITDA",
    sortKey: "ebitda",
    align: "right",
    domain: "size",
    render: (row, ctx) => (
      <Figure
        row={row}
        metric="ebitda"
        ctx={ctx}
        text={row.ebitda === null ? "not disclosed" : money(row.ebitda)}
      />
    ),
  },
  {
    key: "margin",
    label: "Margin",
    sortKey: "ebitda_margin",
    align: "right",
    domain: "profit",
    render: (row) => (
      <span className="figure-muted">
        {row.ebitda_margin === null ? "—" : fmtPct(row.ebitda_margin)}
      </span>
    ),
  },
  {
    key: "leverage",
    // "Leverage" is what the desk calls it, and the full ratio name cost 185px
    // of a 700px table. The source record spells out the arithmetic.
    label: "Leverage",
    sortKey: "leverage",
    align: "right",
    domain: "balance",
    render: (row, ctx) => (
      <Figure
        row={row}
        metric="leverage"
        ctx={ctx}
        text={multiple(row.leverage)}
        // Utilities beat the .figure component class by layer order, so the
        // band colour applies without an importance override.
        tone={
          row.leverage === null || row.leverage === undefined
            ? undefined
            : leverageTone(row.leverage)
        }
      />
    ),
  },
  {
    key: "sector",
    label: "Sector",
    sortKey: "sector",
    align: "left",
    domain: "classify",
    render: (row) => (
      <span
        title={row.sector ?? undefined}
        className="block max-w-[8rem] truncate text-[0.8125rem] text-ink-secondary"
      >
        {row.sector ?? "—"}
      </span>
    ),
  },
  {
    key: "period",
    label: "Period",
    align: "right",
    domain: "classify",
    render: (row) => (
      <span className="font-mono text-[0.6875rem] font-medium text-ink-muted">
        {row.period.replace("CY", "FY")}
      </span>
    ),
  },
];

function fmtPct(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

export default function ScreenPage() {
  const [filters, setFilters] = useState<ScreenFilterState>(EMPTY_FILTERS);
  const [sort, setSort] = useState("revenue");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ScreenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [urlApplied, setUrlApplied] = useState(false);

  const facets = useApi(() => getScreenFacets(), []);

  const query = useMemo(
    () => ({ ...toQuery(filters), sort, direction, limit: PAGE_SIZE, offset }),
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

  // Debounced so typing in a range box does not fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(run, 250);
    return () => clearTimeout(timer);
  }, [run]);

  // Filters carried in the URL, applied once after hydration. Read from
  // window rather than useSearchParams, which would force this static route
  // into a Suspense boundary at build time.
  useEffect(() => {
    const fromUrl = fromSearchParams(window.location.search);
    if (fromUrl) setFilters(fromUrl);
    setUrlApplied(true);
  }, []);

  // Keep the address bar in step so any screen can be linked or shared.
  //
  // Gated on the read above having happened. Without the gate this effect
  // runs on the first render with empty filters and overwrites the very
  // parameters the page was opened with, so every shared link arrives blank.
  useEffect(() => {
    if (!urlApplied) return;
    const qs = toSearchParams(filters);
    const next = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, "", next);
  }, [filters, urlApplied]);

  useEffect(() => setOffset(0), [filters, sort, direction]);

  const onSort = (key: string) => {
    if (key === sort) {
      setDirection((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSort(key);
      setDirection(key === "entity_name" || key === "sector" ? "asc" : "desc");
    }
  };

  const coverage = data?.coverage;
  const indexEmpty = coverage !== undefined && coverage.total === 0;
  const shown = data ? data.rows.length : 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto w-full max-w-[100rem] px-4 py-8 sm:px-6">
      <header className="border-b-2 border-line-strong pb-5">
        <h1 className="text-[1.5rem] font-semibold text-ink">Deal screen</h1>
        <p className="mt-1 max-w-[70ch] text-[0.9375rem] leading-snug text-ink-secondary">
          Filter every US-listed filer on figures taken from their own SEC
          filings. Revenue, operating income and the balance sheet are as
          reported. EBITDA is calculated as operating income plus depreciation
          and amortisation, and is left blank where a company does not report
          D&amp;A separately.
        </p>
        {coverage && !indexEmpty && (
          <p className="mt-3 font-mono text-[0.6875rem] font-medium leading-relaxed text-ink-muted">
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

      <div className="mt-6 grid gap-8 lg:grid-cols-[16rem_1fr]">
        <aside className="lg:border-r lg:border-line lg:pr-6">
          <ScreenFilters
            value={filters}
            onChange={setFilters}
            facets={facets.data ?? null}
            onReset={() => setFilters(EMPTY_FILTERS)}
          />
        </aside>

        <section className="min-w-0">
          {indexEmpty ? (
            <p className="border border-line-strong bg-surface px-4 py-8 text-center text-[0.9375rem] text-ink-secondary">
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
              <AppliedFilters
                state={filters}
                onRemove={(id) => setFilters((f) => withoutChip(f, id))}
                onClear={() => setFilters(EMPTY_FILTERS)}
              />

              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 pb-2">
                <p className="text-[0.9375rem] text-ink">
                  <span className="font-mono font-semibold tabular-nums">
                    {data.total.toLocaleString()}
                  </span>{" "}
                  {data.total === 1 ? "company" : "companies"} match
                </p>
                <span className="flex items-center gap-3">
                  {/* The filters live in the address bar, which is the whole
                      "every screen is a link" claim. Until now there was no
                      way to act on it from the page. */}
                  <CopyLink label="Copy this screen" />
                  <p className="label-mono">{data.source}</p>
                </span>
              </div>

              <ScreenTable
                rows={data.rows}
                columns={COLUMNS}
                sort={sort}
                direction={direction}
                onSort={onSort}
              />

              <p className="mt-3 max-w-[80ch] text-[0.75rem] leading-relaxed text-ink-secondary">
                {data.note}
              </p>

              {data.total > PAGE_SIZE && (
                <div className="mt-5 flex items-center justify-between border-t border-line pt-3">
                  <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                    className="text-[0.8125rem] font-medium text-link disabled:cursor-not-allowed disabled:text-ink-muted"
                  >
                    ← Previous
                  </button>
                  <span className="font-mono text-[0.6875rem] font-medium text-ink-muted">
                    {page} of {pages}
                  </span>
                  <button
                    type="button"
                    disabled={offset + shown >= data.total}
                    onClick={() => setOffset((o) => o + PAGE_SIZE)}
                    className="text-[0.8125rem] font-medium text-link disabled:cursor-not-allowed disabled:text-ink-muted"
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
