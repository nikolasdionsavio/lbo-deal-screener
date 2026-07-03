"use client";

// Dividends (route /company/[ticker]/dividends): the Bloomberg DVD view —
// dividend rate, yield, payout, five-year average and ex-date. Clean free data
// (Yahoo). Non-payers get a clear "does not pay a dividend" state rather than a
// grid of dashes.

import { useCompany } from "@/components/company/CompanyContext";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import WarningList from "@/components/ui/WarningList";
import { getMarketStats } from "@/lib/api";
import { fmtDate, fmtPercent, fmtPerShare } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function DividendsPage() {
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
      title="Dividends"
      subtitle="Dividend rate, yield, payout and ex-date. A capital-return read alongside the LBO and cash-flow analysis."
    />
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <LoadingState lines={5} />
        <Disclaimer />
      </div>
    );
  }
  if (error !== null || data === null) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          message={error?.message ?? `Dividend data is unavailable for ${ticker}.`}
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const d = data.dividends;
  const paysDividend =
    d.dividend_rate !== null || d.dividend_yield !== null;

  return (
    <div className="fade-in space-y-6">
      {header}
      <WarningList warnings={data.warnings} />

      <section>
        <Card>
          {paysDividend ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <StatCard
                  label="Dividend yield"
                  value={fmtPercent(d.dividend_yield, { digits: 2 })}
                  sub="Annual dividend ÷ current price"
                />
                <StatCard
                  label="Annual rate"
                  value={fmtPerShare(d.dividend_rate, currency)}
                  sub="Per share, trailing twelve months"
                />
                <StatCard
                  label="Payout ratio"
                  value={fmtPercent(d.payout_ratio)}
                  sub="Dividends ÷ earnings"
                />
                <StatCard
                  label="5-year average yield"
                  value={fmtPercent(d.five_year_avg_yield, { digits: 2 })}
                />
                <StatCard
                  label="Ex-dividend date"
                  value={fmtDate(d.ex_dividend_date)}
                />
                <StatCard
                  label="Last dividend"
                  value={fmtPerShare(d.last_dividend_value, currency)}
                  sub="Most recent per-share payment"
                />
              </div>
              <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
                A high payout ratio leaves less free cash flow to service
                acquisition debt; read alongside the LBO and cash-conversion
                analysis. Aggregated from Yahoo Finance as of{" "}
                {fmtDate(data.as_of)}.
              </p>
            </>
          ) : (
            <>
              <p className="text-sm text-ink-secondary">
                {ticker} does not currently pay a dividend.
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                Retaining all earnings is typical for growth companies; capital
                is returned through reinvestment or buybacks instead. Payout
                history, when it exists, appears on the Financials page.
              </p>
            </>
          )}
        </Card>
      </section>

      <Disclaimer />
    </div>
  );
}
