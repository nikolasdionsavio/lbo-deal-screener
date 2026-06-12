"use client";

// Company news page (BUILD_SPEC section 19.8): story cards from
// GET /api/companies/{ticker}/news with range chips (1d/3d/1w/1m/6m,
// client-side filter on published_at, default 1w), a per-range story count,
// an oldest-available note when the source window is shorter than the
// selected range, and a manual refresh (limit=60) with the last-updated
// time. In mock mode the backend returns an empty list with a live-only
// warning, rendered as the empty state.

import { useEffect, useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import NewsList from "@/components/news/NewsList";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getNews } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { NewsItem } from "@/lib/types";

const DAY_MS = 86_400_000;

const RANGES = [
  { key: "1d", label: "1d", days: 1 },
  { key: "3d", label: "3d", days: 3 },
  { key: "1w", label: "1w", days: 7 },
  { key: "1m", label: "1m", days: 30 },
  { key: "6m", label: "6m", days: 182 },
] as const;

type RangeKey = (typeof RANGES)[number]["key"];

function publishedMs(item: NewsItem): number | null {
  const ms = Date.parse(item.published_at);
  return Number.isNaN(ms) ? null : ms;
}

function RangeChips({
  active,
  onChange,
  count,
}: {
  active: RangeKey;
  onChange: (key: RangeKey) => void;
  count: number;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div
        role="group"
        aria-label="Time range"
        className="flex items-center gap-1.5"
      >
        {RANGES.map((range) => {
          const selected = range.key === active;
          return (
            <button
              key={range.key}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(range.key)}
              className={`rounded-full px-3 py-1 text-xs font-medium tabular-nums transition-colors duration-150 ${
                selected
                  ? "bg-ink text-surface"
                  : "border border-line text-ink-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              {range.label}
            </button>
          );
        })}
      </div>
      <span className="text-xs tabular-nums text-ink-muted">
        {count} {count === 1 ? "story" : "stories"}
      </span>
    </div>
  );
}

function RefreshIcon() {
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
      <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9" />
      <path d="M13.5 1.75V4.5h-2.75" />
    </svg>
  );
}

export default function NewsPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  // Initial load uses the backend default (30); manual refresh asks for the
  // full window (limit=60) so the wider ranges have depth to filter.
  const [limit, setLimit] = useState<number | undefined>(undefined);
  const [range, setRange] = useState<RangeKey>("1w");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const { data, error, loading, retry } = useApi(
    () => getNews(ticker, limit),
    [ticker, limit],
  );

  useEffect(() => {
    if (data !== null) setUpdatedAt(new Date());
  }, [data]);

  function refresh() {
    if (limit === 60) retry();
    else setLimit(60);
  }

  const header = (
    <SectionHeader
      variant="page"
      as="h2"
      title="News"
      subtitle={data !== null ? `Provider: ${data.provider}` : undefined}
      actions={
        <div className="flex items-center gap-3">
          {updatedAt !== null && (
            <span className="text-xs tabular-nums text-ink-muted">
              Updated{" "}
              {updatedAt.toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            className="btn btn-secondary gap-1.5 px-3 py-1.5 text-xs"
          >
            <RefreshIcon />
            {loading && data !== null ? "Refreshing" : "Refresh"}
          </button>
        </div>
      }
    />
  );

  if (loading && data === null) {
    return (
      <div>
        {header}
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        {header}
        <ErrorState
          message={
            error !== null ? error.message : `Could not load news for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const rangeDef = RANGES.find((r) => r.key === range) ?? RANGES[2];
  const now = Date.now();
  const cutoff = now - rangeDef.days * DAY_MS;
  // Items with unparseable timestamps stay visible rather than vanishing.
  const filtered = data.items.filter((item) => {
    const ms = publishedMs(item);
    return ms === null || ms >= cutoff;
  });

  // Note when the provider's window is shallower than the selected range:
  // the oldest available story is younger than the range start.
  const stamps = data.items
    .map(publishedMs)
    .filter((ms): ms is number => ms !== null);
  const oldest = stamps.length > 0 ? Math.min(...stamps) : null;
  const coverageDays =
    oldest !== null ? Math.max(1, Math.ceil((now - oldest) / DAY_MS)) : null;
  const shallow =
    coverageDays !== null &&
    data.items.length > 0 &&
    coverageDays < rangeDef.days;

  return (
    <div>
      <section>
        {header}
        {data.items.length === 0 ? (
          <Card>
            <p className="text-sm text-warn-text">
              {data.warnings.length > 0
                ? data.warnings.join(" ")
                : `No recent news is available for ${ticker}.`}
            </p>
          </Card>
        ) : (
          <>
            <WarningList warnings={data.warnings} className="mb-4" />
            <RangeChips
              active={range}
              onChange={setRange}
              count={filtered.length}
            />
            {shallow && (
              <p className="mt-2 text-xs text-ink-muted">
                Source window covers ~{coverageDays}{" "}
                {coverageDays === 1 ? "day" : "days"}; older stories are not
                available from the provider.
              </p>
            )}
            {filtered.length === 0 ? (
              <Card className="mt-4">
                <p className="text-sm text-ink-muted">
                  No stories in the last {rangeDef.label}. The loaded feed
                  holds {data.items.length}{" "}
                  {data.items.length === 1 ? "story" : "stories"}; widen the
                  range to see them.
                </p>
              </Card>
            ) : (
              <div className="mt-4">
                <NewsList items={filtered} />
              </div>
            )}
          </>
        )}
      </section>

      <Disclaimer />
    </div>
  );
}
