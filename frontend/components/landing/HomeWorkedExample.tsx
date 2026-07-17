"use client";

// One worked example on the landing page, presented as a single annotated
// research sheet (DESIGN.md). Every figure is drawn LIVE from the same API the
// rest of the tool uses: this is real output, not a mock-up. Marginal
// annotations carry provenance the way model notes would.

import Link from "next/link";
import { getFinancials, getProfile, getScore } from "@/lib/api";
import { fmtCurrency, fmtDate, fmtMultiple, fmtPercent } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const TICKER = "AAPL";

const LINKS = [
  { label: "Open dashboard", href: `/company/${TICKER}/dashboard` },
  { label: "Inspect financials", href: `/company/${TICKER}/financials` },
  { label: "Review LBO assumptions", href: `/company/${TICKER}/lbo` },
  { label: "Read the memo", href: `/company/${TICKER}/memo` },
];

/** One figure in the aligned strip. No background, separated by a rule. */
function Figure({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="border-t border-line py-3 sm:border-t-0 sm:border-l sm:pl-4 sm:pt-0 sm:first:border-l-0 sm:first:pl-0">
      <div className="text-[11px] text-ink-muted">{label}</div>
      <div className="mt-1 font-mono text-[0.9375rem] tabular-nums text-ink">
        {value}
      </div>
      {note && (
        <div className="mt-1 font-mono text-[10px] leading-tight text-ink-muted">
          {note}
        </div>
      )}
    </div>
  );
}

/** Operating-margin bars. Plain, one accent series, direct labels, no gradient. */
function MarginFigure({
  points,
}: {
  points: { year: number; margin: number }[];
}) {
  if (points.length < 2) return null;
  const max = Math.max(...points.map((p) => p.margin));
  const min = Math.min(...points.map((p) => p.margin), 0);
  const span = max - min || 1;
  const H = 120;
  const barW = 100 / points.length;

  return (
    <div>
      <svg
        viewBox={`0 0 100 ${H}`}
        preserveAspectRatio="none"
        className="h-[120px] w-full"
        role="img"
        aria-label={`Operating margin by fiscal year, ${points
          .map((p) => `FY${p.year} ${(p.margin * 100).toFixed(1)}%`)
          .join(", ")}`}
      >
        {points.map((p, i) => {
          const h = ((p.margin - min) / span) * (H - 18);
          return (
            <rect
              key={p.year}
              x={i * barW + barW * 0.2}
              y={H - h}
              width={barW * 0.6}
              height={Math.max(h, 1)}
              fill="var(--accent)"
            />
          );
        })}
      </svg>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] tabular-nums text-ink-muted">
        {points.map((p) => (
          <span key={p.year}>FY{String(p.year).slice(-2)}</span>
        ))}
      </div>
    </div>
  );
}

export default function HomeWorkedExample() {
  const profile = useApi(() => getProfile(TICKER), [TICKER]);
  const score = useApi(() => getScore(TICKER), [TICKER]);
  const financials = useApi(() => getFinancials(TICKER), [TICKER]);

  const p = profile.data;
  const years = financials.data?.years ?? [];
  const latest = years.length ? years[years.length - 1] : null;

  const marginPoints = years
    .filter((y) => y.operating_income != null && y.revenue)
    .map((y) => ({
      year: y.fiscal_year,
      margin: (y.operating_income as number) / (y.revenue as number),
    }));

  const opMargin =
    latest?.operating_income != null && latest?.revenue
      ? latest.operating_income / latest.revenue
      : null;
  const evEbitda =
    p?.enterprise_value != null && p?.ebitda ? p.enterprise_value / p.ebitda : null;
  const netDebt = p?.net_debt ?? null;
  const netLabel = netDebt != null && netDebt < 0 ? "Net cash" : "Net debt";

  const first = marginPoints[0];
  const last = marginPoints[marginPoints.length - 1];

  return (
    <section className="mt-20 border-t border-line pt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="text-[1.375rem] font-medium text-ink">
          A quick look at Apple
        </h2>
        <p className="font-mono text-[11px] text-ink-muted">
          {p
            ? `${p.ticker} · ${p.exchange ?? ""}${
                latest?.period_end ? ` · reporting date ${fmtDate(latest.period_end)}` : ""
              }`
            : "loading live figures"}
        </p>
      </div>

      {/* Aligned figure strip on a faint paper surface. No card per metric. */}
      <div className="mt-5 bg-surface px-4 py-4 sm:px-5">
        {profile.loading ? (
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i}>
                <div className="skeleton h-2.5 w-16" />
                <div className="skeleton mt-2 h-4 w-20" />
              </div>
            ))}
          </div>
        ) : p ? (
          <div className="grid sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-6">
            <Figure
              label="Market cap"
              value={fmtCurrency(p.market_cap, p.currency)}
              note="From market data"
            />
            <Figure
              label="Enterprise value"
              value={fmtCurrency(p.enterprise_value, p.currency)}
              note="Calculated from cash and debt"
            />
            <Figure
              label={`Revenue (FY${p.latest_fiscal_year ?? ""})`}
              value={fmtCurrency(p.revenue, p.currency)}
              note="From the annual filing"
            />
            <Figure
              label="Operating margin"
              value={fmtPercent(opMargin)}
              note="Calculated: operating income / revenue"
            />
            <Figure
              label={netLabel}
              value={
                netDebt == null
                  ? fmtCurrency(null)
                  : fmtCurrency(Math.abs(netDebt), p.currency)
              }
              note="Calculated from reported cash and debt"
            />
            <Figure
              label="EV / EBITDA"
              value={fmtMultiple(evEbitda)}
              note="Calculated at the current price"
            />
          </div>
        ) : (
          <p className="text-[0.875rem] text-ink-muted">
            Live figures are not loading right now. The links below still open
            the real pages.
          </p>
        )}
      </div>

      {/* Figure: question, subtitle, chart, caption, source. */}
      {marginPoints.length >= 2 && first && last && (
        <div className="mt-8 grid grid-cols-12 gap-x-6 gap-y-6">
          <div className="col-span-12 lg:col-span-7">
            <h3 className="text-[0.9375rem] font-medium text-ink">
              How has operating margin changed?
            </h3>
            <p className="mt-0.5 text-[0.8125rem] text-ink-muted">
              Reported operating income over reported revenue, by fiscal year.
            </p>
            <div className="mt-4">
              <MarginFigure points={marginPoints} />
            </div>
            <p className="mt-3 max-w-[62ch] text-[0.8125rem] leading-snug text-ink-secondary">
              Operating margin moved from {fmtPercent(first.margin)} in FY
              {first.year} to {fmtPercent(last.margin)} in FY{last.year}.
            </p>
            <p className="mt-1 font-mono text-[10px] text-ink-muted">
              Source: company annual filings via SEC EDGAR · calculation shown
              above
            </p>
          </div>

          {/* Short editorial observation, in the authored face. */}
          <div className="col-span-12 lg:col-span-5">
            <p className="font-mono text-[11px] text-ink-muted">Observation</p>
            <p className="mt-2 font-display text-[1.0625rem] leading-[1.6] text-ink-secondary">
              Apple is not an obvious conventional LBO candidate: its scale and
              entry valuation work against a deal. It is still a useful example
              for testing the model, reading cash generation, and seeing how the
              screen weighs strong operating quality against difficult
              transaction economics.
            </p>
            {score.data && (
              <p className="mt-4 font-mono text-[11px] text-ink-muted">
                Screening score{" "}
                <span className="text-ink">
                  {score.data.total.toFixed(0)} / 100
                </span>{" "}
                · {score.data.rating} · a screening aid, not a recommendation
              </p>
            )}
          </div>
        </div>
      )}

      <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 border-t border-line pt-4">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="text-[0.875rem] text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover hover:decoration-link"
          >
            {l.label}
          </Link>
        ))}
      </div>

      {p?.data_as_of && (
        <p className="mt-3 font-mono text-[10px] text-ink-muted">
          Market data as of {fmtDate(p.data_as_of)} · financial data from the FY
          {p.latest_fiscal_year} annual filing · {p.data_source}
        </p>
      )}
    </section>
  );
}
