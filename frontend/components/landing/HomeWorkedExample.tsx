"use client";

// One worked example on the landing page, drawn LIVE from the same API the rest
// of the tool uses (profile + screening score for Apple). Not a mock-up: the
// figures are whatever the tool currently computes, each links into the real
// page it came from. Degrades to the reasoning + links if the API is slow.

import Link from "next/link";
import { getProfile, getScore } from "@/lib/api";
import { fmtCurrency, fmtMultiple, fmtPercent, fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const TICKER = "AAPL";

const LINKS = [
  { label: "Open dashboard", href: `/company/${TICKER}/dashboard` },
  { label: "Inspect financials", href: `/company/${TICKER}/financials` },
  { label: "Review LBO assumptions", href: `/company/${TICKER}/lbo` },
  { label: "Read the memo", href: `/company/${TICKER}/memo` },
];

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-line py-2.5">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-0.5 font-mono text-[0.95rem] text-ink">{value}</dd>
    </div>
  );
}

export default function HomeWorkedExample() {
  const profile = useApi(() => getProfile(TICKER), [TICKER]);
  const score = useApi(() => getScore(TICKER), [TICKER]);

  const p = profile.data;
  const ebitdaMargin =
    p && p.ebitda != null && p.revenue ? p.ebitda / p.revenue : null;
  const evEbitda =
    p && p.enterprise_value != null && p.ebitda ? p.enterprise_value / p.ebitda : null;
  const netDebt = p?.net_debt ?? null;
  const netDebtLabel = netDebt != null && netDebt < 0 ? "Net cash" : "Net debt";
  const netDebtValue =
    netDebt == null
      ? fmtCurrency(null)
      : fmtCurrency(Math.abs(netDebt), p?.currency);

  return (
    <section className="mt-16">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-lg font-semibold text-ink">A quick look at Apple</h2>
        <span className="font-mono text-xs text-ink-muted">
          {p ? `${p.ticker} · ${p.exchange ?? ""} · live` : "loading live figures"}
        </span>
      </div>

      {profile.loading ? (
        <div className="mt-4 grid gap-x-8 gap-y-1 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="border-t border-line py-2.5">
              <div className="skeleton h-3 w-20" />
              <div className="skeleton mt-1.5 h-4 w-24" />
            </div>
          ))}
        </div>
      ) : p ? (
        <dl className="mt-4 grid gap-x-8 sm:grid-cols-3">
          <Figure
            label={`Revenue (FY${p.latest_fiscal_year ?? ""})`}
            value={fmtCurrency(p.revenue, p.currency)}
          />
          <Figure label="EBITDA margin" value={fmtPercent(ebitdaMargin)} />
          <Figure label={netDebtLabel} value={netDebtValue} />
          <Figure label="Current EV / EBITDA" value={fmtMultiple(evEbitda)} />
          <Figure label="Enterprise value" value={fmtCurrency(p.enterprise_value, p.currency)} />
          <Figure
            label="Screening score"
            value={
              score.data ? `${score.data.total.toFixed(0)} / 100 · ${score.data.rating}` : "—"
            }
          />
        </dl>
      ) : (
        <p className="mt-4 border-t border-line py-3 text-sm text-ink-muted">
          Live figures are not loading right now. The reasoning and links below
          still open the real pages.
        </p>
      )}

      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-secondary">
        Apple is not an obvious conventional LBO candidate: its scale and entry
        valuation work against a deal. It is still a useful example for testing
        the model, reading cash generation, and seeing how the screen weighs
        strong operating quality against difficult transaction economics.
      </p>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="text-sm text-brand-text underline decoration-line-strong underline-offset-2 transition-colors hover:decoration-brand"
          >
            {l.label}
          </Link>
        ))}
      </div>

      {p?.data_as_of && (
        <p className="mt-3 font-mono text-xs text-ink-muted">
          Fundamentals as of {fmtDate(p.data_as_of)} · {p.data_source}
        </p>
      )}
    </section>
  );
}
