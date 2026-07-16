"use client";

// IC one-pager: the artifact a PE associate circulates to float a screen — a
// single print-optimized page composing the deal score, the deterministic memo,
// a metrics snapshot, and the LBO base case + underwriting scenarios. Rendered
// outside the company chrome so it prints clean; "Print / Save as PDF" invokes
// the browser's print dialog (print:hidden on the controls).

import { useEffect, useState } from "react";
import Link from "next/link";
import MemoRenderer from "@/components/memo/MemoRenderer";
import RatingBadge from "@/components/ui/RatingBadge";
import {
  generateMemo,
  getLboDefaults,
  getProfile,
  getScore,
} from "@/lib/api";
import { fmtCurrency, fmtMultiple, fmtPercent } from "@/lib/format";
import { runLbo } from "@/lib/api";
import type {
  CompanyProfile,
  LboResponse,
  MemoResponse,
  ScoreResponse,
} from "@/lib/types";

interface OnePagerData {
  profile: CompanyProfile;
  score: ScoreResponse | null;
  memo: MemoResponse | null;
  lbo: LboResponse | null;
}

function fmtMom(v: number | null): string {
  return v === null || !Number.isFinite(v) ? "—" : `${v.toFixed(2)}x`;
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-[0.65rem] font-medium uppercase tracking-wide text-ink-muted">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold tabular-nums text-ink">
        {value}
      </div>
    </div>
  );
}

export default function OnePagerPage({
  params,
}: {
  params: { ticker: string };
}) {
  const ticker = decodeURIComponent(params.ticker).toUpperCase();
  const [data, setData] = useState<OnePagerData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const profile = await getProfile(ticker);
        const [score, defaults] = await Promise.all([
          getScore(ticker).catch(() => null),
          getLboDefaults(ticker).catch(() => null),
        ]);
        const [lbo, memo] = await Promise.all([
          defaults
            ? runLbo(ticker, defaults.assumptions).catch(() => null)
            : Promise.resolve(null),
          generateMemo(ticker, defaults?.assumptions ?? null).catch(() => null),
        ]);
        if (!cancelled) setData({ profile, score, memo, lbo });
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load one-pager");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (error !== null) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center">
        <p className="text-sm text-negative">{error}</p>
        <Link href={`/company/${ticker}/dashboard`} className="btn btn-secondary mt-4">
          Back to {ticker}
        </Link>
      </div>
    );
  }

  if (data === null) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-sm text-ink-muted">
        Composing the one-pager for {ticker}…
      </div>
    );
  }

  const { profile, score, memo, lbo } = data;
  const currency = profile.currency ?? null;
  const rating = score?.rating ?? memo?.rating ?? null;
  const sectorIndustry = [profile.sector, profile.industry]
    .filter((v): v is string => v !== null && v !== "")
    .join(" · ");
  const scenarios = lbo?.scenarios ?? [];

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 print:px-0 print:py-0">
      <style>{`@media print { @page { margin: 14mm; } .no-print { display: none !important; } }`}</style>

      {/* Controls (screen only) */}
      <div className="no-print mb-6 flex items-center justify-between">
        <Link
          href={`/company/${ticker}/dashboard`}
          className="text-sm text-ink-muted hover:text-ink"
        >
          ← Back to {ticker}
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="btn btn-primary px-3 py-1.5 text-sm"
        >
          Print / Save as PDF
        </button>
      </div>

      {/* Header */}
      <header className="border-b-2 border-ink pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="font-display text-2xl font-semibold leading-tight text-ink">
              {profile.name}
            </h1>
            <p className="mt-0.5 text-sm text-ink-muted">
              {profile.ticker}
              {profile.exchange ? ` · ${profile.exchange}` : ""}
              {sectorIndustry ? ` · ${sectorIndustry}` : ""}
            </p>
          </div>
          <div className="text-right">
            {rating && <RatingBadge rating={rating} />}
            {score && (
              <div className="mt-1 text-sm tabular-nums text-ink-secondary">
                Deal score{" "}
                <span className="font-semibold text-ink">
                  {score.total.toFixed(0)}
                </span>
                /100
              </div>
            )}
          </div>
        </div>
        <p className="mt-1 text-[0.7rem] uppercase tracking-wide text-ink-muted">
          Investment Intelligence · Screening one-pager · {profile.data_source}
        </p>
      </header>

      {/* Snapshot metrics */}
      <section className="mt-4 grid grid-cols-3 gap-x-6 gap-y-3 sm:grid-cols-6">
        <Metric label="Share price" value={fmtCurrency(profile.share_price, currency)} />
        <Metric label="Market cap" value={fmtCurrency(profile.market_cap, currency)} />
        <Metric label="Enterprise value" value={fmtCurrency(profile.enterprise_value, currency)} />
        <Metric label="Revenue" value={fmtCurrency(profile.revenue, currency)} />
        <Metric label="EBITDA" value={fmtCurrency(profile.ebitda, currency)} />
        <Metric label="Net debt" value={fmtCurrency(profile.net_debt, currency)} />
      </section>

      {/* LBO base case + scenarios */}
      {lbo && (
        <section className="mt-5 border-t border-line pt-4">
          <h2 className="text-sm font-semibold text-ink">LBO returns range</h2>
          <div className="mt-2 grid grid-cols-3 gap-3">
            {scenarios.map((sc) => (
              <div
                key={sc.key}
                className={`rounded border p-2.5 ${
                  sc.key === "base" ? "border-brand" : "border-line"
                }`}
              >
                <div className="text-[0.65rem] font-semibold uppercase tracking-wide text-ink-secondary">
                  {sc.label}
                </div>
                <div className="mt-0.5 text-lg font-semibold tabular-nums text-ink">
                  {fmtPercent(sc.irr)}
                </div>
                <div className="text-[0.7rem] tabular-nums text-ink-muted">
                  IRR · {fmtMom(sc.mom)} MoM · {fmtMultiple(sc.exit_multiple)} exit
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs tabular-nums text-ink-muted">
            Entry {fmtMultiple(lbo.assumptions.entry_multiple)}
            {lbo.assumptions.valuation_basis === "revenue"
              ? " EV/Revenue"
              : " EV/EBITDA"}{" "}
            · EV {fmtCurrency(lbo.entry.entry_ev, currency)} · sponsor equity{" "}
            {fmtCurrency(lbo.entry.sponsor_equity, currency)}
            {lbo.entry.opening_net_leverage != null
              ? ` · ${lbo.entry.opening_net_leverage.toFixed(1)}x opening leverage`
              : ""}
            {lbo.covenants
              ? lbo.covenants.any_breach
                ? " · covenant breach in the hold"
                : " · covenants hold"
              : ""}
          </p>
        </section>
      )}

      {/* Memo sections */}
      {memo && (
        <section className="mt-5 border-t border-line pt-4">
          <div className="columns-1 gap-8 sm:columns-2">
            {memo.sections.map((s) => (
              <div key={s.key} className="mb-4 break-inside-avoid">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-secondary">
                  {s.title}
                </h3>
                <div className="mt-1 text-sm">
                  <MemoRenderer content={s.content} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <footer className="mt-6 border-t border-line pt-3 text-[0.7rem] leading-snug text-ink-muted">
        {memo?.disclaimer ??
          "Educational tool built on public filings. Not investment advice."}
      </footer>
    </div>
  );
}
