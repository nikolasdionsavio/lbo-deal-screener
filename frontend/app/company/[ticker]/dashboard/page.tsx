"use client";

// Company dashboard, ordered by decision relevance (BUILD_SPEC section
// 19.8 IA pass): a six-tile Snapshot band (the numbers an analyst checks
// first), the business description, secondary financial tiles, the
// financial trend chart, the TradingView price chart, recent SEC filings,
// and the data-source tiles last. Identity fields (name/ticker/sector/
// industry) live only in the layout's company header. Profile data comes
// from CompanyContext; filings from GET /api/companies/{ticker}/filings.

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import {
  NetDebtBridge,
  type DiligenceSeries,
} from "@/components/company/DiligenceRead";
import TradingViewChart from "@/components/company/TradingViewChart";
import FinancialTrendChart from "@/components/charts/FinancialTrendChart";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import { FigureRow, MISSING } from "@/components/ui/figure";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import Sparkline from "@/components/ui/Sparkline";
import WarningList from "@/components/ui/WarningList";
import { getFilings, getFinancials } from "@/lib/api";
import { fmtCurrency, fmtDate, fmtPercent } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Filing, FinancialsResponse } from "@/lib/types";

const isFin = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

/** Derive the multi-year series the dashboard band + flow rows visualise from a
 *  single /financials payload. Returns nulls until the fetch resolves or when
 *  fewer than two revenue-bearing years exist, so every mark degrades honestly. */
function buildSeries(financials: FinancialsResponse | null): {
  series: DiligenceSeries | null;
  rowSparks: { netIncome: number[]; fcf: number[] } | null;
} {
  if (financials === null) return { series: null, rowSparks: null };
  const years = [...financials.years]
    .filter((y) => isFin(y.revenue))
    .sort((a, b) => a.fiscal_year - b.fiscal_year);
  if (years.length < 2) return { series: null, rowSparks: null };

  const leverage = years.map((y) => {
    const nd =
      isFin(y.total_debt) && isFin(y.cash_and_equivalents)
        ? y.total_debt - y.cash_and_equivalents
        : null;
    return nd !== null && isFin(y.ebitda) && y.ebitda > 0 ? nd / y.ebitda : null;
  });
  const fcfConv = years.map((y) =>
    isFin(y.free_cash_flow) && isFin(y.ebitda) && y.ebitda > 0
      ? y.free_cash_flow / y.ebitda
      : null,
  );
  const rev = years.map((y) => y.revenue as number);
  const prior = rev[rev.length - 2];
  const latest = rev[rev.length - 1];
  const revYoY = prior > 0 ? latest / prior - 1 : null;

  return {
    series: { leverage, fcfConv, revYoY },
    rowSparks: {
      netIncome: years.map((y) => y.net_income).filter(isFin),
      fcf: years.map((y) => y.free_cash_flow).filter(isFin),
    },
  };
}

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

/** One figure in the company summary strip: a direct label over a value, no
 *  background box. Columns are separated by spacing; the strip by thin rules
 *  (DESIGN.md company summary aesthetic, not a row of KPI cards). */
function StripFigure({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="py-3">
      <div className="text-[11px] leading-tight text-ink-muted">{label}</div>
      <div className="mt-1 font-mono text-[0.9375rem] tabular-nums text-ink">
        {value}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { profile } = useCompany();
  const currency = profile.currency ?? null;

  const fmtMoney = (value: number | null) => fmtCurrency(value, currency);
  // A money figure for a ledger row, or the muted dash when it is missing.
  const fig = (value: number | null) =>
    value === null ? MISSING : fmtMoney(value);

  const fyNote =
    profile.latest_fiscal_year !== null
      ? `FY${profile.latest_fiscal_year}`
      : "the latest fiscal year";

  // One shared /financials fetch drives the band sparklines, the YoY delta, the
  // flow-row sparklines, and the trend chart below (passed down so it is fetched
  // once). The page renders fully from the profile before this resolves.
  const { data: financials } = useApi(
    () => getFinancials(profile.ticker),
    [profile.ticker],
  );
  const { rowSparks } = useMemo(() => buildSeries(financials), [financials]);

  const ebitdaMargin =
    isFin(profile.ebitda) && isFin(profile.revenue) && profile.revenue !== 0
      ? profile.ebitda / profile.revenue
      : null;
  const netDebt = profile.net_debt;
  const netLabel = isFin(netDebt) && netDebt < 0 ? "Net cash" : "Net debt";
  const netValue = isFin(netDebt) ? fmtMoney(Math.abs(netDebt)) : MISSING;

  return (
    <div>
      {/* Company summary: an aligned information strip, not KPI cards. */}
      <section>
        <div className="grid grid-cols-2 gap-x-6 border-y border-line py-1 sm:grid-cols-3 lg:grid-cols-6">
          <StripFigure label="Share price" value={fig(profile.share_price)} />
          <StripFigure label="Market cap" value={fig(profile.market_cap)} />
          <StripFigure
            label="Enterprise value"
            value={fig(profile.enterprise_value)}
          />
          <StripFigure label={`Revenue ${fyNote}`} value={fig(profile.revenue)} />
          <StripFigure
            label="EBITDA margin"
            value={ebitdaMargin === null ? MISSING : fmtPercent(ebitdaMargin)}
          />
          <StripFigure label={netLabel} value={netValue} />
        </div>
        <p className="mt-2.5 font-mono text-[11px] leading-relaxed text-ink-muted">
          Market data{" "}
          {profile.data_as_of !== null
            ? `as of ${fmtDate(profile.data_as_of)}`
            : "unavailable"}{" "}
          · financial figures from {fyNote} · {profile.data_source}
        </p>
        <p className="mt-2 text-xs text-ink-muted">
          Start here: confirm the reporting period before opening the model.
          Enterprise value = market cap + net debt.
        </p>
      </section>

      {profile.description !== null && profile.description !== "" && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader title="Business" />
          <CompanyDescription description={profile.description} />
        </section>
      )}

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader title="Financial detail" />
        <Card>
          <div className="grid gap-y-0 sm:grid-cols-2 sm:gap-x-10">
            <div>
              <FigureRow
                label="Net income"
                value={fig(profile.net_income)}
                sub={
                  rowSparks ? (
                    <Sparkline
                      points={rowSparks.netIncome}
                      className="mt-1 text-ink-muted"
                    />
                  ) : undefined
                }
              />
              <FigureRow
                label="Free cash flow"
                value={fig(profile.free_cash_flow)}
                sub={
                  rowSparks ? (
                    <Sparkline
                      points={rowSparks.fcf}
                      className="mt-1 text-ink-muted"
                    />
                  ) : undefined
                }
              />
              <FigureRow label="Cash" value={fig(profile.cash)} />
            </div>
            <div>
              <FigureRow label="Total debt" value={fig(profile.total_debt)} />
              <FigureRow
                label="Latest fiscal year"
                value={
                  profile.latest_fiscal_year === null
                    ? MISSING
                    : `FY${profile.latest_fiscal_year}`
                }
              />
            </div>
          </div>
          <NetDebtBridge profile={profile} />
          <p className="mt-3 text-xs text-ink-muted">
            Net debt = total debt less cash.
          </p>
        </Card>
      </section>

      <FinancialTrendChart currency={currency} financials={financials} />

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
