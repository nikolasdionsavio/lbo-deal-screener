"use client";

// Company dashboard: StatCard grid over every profile field from
// BUILD_SPEC section 2 / section 12 (profile endpoint), the business
// description as collapsible prose (section 19.6), and a lazily fetched
// "Recent SEC filings" card (section 19.5). Profile data comes from the
// layout's CompanyContext; filings from GET /api/companies/{ticker}/filings.

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import TradingViewChart from "@/components/company/TradingViewChart";
import FinancialTrendChart from "@/components/charts/FinancialTrendChart";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import WarningList from "@/components/ui/WarningList";
import { getFilings } from "@/lib/api";
import { fmtCurrency } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Filing } from "@/lib/types";

const NOT_AVAILABLE = (
  <span title="Not available" className="text-ink-muted">
    —
  </span>
);

// 16px, 1.5px-stroke icons for the Data section tile rows.
function dataIconAttrs() {
  return {
    width: 16,
    height: 16,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };
}

function DatabaseIcon() {
  return (
    <svg {...dataIconAttrs()}>
      <ellipse cx="8" cy="3.5" rx="5.5" ry="2" />
      <path d="M2.5 3.5V8c0 1.1 2.46 2 5.5 2s5.5-.9 5.5-2V3.5" />
      <path d="M2.5 8v4.5c0 1.1 2.46 2 5.5 2s5.5-.9 5.5-2V8" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg {...dataIconAttrs()}>
      <rect x="2" y="3" width="12" height="11.5" rx="1.5" />
      <path d="M2 6.5h12M5.25 1.5V4M10.75 1.5V4" />
    </svg>
  );
}

/** Data-section tile row (Aesthetic v2): rounded-square icon tile + label
 *  + value, separated from siblings by dashed dividers. */
function DataSourceRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-4 py-3.5">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-surface text-ink-secondary">
        {icon}
      </span>
      <span className="text-sm font-semibold text-ink">{label}</span>
      <span className="ml-auto text-right text-sm tabular-nums text-ink-secondary">
        {value}
      </span>
    </div>
  );
}

function text(value: string | null): ReactNode {
  return value === null || value === "" ? NOT_AVAILABLE : value;
}

/** Business description as prose, clamped to ~4 lines with a toggle when long. */
function CompanyDescription({ description }: { description: string }) {
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const proseRef = useRef<HTMLParagraphElement | null>(null);

  // Detect whether the clamped text actually overflows so the toggle only
  // appears when there is hidden content. The resize listener keeps it
  // honest when the column width changes.
  useEffect(() => {
    const measure = () => {
      const el = proseRef.current;
      if (el === null) return;
      // scrollHeight > clientHeight only while the clamp is applied; when
      // expanded, keep the toggle so the user can collapse again.
      if (!expanded) setOverflows(el.scrollHeight > el.clientHeight + 1);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [description, expanded]);

  return (
    <Card className="mt-4">
      <p
        ref={proseRef}
        className={`text-sm leading-relaxed text-ink-secondary ${
          expanded ? "" : "line-clamp-4"
        }`}
      >
        {description}
      </p>
      {(overflows || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-sm font-medium text-brand-text hover:underline"
          aria-expanded={expanded}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </Card>
  );
}

/** Form-type badge; 10-K (the primary annual filing) gets the accent tint. */
function FilingFormBadge({ form }: { form: string }) {
  const accent = form === "10-K";
  return (
    <span
      className={`inline-flex w-20 shrink-0 items-center justify-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${
        accent
          ? "border-transparent bg-accent-soft text-positive-text"
          : "border-line bg-surface-sunken text-ink-secondary"
      }`}
    >
      {form}
    </span>
  );
}

function FilingRow({ filing }: { filing: Filing }) {
  return (
    <li className="flex flex-wrap items-center gap-3 py-2">
      <FilingFormBadge form={filing.form} />
      <span className="text-sm tabular-nums text-ink-secondary">
        Filed {filing.filed}
      </span>
      <a
        href={filing.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-brand-text underline decoration-line-strong underline-offset-2 hover:decoration-brand"
        title={filing.primary_document}
      >
        View filing
      </a>
    </li>
  );
}

/** Lazily fetched list of the latest SEC filings (BUILD_SPEC section 19.5). */
function RecentFilings({ ticker }: { ticker: string }) {
  const { data, error, loading } = useApi(() => getFilings(ticker), [ticker]);

  return (
    <section className="divider-dashed mt-8 pt-8">
      <SectionHeader
        title="Recent SEC filings"
        subtitle={data !== null ? `Source: ${data.source}` : undefined}
      />
      <Card>
        {loading ? (
          <LoadingState lines={4} />
        ) : error !== null || data === null ? (
          <p className="text-sm text-ink-muted">
            Could not load SEC filings
            {error !== null ? `: ${error.message}` : "."}
          </p>
        ) : data.filings.length === 0 ? (
          <div>
            <p className="text-sm text-warn-text">
              {data.warnings.length > 0
                ? data.warnings.join(" ")
                : "No recent SEC filings are available for this company."}
            </p>
          </div>
        ) : (
          <>
            <ul className="divide-y divide-line">
              {data.filings.map((filing) => (
                <FilingRow key={filing.accession} filing={filing} />
              ))}
            </ul>
            <WarningList warnings={data.warnings} className="mt-3" />
          </>
        )}
      </Card>
    </section>
  );
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
        {profile.description !== null && profile.description !== "" && (
          <CompanyDescription description={profile.description} />
        )}
      </section>

      <section className="divider-dashed mt-8 pt-8">
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

      <section className="divider-dashed mt-8 pt-8">
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

      <FinancialTrendChart ticker={profile.ticker} currency={currency} />

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Price chart"
          subtitle="Interactive chart by TradingView (its own market data, independent of the figures above)"
        />
        <TradingViewChart ticker={profile.ticker} exchange={profile.exchange} />
      </section>

      <RecentFilings ticker={profile.ticker} />

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader title="Data" />
        <DataSourceRow
          icon={<DatabaseIcon />}
          label="Data source"
          value={profile.data_source}
        />
        <div className="divider-dashed" />
        <DataSourceRow
          icon={<CalendarIcon />}
          label="Data as of"
          value={profile.data_as_of ?? "Not available"}
        />
      </section>

      <Disclaimer />
    </div>
  );
}
