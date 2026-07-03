"use client";

// Analysts (route /company/[ticker]/analysts): the Bloomberg ANR / EE / ERN
// view — sell-side ratings, price targets and forward estimates. Coverage is
// thin outside large-cap US names, so missing figures show honest "unavailable"
// states rather than blanks, per the app's traceability contract.

import { useCompany } from "@/components/company/CompanyContext";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import WarningList from "@/components/ui/WarningList";
import { getMarketStats } from "@/lib/api";
import {
  fmtDate,
  fmtMultiple,
  fmtPercent,
  fmtPerShare,
} from "@/lib/format";
import { useApi } from "@/lib/hooks";

/** Rating badge coloured by direction: buy → positive, sell → negative. */
function RatingBadge({ rating }: { rating: string }) {
  const key = rating.toLowerCase();
  const tone = /buy|outperform|overweight/.test(key)
    ? "bg-accent-soft text-positive-text"
    : /sell|underperform|underweight/.test(key)
      ? "bg-negative/10 text-negative-text"
      : "bg-warn-soft text-warn-text";
  const label = rating
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-medium ${tone}`}
    >
      {label}
    </span>
  );
}

/** Low — mean — high target range with a current-price marker. */
function TargetRange({
  low,
  mean,
  high,
  current,
  currency,
}: {
  low: number;
  mean: number;
  high: number;
  current: number | null;
  currency: string | null;
}) {
  const lo = Math.min(low, current ?? low);
  const hi = Math.max(high, current ?? high);
  const span = hi - lo || 1;
  const pos = (v: number) => `${((v - lo) / span) * 100}%`;
  return (
    <div className="pt-6">
      <div className="relative h-1.5 rounded-full bg-surface-sunken">
        <div
          className="absolute h-1.5 rounded-full bg-brand/25"
          style={{ left: pos(low), right: `${100 - (high - lo) / span * 100}%` }}
        />
        {/* mean target */}
        <div
          className="absolute -top-1 h-3.5 w-3.5 -translate-x-1/2 rounded-full border-2 border-surface bg-brand"
          style={{ left: pos(mean) }}
          title={`Mean target ${fmtPerShare(mean, currency)}`}
        />
        {/* current price */}
        {current !== null && (
          <div
            className="absolute -top-1 h-3.5 w-3.5 -translate-x-1/2 rounded-full border-2 border-surface bg-ink"
            style={{ left: pos(current) }}
            title={`Current ${fmtPerShare(current, currency)}`}
          />
        )}
      </div>
      <div className="mt-2 flex justify-between text-xs text-ink-muted">
        <span>Low {fmtPerShare(low, currency)}</span>
        <span>High {fmtPerShare(high, currency)}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-brand" />
          Mean target {fmtPerShare(mean, currency)}
        </span>
        {current !== null && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-ink" />
            Current {fmtPerShare(current, currency)}
          </span>
        )}
      </div>
    </div>
  );
}

function Upside({ value }: { value: number }) {
  const cls =
    value > 0 ? "text-positive-text" : value < 0 ? "text-negative-text" : "text-ink";
  const sign = value > 0 ? "+" : "";
  return (
    <span className={`tabular-nums ${cls}`}>
      {sign}
      {fmtPercent(value)}
    </span>
  );
}

export default function AnalystsPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const currency = profile.currency ?? null;
  const { data, error, loading, retry } = useApi(
    () => getMarketStats(ticker),
    [ticker],
  );

  const header = (
    <SectionHeader
      variant="page"
      as="h2"
      title="Analysts"
      subtitle="Sell-side ratings, price targets and forward estimates. Coverage is aggregated from public sources and is thin outside large-cap US names."
    />
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }
  if (error !== null || data === null) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          message={
            error?.message ?? `Market statistics are unavailable for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const a = data.analysts;
  const hasCoverage = a.target_mean !== null || a.analyst_count !== null;
  const hasEstimates =
    a.forward_pe !== null ||
    a.forward_eps !== null ||
    a.earnings_growth !== null ||
    a.revenue_growth !== null ||
    a.next_earnings_date !== null;

  return (
    <div className="fade-in space-y-6">
      {header}
      <WarningList warnings={data.warnings} />

      <section>
        <SectionHeader title="Price target" subtitle="Consensus of covering analysts" />
        <Card>
          {a.target_mean !== null &&
          a.target_low !== null &&
          a.target_high !== null ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="Mean target"
                  value={fmtPerShare(a.target_mean, currency)}
                />
                <StatCard
                  label="Current price"
                  value={fmtPerShare(a.current_price, currency)}
                />
                <StatCard
                  label="Implied upside"
                  value={
                    a.implied_upside !== null ? (
                      <Upside value={a.implied_upside} />
                    ) : (
                      "—"
                    )
                  }
                  sub="Mean target vs current price"
                />
                <StatCard
                  label="Rating"
                  value={
                    a.rating ? <RatingBadge rating={a.rating} /> : "—"
                  }
                  sub={
                    a.analyst_count !== null
                      ? `${a.analyst_count} analyst${a.analyst_count === 1 ? "" : "s"}${
                          a.rating_score !== null
                            ? ` · ${a.rating_score.toFixed(1)} / 5`
                            : ""
                        }`
                      : undefined
                  }
                />
              </div>
              <TargetRange
                low={a.target_low}
                mean={a.target_mean}
                high={a.target_high}
                current={a.current_price}
                currency={currency}
              />
            </>
          ) : (
            <p className="text-sm text-ink-secondary">
              No sell-side price target is available for {ticker} from the free
              data source. This is common outside large-cap US names, where
              broker research is not publicly aggregated.
            </p>
          )}
        </Card>
      </section>

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Estimates"
          subtitle="Forward-looking figures; verify against company guidance"
        />
        <Card>
          {hasEstimates ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard label="Forward P/E" value={fmtMultiple(a.forward_pe)} />
              <StatCard
                label="Forward EPS"
                value={fmtPerShare(a.forward_eps, currency)}
              />
              <StatCard
                label="Trailing EPS"
                value={fmtPerShare(a.trailing_eps, currency)}
              />
              <StatCard
                label="Expected earnings growth"
                value={fmtPercent(a.earnings_growth)}
              />
              <StatCard
                label="Expected revenue growth"
                value={fmtPercent(a.revenue_growth)}
              />
              <StatCard
                label="Next earnings date"
                value={fmtDate(a.next_earnings_date)}
              />
            </div>
          ) : (
            <p className="text-sm text-ink-secondary">
              Forward consensus estimates are unavailable for {ticker}. Forward
              estimates are the classic paid dataset; free coverage exists only
              for large-cap US names.
            </p>
          )}
        </Card>
      </section>

      {!hasCoverage && (
        <p className="text-xs text-ink-muted">
          Aggregated from Yahoo Finance ({fmtDate(data.as_of)}). Analyst data is
          not sourced from filings and should be treated as indicative.
        </p>
      )}
      <Disclaimer />
    </div>
  );
}
