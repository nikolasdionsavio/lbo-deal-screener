"use client";

// Company dashboard: StatCard grid over every profile field from
// BUILD_SPEC section 2 / section 12 (profile endpoint). No extra fetch —
// data comes from the layout's CompanyContext.

import type { ReactNode } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import TradingViewChart from "@/components/company/TradingViewChart";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import { fmtCurrency } from "@/lib/format";

const NOT_AVAILABLE = (
  <span title="Not available" className="text-slate-400">
    —
  </span>
);

function text(value: string | null): ReactNode {
  return value === null || value === "" ? NOT_AVAILABLE : value;
}

export default function DashboardPage() {
  const { profile } = useCompany();
  const currency = profile.currency ?? null;

  function money(value: number | null): ReactNode {
    return value === null ? NOT_AVAILABLE : fmtCurrency(value, currency);
  }

  const fiscalYearLabel =
    profile.latest_fiscal_year === null
      ? NOT_AVAILABLE
      : `FY${profile.latest_fiscal_year}`;

  return (
    <div>
      <section>
        <SectionHeader title="Company" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Name"
            value={<span className="text-base">{profile.name}</span>}
          />
          <StatCard label="Ticker" value={profile.ticker} />
          <StatCard
            label="Sector"
            value={<span className="text-base">{text(profile.sector)}</span>}
          />
          <StatCard
            label="Industry"
            value={<span className="text-base">{text(profile.industry)}</span>}
          />
        </div>
      </section>

      <section className="mt-8">
        <SectionHeader
          title="Market"
          subtitle={
            profile.data_as_of !== null
              ? `As of ${profile.data_as_of}`
              : "Data date not available"
          }
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Share price" value={money(profile.share_price)} />
          <StatCard label="Market cap" value={money(profile.market_cap)} />
          <StatCard
            label="Enterprise value"
            value={money(profile.enterprise_value)}
            sub="Market cap + net debt"
          />
        </div>
      </section>

      <section className="mt-8">
        <SectionHeader
          title="Financials"
          subtitle={
            profile.latest_fiscal_year !== null
              ? `Latest fiscal year FY${profile.latest_fiscal_year}`
              : "Latest fiscal year not available"
          }
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Revenue" value={money(profile.revenue)} />
          <StatCard label="EBITDA" value={money(profile.ebitda)} />
          <StatCard label="Net income" value={money(profile.net_income)} />
          <StatCard
            label="Free cash flow"
            value={money(profile.free_cash_flow)}
          />
          <StatCard label="Cash" value={money(profile.cash)} />
          <StatCard label="Total debt" value={money(profile.total_debt)} />
          <StatCard
            label="Net debt"
            value={money(profile.net_debt)}
            sub="Total debt less cash"
          />
          <StatCard label="Latest fiscal year" value={fiscalYearLabel} />
        </div>
      </section>

      <section className="mt-8">
        <SectionHeader
          title="Price chart"
          subtitle="Interactive chart by TradingView (its own market data, independent of the figures above)"
        />
        <TradingViewChart ticker={profile.ticker} exchange={profile.exchange} />
      </section>

      <section className="mt-8">
        <SectionHeader title="Data" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Data source"
            value={
              <span className="text-base">{profile.data_source}</span>
            }
            sub={
              profile.data_as_of !== null
                ? `Data as of ${profile.data_as_of}`
                : "Data date not available"
            }
          />
        </div>
      </section>

      <Disclaimer />
    </div>
  );
}
