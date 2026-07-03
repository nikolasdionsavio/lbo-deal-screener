"use client";

// Ownership (route /company/[ticker]/ownership): the Bloomberg HDS view —
// institutional / insider ownership and short interest. This is a strength of
// free data for US filers (SEC 13F and Forms 3-5, wrapped by Yahoo); non-US
// names have no equivalent, so figures degrade to honest "unavailable" states.

import { useCompany } from "@/components/company/CompanyContext";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import WarningList from "@/components/ui/WarningList";
import { getMarketStats } from "@/lib/api";
import { fmtDate, fmtDays, fmtPercent, fmtShareCount } from "@/lib/format";
import { useApi } from "@/lib/hooks";

export default function OwnershipPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const { data, error, loading, retry } = useApi(
    () => getMarketStats(ticker),
    [ticker],
  );

  const header = (
    <SectionHeader
      variant="page"
      as="h2"
      title="Ownership"
      subtitle="Institutional and insider ownership and short interest. Sourced from SEC 13F and insider filings for US names; unavailable elsewhere."
    />
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <LoadingState lines={6} />
        <Disclaimer />
      </div>
    );
  }
  if (error !== null || data === null) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          message={error?.message ?? `Ownership data is unavailable for ${ticker}.`}
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const o = data.ownership;
  const hasOwnership =
    o.held_pct_institutions !== null || o.held_pct_insiders !== null;
  const hasShort =
    o.shares_short !== null ||
    o.short_pct_of_float !== null ||
    o.short_ratio !== null;

  return (
    <div className="fade-in space-y-6">
      {header}
      <WarningList warnings={data.warnings} />

      <section>
        <SectionHeader
          title="Ownership structure"
          subtitle="Share of the company held by each holder type"
        />
        <Card>
          {hasOwnership ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Institutions"
                value={fmtPercent(o.held_pct_institutions)}
                sub="Held by 13F filers"
              />
              <StatCard
                label="Insiders"
                value={fmtPercent(o.held_pct_insiders)}
                sub="Held by officers and directors"
              />
              <StatCard
                label="Public float"
                value={fmtShareCount(o.float_shares)}
                sub="Shares available to trade"
              />
              <StatCard
                label="Shares outstanding"
                value={fmtShareCount(o.shares_outstanding)}
              />
            </div>
          ) : (
            <p className="text-sm text-ink-secondary">
              Ownership breakdown is unavailable for {ticker}. Institutional and
              insider holdings are reported to the SEC by US filers; there is no
              free equivalent for non-US listings.
            </p>
          )}
        </Card>
      </section>

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Short interest"
          subtitle="Bearish positioning and how long it would take to cover"
        />
        <Card>
          {hasShort ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Shares short"
                value={fmtShareCount(o.shares_short)}
              />
              <StatCard
                label="Short % of float"
                value={fmtPercent(o.short_pct_of_float)}
              />
              <StatCard
                label="Short % of shares out"
                value={fmtPercent(o.short_pct_shares_out)}
              />
              <StatCard
                label="Days to cover"
                value={fmtDays(o.short_ratio)}
                sub="Short interest ÷ average volume"
              />
            </div>
          ) : (
            <p className="text-sm text-ink-secondary">
              Short-interest data is unavailable for {ticker}.
            </p>
          )}
        </Card>
      </section>

      <p className="text-xs text-ink-muted">
        Aggregated from Yahoo Finance as of {fmtDate(data.as_of)}.
      </p>
      <Disclaimer />
    </div>
  );
}
