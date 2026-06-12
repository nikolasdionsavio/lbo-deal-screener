"use client";

// Company dashboard, ordered by decision relevance (BUILD_SPEC section
// 19.8 IA pass): a six-tile Snapshot band (the numbers an analyst checks
// first), the business description, secondary financial tiles, the
// financial trend chart, the TradingView price chart, recent SEC filings,
// and the data-source tiles last. Identity fields (name/ticker/sector/
// industry) live only in the layout's company header. Profile data comes
// from CompanyContext; filings from GET /api/companies/{ticker}/filings.

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import TradingViewChart from "@/components/company/TradingViewChart";
import FinancialTrendChart from "@/components/charts/FinancialTrendChart";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getFilings } from "@/lib/api";
import { fmtCurrency, fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { useCountUp } from "@/lib/useCountUp";
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

/** Snapshot band tile: compact, value-first (the analyst's first scan).
 *  The value counts up once on first mount (motion pass; reduced-motion
 *  renders it directly). Linked tiles open the page detailing the figure
 *  and carry the card hover lift to signal it. */
function SnapshotTile({
  label,
  value,
  format,
  href,
  hrefTitle,
}: {
  label: string;
  value: number | null;
  format: (value: number | null) => string;
  href?: string;
  hrefTitle?: string;
}) {
  const text = useCountUp(value, format);
  const body = (
    <>
      <div className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">
        {label}
      </div>
      <div className="mt-0.5 text-xl font-semibold tabular-nums text-ink">
        {value === null ? NOT_AVAILABLE : text}
      </div>
    </>
  );
  const surface =
    "block rounded-lg border border-line bg-surface px-4 py-3 shadow-card";
  if (href !== undefined && value !== null) {
    return (
      <Link href={href} title={hrefTitle} className={`${surface} tile-link`}>
        {body}
      </Link>
    );
  }
  return <div className={surface}>{body}</div>;
}

/** Secondary financial tile: one register smaller than the snapshot band. */
function DetailTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3 shadow-card">
      <div className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">
        {label}
      </div>
      <div className="mt-0.5 text-base font-semibold tabular-nums text-ink">
        {value}
      </div>
      {sub !== undefined && (
        <div className="mt-0.5 text-[11px] text-ink-muted">{sub}</div>
      )}
    </div>
  );
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
    <Card>
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
          <div className="fade-in">
            <ul className="divide-y divide-line">
              {data.filings.map((filing) => (
                <FilingRow key={filing.accession} filing={filing} />
              ))}
            </ul>
            <WarningList warnings={data.warnings} className="mt-3" />
          </div>
        )}
      </Card>
    </section>
  );
}

export default function DashboardPage() {
  const { profile } = useCompany();
  const currency = profile.currency ?? null;
  const ticker = encodeURIComponent(profile.ticker);

  function money(value: number | null): ReactNode {
    return value === null ? NOT_AVAILABLE : fmtCurrency(value, currency);
  }

  const fmtMoney = (value: number | null) => fmtCurrency(value, currency);

  const fiscalYearLabel =
    profile.latest_fiscal_year === null
      ? NOT_AVAILABLE
      : `FY${profile.latest_fiscal_year}`;

  const fyNote =
    profile.latest_fiscal_year !== null
      ? `FY${profile.latest_fiscal_year}`
      : "the latest fiscal year";

  return (
    <div>
      <section>
        <SectionHeader
          title="Snapshot"
          subtitle={`Price and EV at market; revenue, EBITDA and net debt from ${fyNote}. EV = market cap + net debt.`}
        />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <SnapshotTile
            label="Share price"
            value={profile.share_price}
            format={fmtMoney}
            href="#price-chart"
            hrefTitle="Jump to the price chart"
          />
          <SnapshotTile
            label="Market cap"
            value={profile.market_cap}
            format={fmtMoney}
            href={`/company/${ticker}/valuation`}
            hrefTitle="Open valuation"
          />
          <SnapshotTile
            label="Enterprise value"
            value={profile.enterprise_value}
            format={fmtMoney}
            href={`/company/${ticker}/valuation`}
            hrefTitle="Open valuation"
          />
          <SnapshotTile
            label="Revenue"
            value={profile.revenue}
            format={fmtMoney}
            href={`/company/${ticker}/financials`}
            hrefTitle="Open financial statements"
          />
          <SnapshotTile
            label="EBITDA"
            value={profile.ebitda}
            format={fmtMoney}
            href={`/company/${ticker}/financials`}
            hrefTitle="Open financial statements"
          />
          <SnapshotTile
            label="Net debt"
            value={profile.net_debt}
            format={fmtMoney}
            href={`/company/${ticker}/financials`}
            hrefTitle="Open financial statements"
          />
        </div>
      </section>

      {profile.description !== null && profile.description !== "" && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader title="Business" />
          <CompanyDescription description={profile.description} />
        </section>
      )}

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader title="Financial detail" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <DetailTile label="Net income" value={money(profile.net_income)} />
          <DetailTile
            label="Free cash flow"
            value={money(profile.free_cash_flow)}
          />
          <DetailTile label="Cash" value={money(profile.cash)} />
          <DetailTile
            label="Total debt"
            value={money(profile.total_debt)}
            sub="Net debt = total debt less cash"
          />
          <DetailTile label="Latest fiscal year" value={fiscalYearLabel} />
        </div>
      </section>

      <FinancialTrendChart ticker={profile.ticker} currency={currency} />

      {/* scroll-mt clears the sticky top bar for the Share price tile anchor. */}
      <section id="price-chart" className="divider-dashed mt-8 scroll-mt-14 pt-8">
        <SectionHeader
          title="Price chart"
          subtitle="TradingView chart. Its market data is independent of the figures above."
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
          value={
            profile.data_as_of !== null
              ? fmtDate(profile.data_as_of)
              : "Not available"
          }
        />
      </section>

      <Disclaimer />
    </div>
  );
}
