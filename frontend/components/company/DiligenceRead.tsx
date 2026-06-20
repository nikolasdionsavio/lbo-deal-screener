"use client";

// The "Diligence read": the figures an LBO analyst checks first, encoded with
// meaning rather than decoration. Net leverage (the go / no-go number) is the
// one promoted figure, threshold-coloured, with an auditable net-debt / EBITDA
// caption; a 2x2 of supporting ratios sits below. Two zero-fetch instruments
// make the dashboard's existing identities visible: the EV capital-structure
// split (EV = equity + net debt) and the net-debt bridge (total debt - cash).
// Everything renders from the CompanyProfile alone; multi-year sparklines and
// the revenue-growth cell are a progressive enhancement from one shared
// /financials fetch and degrade to an em dash when the history is missing.

import type { ReactNode } from "react";
import Delta from "@/components/ui/Delta";
import { MISSING } from "@/components/ui/figure";
import Sparkline from "@/components/ui/Sparkline";
import { fmtCurrency, fmtMultiple, fmtPercent } from "@/lib/format";
import type { CompanyProfile } from "@/lib/types";

const fin = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

export interface DiligenceSeries {
  /** Net debt / EBITDA per fiscal year, oldest first (nulls allowed). */
  leverage: (number | null)[];
  /** FCF / EBITDA per fiscal year, oldest first (nulls allowed). */
  fcfConv: (number | null)[];
  /** Latest-vs-prior revenue growth, or null when the prior year was <= 0. */
  revYoY: number | null;
}

/** One supporting ratio cell: a label, an 18px value, and at most one secondary
 *  signal (a proportion bar, a delta, a sparkline, a caption, or a toned value). */
function RatioCell({
  label,
  value,
  caption,
  bar,
  delta,
  spark,
  tone = "text-ink",
  className = "",
}: {
  label: string;
  value: ReactNode;
  caption?: string;
  bar?: number | null;
  delta?: number | null;
  spark?: (number | null)[];
  tone?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="text-sm text-ink-secondary">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-2">
        <span className={`text-[1.125rem] font-semibold tabular-nums ${tone}`}>
          {value}
        </span>
        {delta !== undefined && <Delta pct={delta ?? null} />}
      </div>
      {fin(bar) && bar >= 0 && (
        <div
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken"
          role="img"
          aria-label={`${Math.round(bar * 100)}% of revenue`}
        >
          <div
            className="h-full rounded-full bg-brand"
            style={{ width: `${Math.min(100, Math.max(0, bar * 100))}%` }}
          />
        </div>
      )}
      {spark && <Sparkline points={spark} className="mt-2 text-ink-muted" />}
      {caption && <div className="mt-1 text-xs text-ink-muted">{caption}</div>}
    </div>
  );
}

export function DiligenceReadBand({
  profile,
  series,
  className = "",
}: {
  profile: CompanyProfile;
  series: DiligenceSeries | null;
  className?: string;
}) {
  const cur = profile.currency ?? null;
  const money = (v: number | null) => fmtCurrency(v, cur);
  const { revenue, ebitda, net_debt, enterprise_value, free_cash_flow } =
    profile;

  const netCash = fin(net_debt) && net_debt < 0;
  const lev =
    !netCash && fin(net_debt) && fin(ebitda) && ebitda > 0
      ? net_debt / ebitda
      : null;
  const levTone = netCash
    ? "text-positive-text"
    : lev === null
      ? "text-ink-muted"
      : lev <= 3
        ? "text-positive-text"
        : lev <= 5
          ? "text-warn-text"
          : "text-negative-text";

  const ebitdaMargin =
    fin(ebitda) && fin(revenue) && revenue > 0 ? ebitda / revenue : null;
  const fcfConv =
    fin(free_cash_flow) && fin(ebitda) && ebitda > 0
      ? free_cash_flow / ebitda
      : null;
  const fcfConvTone =
    fin(free_cash_flow) && free_cash_flow < 0
      ? "text-negative-text"
      : fcfConv === null
        ? "text-ink"
        : fcfConv >= 0.8
          ? "text-positive-text"
          : fcfConv >= 0.5
            ? "text-ink"
            : "text-warn-text";
  const evEbitda =
    fin(enterprise_value) && fin(ebitda) && ebitda > 0
      ? enterprise_value / ebitda
      : null;

  const revYoY = series?.revYoY ?? null;
  const growthTone =
    revYoY === null
      ? "text-ink-muted"
      : Math.abs(revYoY) < 0.0005
        ? "text-ink"
        : revYoY > 0
          ? "text-positive-text"
          : "text-negative-text";

  return (
    <div
      className={`grid grid-cols-2 border-t border-line sm:border-l sm:border-t-0 sm:pl-8 ${className}`}
    >
      <div className="col-span-2 border-b border-line pb-4">
        <div className="text-sm text-ink-secondary">Net leverage</div>
        <div
          className={`mt-1 text-[2.125rem] font-semibold leading-none tabular-nums tracking-tight ${levTone}`}
        >
          {netCash ? "Net cash" : lev === null ? MISSING : fmtMultiple(lev)}
        </div>
        {series && (
          <Sparkline points={series.leverage} className="mt-2 text-ink-muted" />
        )}
        <p className="mt-1.5 text-xs tabular-nums text-ink-muted">
          {money(net_debt)} net debt / {money(ebitda)} EBITDA
        </p>
      </div>

      <RatioCell
        label="EBITDA margin"
        value={fmtPercent(ebitdaMargin)}
        bar={ebitdaMargin}
        className="border-r border-line pr-4 pt-3"
      />
      <RatioCell
        label="FCF conversion"
        value={fmtPercent(fcfConv)}
        tone={fcfConvTone}
        spark={series?.fcfConv}
        className="pl-4 pt-3"
      />
      <RatioCell
        label="EV / EBITDA"
        value={fmtMultiple(evEbitda)}
        caption="entry multiple"
        className="border-r border-t border-line pr-4 pt-3"
      />
      <RatioCell
        label="Revenue growth"
        value={revYoY === null ? MISSING : fmtPercent(revYoY, { signed: true })}
        tone={growthTone}
        caption="vs prior FY"
        className="border-t border-line pl-4 pt-3"
      />
    </div>
  );
}

/** EV = equity (market cap) + net debt, drawn as a proportion bar. Solid,
 *  legible fills only: navy equity, neutral net-debt. Net cash clamps to full
 *  equity and is annotated rather than drawn as a negative segment. */
export function EvSplitBar({ profile }: { profile: CompanyProfile }) {
  const ev = profile.enterprise_value;
  const mc = profile.market_cap;
  const nd = profile.net_debt;
  if (!(fin(ev) && ev > 0 && fin(mc) && fin(nd))) return null;
  const equityPct = Math.min(100, (mc / ev) * 100);
  return (
    <div className="mt-5 border-t border-line pt-4">
      <div
        className="flex h-2.5 w-full overflow-hidden rounded-full bg-surface-sunken"
        role="img"
        aria-label={
          nd < 0
            ? "Net cash: equity exceeds enterprise value"
            : `Equity ${Math.round((mc / ev) * 100)} percent, net debt ${Math.round((nd / ev) * 100)} percent of enterprise value`
        }
      >
        <div className="h-full bg-brand" style={{ width: `${equityPct}%` }} />
        {nd > 0 && (
          <div
            className="h-full bg-line-strong"
            style={{ width: `${(nd / ev) * 100}%` }}
          />
        )}
      </div>
      <div className="mt-2 flex flex-col gap-1.5 text-xs text-ink-secondary sm:flex-row sm:items-center sm:gap-5">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 shrink-0 rounded-sm bg-brand" />
          Equity{" "}
          <span className="tabular-nums text-ink">
            {fmtPercent(mc / ev, { digits: 0 })}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 shrink-0 rounded-sm bg-line-strong" />
          Net debt{" "}
          {nd < 0 ? (
            <span className="text-positive-text">net cash</span>
          ) : (
            <span className="tabular-nums text-ink">
              {fmtPercent(nd / ev, { digits: 0 })}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}

/** Net debt = total debt - cash, drawn as a bridge: the debt track, cash
 *  carving from the right, and a hard tick at the resulting net-debt position. */
export function NetDebtBridge({ profile }: { profile: CompanyProfile }) {
  const cur = profile.currency ?? null;
  const money = (v: number | null) => fmtCurrency(v, cur);
  const td = profile.total_debt;
  const cash = profile.cash;
  if (!(fin(td) && td > 0 && fin(cash))) return null;
  const net = td - cash;
  return (
    <div className="mt-5 border-t border-line pt-4">
      <div
        className="relative h-2.5 w-full overflow-hidden rounded-full bg-negative-soft"
        role="img"
        aria-label={`Total debt ${money(td)} less cash ${money(cash)} equals net debt ${money(net)}`}
      >
        <div
          className="absolute right-0 top-0 h-full bg-accent-soft"
          style={{ width: `${Math.min(100, (cash / td) * 100)}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-ink"
          style={{ left: `${Math.min(100, Math.max(0, (net / td) * 100))}%` }}
        />
      </div>
      <p className="mt-2 text-xs tabular-nums text-ink-muted">
        Total debt {money(td)} − cash {money(cash)} ={" "}
        <span className={net < 0 ? "text-positive-text" : "text-ink"}>
          net debt {money(net)}
        </span>
      </p>
    </div>
  );
}
