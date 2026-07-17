"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useCompany } from "@/components/company/CompanyContext";
import AssumptionsPanel from "@/components/lbo/AssumptionsPanel";
import CovenantPanel from "@/components/lbo/CovenantPanel";
import DebtPaydownChart from "@/components/lbo/DebtPaydownChart";
import ValueCreationBridge from "@/components/lbo/ValueCreationBridge";
import SensitivityTable from "@/components/charts/SensitivityTable";
import Card from "@/components/ui/Card";
import DataTable, { type Column } from "@/components/ui/DataTable";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getLboDefaults, runLbo } from "@/lib/api";
import { fmtCurrency, fmtMultiple, fmtPercent } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import type {
  LboAssumptions,
  LboEntry,
  LboResponse,
  LboScenario,
  LboYear,
} from "@/lib/types";

/** MoM rendered as X.XXx per spec; fmtMultiple is one decimal, so not reused here. */
function fmtMom(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(2)}x`;
}

// The LBO model runs entirely in the company's reporting currency
// (BUILD_SPEC section 4 currency contract).
function yearColumns(currency: string | null): Column<LboYear>[] {
  return [
    { key: "year", header: "Year", render: (r) => `Year ${r.year}` },
    {
      key: "revenue",
      header: "Revenue",
      numeric: true,
      render: (r) => fmtCurrency(r.revenue, currency),
    },
    {
      key: "ebitda",
      header: "EBITDA",
      numeric: true,
      render: (r) => fmtCurrency(r.ebitda, currency),
    },
    {
      key: "capex",
      header: "Capex",
      numeric: true,
      render: (r) => fmtCurrency(r.capex, currency),
    },
    {
      key: "delta_nwc",
      header: "ΔNWC",
      numeric: true,
      render: (r) => fmtCurrency(r.delta_nwc, currency),
    },
    {
      key: "interest",
      header: "Interest",
      numeric: true,
      render: (r) => fmtCurrency(r.interest, currency),
    },
    {
      key: "taxes",
      header: "Taxes",
      numeric: true,
      render: (r) => fmtCurrency(r.taxes, currency),
    },
    {
      key: "fcf",
      header: "FCF",
      numeric: true,
      render: (r) => fmtCurrency(r.fcf, currency),
    },
    {
      key: "debt_repaid",
      header: "Debt repaid",
      numeric: true,
      render: (r) => fmtCurrency(r.debt_repaid, currency),
    },
    {
      key: "ending_debt",
      header: "Ending debt",
      numeric: true,
      render: (r) => fmtCurrency(r.ending_debt, currency),
    },
    {
      key: "ending_cash",
      header: "Ending cash",
      numeric: true,
      render: (r) => fmtCurrency(r.ending_cash, currency),
    },
  ];
}

/** IRR/MoM headline value. Rendered directly, never counted up (DESIGN.md
 *  motion: no number-count animation). */
function HeroFigure({
  value,
  format,
}: {
  value: number | null;
  format: (value: number | null) => string;
}) {
  return (
    <div className="mt-1 font-mono text-[2rem] leading-none tabular-nums text-ink">
      {format(value)}
    </div>
  );
}

/** One aligned output figure: label over a data-font value, no card. */
function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-ink-muted">{label}</div>
      <div className="mt-1 font-mono text-[0.9375rem] tabular-nums text-ink">
        {value}
      </div>
    </div>
  );
}

// Named for the change statement shown after an edit. Arrays (per-year growth /
// margin) are reported generically; the first changed scalar names itself.
const ASSUMPTION_LABELS: { key: string; label: string; unit: "x" | "%" | "" }[] = [
  { key: "entry_multiple", label: "Entry multiple", unit: "x" },
  { key: "debt_multiple", label: "Debt multiple", unit: "x" },
  { key: "exit_multiple", label: "Exit multiple", unit: "x" },
  { key: "entry_leverage_pct", label: "Leverage", unit: "%" },
  { key: "tax_rate", label: "Tax rate", unit: "%" },
  { key: "interest_rate", label: "Interest rate", unit: "%" },
  { key: "capex_pct_revenue", label: "Capex", unit: "%" },
  { key: "nwc_pct_revenue", label: "Change in NWC", unit: "%" },
  { key: "mandatory_repayment_pct", label: "Mandatory repayment", unit: "%" },
  { key: "transaction_fee_pct", label: "Transaction fees", unit: "%" },
  { key: "holding_period", label: "Holding period", unit: "" },
];

function fmtAssume(v: number, unit: "x" | "%" | ""): string {
  if (unit === "%") return `${(v * 100).toFixed(1)}%`;
  if (unit === "x") return `${v.toFixed(1)}x`;
  return `${v}`;
}

/** The first changed scalar assumption, named as "X changed from A to B". */
function diffAssumptions(
  prev: LboAssumptions,
  curr: LboAssumptions,
): string | null {
  for (const { key, label, unit } of ASSUMPTION_LABELS) {
    const a = (prev as unknown as Record<string, unknown>)[key];
    const b = (curr as unknown as Record<string, unknown>)[key];
    if (typeof a === "number" && typeof b === "number" && Math.abs(a - b) > 1e-9) {
      return `${label} changed from ${fmtAssume(a, unit)} to ${fmtAssume(b, unit)}`;
    }
  }
  return null;
}

/** After an edit, states precisely what changed and how the return moved
 *  (DESIGN.md). Its own component so the page's early returns never gate a
 *  hook. No number-count animation; the value simply updates. */
function ChangeNote({ lbo }: { lbo: LboResponse | null }) {
  const prev = useRef<{
    assumptions: LboAssumptions;
    irr: number | null;
    mom: number | null;
  } | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!lbo) return;
    const curr = {
      assumptions: lbo.assumptions,
      irr: lbo.exit.irr,
      mom: lbo.exit.mom,
    };
    const before = prev.current;
    if (before) {
      const what = diffAssumptions(before.assumptions, curr.assumptions);
      const moved = before.irr !== curr.irr || before.mom !== curr.mom;
      if (what || moved) {
        const parts: string[] = [];
        if (what) parts.push(`${what}.`);
        if (moved) {
          parts.push(
            `Five-year IRR ${fmtPercent(before.irr)} → ${fmtPercent(
              curr.irr,
            )}, MoM ${fmtMom(before.mom)} → ${fmtMom(curr.mom)}.`,
          );
        }
        setNote(parts.join(" "));
      }
    }
    prev.current = curr;
  }, [lbo]);

  if (note === null) return null;
  return (
    <p
      className="border-y border-line py-2 font-mono text-[11px] leading-relaxed text-ink-secondary"
      role="status"
      aria-live="polite"
    >
      {note}
    </p>
  );
}

/** One Sources-or-Uses line; `strong` renders the ruled total. */
function SuLine({
  label,
  value,
  sub,
  currency,
  strong = false,
}: {
  label: string;
  value: number | null;
  sub?: string;
  currency: string | null;
  strong?: boolean;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-3 py-1 ${
        strong
          ? "mt-1 border-t border-line pt-1.5 font-semibold text-ink"
          : "text-ink-secondary"
      }`}
    >
      <span className="text-sm">
        {label}
        {sub ? <span className="ml-1.5 text-xs text-ink-muted">{sub}</span> : null}
      </span>
      <span className="text-sm tabular-nums">{fmtCurrency(value, currency)}</span>
    </div>
  );
}

/** Base / strategic / downside underwriting cases, worst-to-best. A sponsor
 *  brackets the return rather than underwriting a single point estimate. */
function ScenarioCards({ scenarios }: { scenarios: LboScenario[] }) {
  if (scenarios.length === 0) return null;
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-3">
      {scenarios.map((sc) => {
        const isBase = sc.key === "base";
        return (
          <div
            key={sc.key}
            className={`rounded-lg border p-4 ${
              isBase
                ? "border-brand ring-1 ring-brand-soft"
                : "border-line bg-surface"
            }`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-secondary">
                {sc.label}
              </span>
              <span className="text-xs tabular-nums text-ink-muted">
                {fmtMultiple(sc.exit_multiple)} exit
              </span>
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums text-ink">
              {fmtPercent(sc.irr)}
            </div>
            <div className="text-xs tabular-nums text-ink-muted">
              IRR · {fmtMom(sc.mom)} MoM
            </div>
            <p className="mt-2 text-xs leading-snug text-ink-muted">{sc.note}</p>
          </div>
        );
      })}
    </div>
  );
}

/** Sources & Uses — the first table in any real LBO. Uses (purchase EV + fees)
 *  must balance Sources (new debt + the sponsor-equity plug). */
function SourcesUses({
  entry,
  currency,
}: {
  entry: LboEntry;
  currency: string | null;
}) {
  const lev = entry.opening_net_leverage;
  return (
    <div className="mt-5 grid gap-x-10 gap-y-3 border-t border-line pt-4 sm:grid-cols-2">
      <div>
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-muted">
          Uses
        </div>
        <SuLine
          label="Purchase enterprise value"
          value={entry.entry_ev}
          currency={currency}
        />
        <SuLine
          label="Transaction fees"
          value={entry.transaction_fees}
          currency={currency}
        />
        <SuLine
          label="Total uses"
          value={entry.total_uses}
          currency={currency}
          strong
        />
      </div>
      <div>
        <div className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-muted">
          Sources
        </div>
        <SuLine
          label="New debt"
          value={entry.opening_debt}
          sub={lev != null ? `${lev.toFixed(1)}x EBITDA` : undefined}
          currency={currency}
        />
        <SuLine
          label="Sponsor equity"
          value={entry.sponsor_equity}
          sub={
            entry.equity_pct != null ? fmtPercent(entry.equity_pct) : undefined
          }
          currency={currency}
        />
        <SuLine
          label="Total sources"
          value={entry.total_uses}
          currency={currency}
          strong
        />
      </div>
    </div>
  );
}

export default function LboPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const currency = profile.currency ?? null;

  useEffect(() => {
    window.localStorage.setItem("lastTicker", ticker);
  }, [ticker]);

  const defaultsApi = useApi(() => getLboDefaults(ticker), [ticker]);
  const defaults = defaultsApi.data;

  // Edits are keyed by ticker so stale assumptions from a previous company are
  // never posted (or displayed) after navigation. null = use server defaults.
  const [edited, setEdited] = useState<{
    ticker: string;
    values: LboAssumptions;
  } | null>(null);
  const debounced = useDebounced(edited, 500);

  const editedValues = edited && edited.ticker === ticker ? edited.values : null;
  const debouncedValues =
    debounced && debounced.ticker === ticker ? debounced.values : null;
  const requestBody = debouncedValues ?? defaults?.assumptions ?? null;

  const lboApi = useApi<LboResponse | null>(
    () => (requestBody ? runLbo(ticker, requestBody) : Promise.resolve(null)),
    [ticker, requestBody],
  );
  const lbo = lboApi.data;

  const current = editedValues ?? defaults?.assumptions ?? null;
  const recomputing = lboApi.loading && lbo !== null;

  const header = (
    <SectionHeader
      variant="page"
      as="h2"
      title="LBO Model"
      subtitle="Simplified five-year model. Edits recompute everything, including sensitivities."
      actions={
        <div className="flex items-center gap-3">
          {recomputing && (
            <span className="text-xs text-ink-muted">Recomputing…</span>
          )}
          <Link
            href={`/onepager/${ticker}`}
            className="btn btn-secondary px-2.5 py-1 text-xs"
          >
            IC one-pager
          </Link>
        </div>
      }
    />
  );

  if (defaultsApi.loading) {
    return (
      <div className="space-y-6">
        {header}
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (!defaults || !current) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          message={
            defaultsApi.error?.message ?? "LBO default assumptions are unavailable."
          }
          onRetry={defaultsApi.retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const entryBaseLabel =
    profile.latest_fiscal_year !== null
      ? `FY${profile.latest_fiscal_year}`
      : "latest fiscal year";

  return (
    <div className="space-y-6">
      {header}
      <ChangeNote lbo={lbo} />

      {lbo && lbo.warnings.length > 0 && <WarningList warnings={lbo.warnings} />}

      <div className="grid items-start gap-6 xl:grid-cols-[340px,minmax(0,1fr)]">
        {/* Assumptions stay in view while the outputs scroll (xl and up);
            64px clears the sticky top bar. */}
        <div className="xl:sticky xl:top-[64px] xl:max-h-[calc(100vh-80px)] xl:self-start xl:overflow-y-auto">
          <AssumptionsPanel
            values={current}
            basis={defaults.basis}
            onChange={(values) => setEdited({ ticker, values })}
            onReset={() => setEdited(null)}
          />
        </div>

        <div className="min-w-0">
          {lboApi.error ? (
            <ErrorState message={lboApi.error.message} onRetry={lboApi.retry} />
          ) : !lbo ? (
            <LoadingState lines={10} />
          ) : (
            // fade-in: the outputs LoadingState resolving to the model.
            <div className="fade-in">
              <section>
                <SectionHeader
                  title="Entry"
                  subtitle={
                    lbo.assumptions.valuation_basis === "revenue"
                      ? `Entry at ${fmtMultiple(
                          lbo.assumptions.entry_multiple,
                        )} EV/Revenue with ${fmtPercent(
                          lbo.assumptions.entry_leverage_pct,
                        )} loan-to-value debt`
                      : `Entry at ${fmtMultiple(
                          lbo.assumptions.entry_multiple,
                        )} EV/EBITDA with ${fmtMultiple(
                          lbo.assumptions.debt_multiple,
                        )} of opening debt`
                  }
                />
                <div>
                  <div className="grid gap-x-10 gap-y-3 border-y border-line py-4 sm:grid-cols-3">
                    <Figure
                      label="Entry EV"
                      value={fmtCurrency(lbo.entry.entry_ev, currency)}
                    />
                    <Figure
                      label="Sponsor equity"
                      value={fmtCurrency(lbo.entry.sponsor_equity, currency)}
                    />
                    <Figure
                      label="Opening net leverage"
                      value={
                        lbo.entry.opening_net_leverage != null
                          ? `${lbo.entry.opening_net_leverage.toFixed(1)}x`
                          : "—"
                      }
                    />
                  </div>
                  <SourcesUses entry={lbo.entry} currency={currency} />
                  <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
                    Entry base ({entryBaseLabel}): EBITDA{" "}
                    {fmtCurrency(lbo.entry.entry_ebitda, currency)} on revenue{" "}
                    {fmtCurrency(lbo.entry.entry_revenue, currency)}.
                  </p>
                </div>
              </section>

              <section className="divider-dashed mt-8 pt-8">
                <SectionHeader
                  title="Returns"
                  subtitle={`Exit at ${fmtMultiple(
                    lbo.assumptions.exit_multiple,
                  )} EV/EBITDA after ${lbo.assumptions.holding_period} ${
                    lbo.assumptions.holding_period === 1 ? "year" : "years"
                  }`}
                />
                <div className="grid gap-x-10 gap-y-5 border-y border-line py-4 sm:grid-cols-2">
                  <div>
                    <div className="text-[11px] text-ink-muted">IRR</div>
                    <HeroFigure value={lbo.exit.irr} format={fmtPercent} />
                    <div className="mt-1.5 text-xs text-ink-muted">
                      Internal rate of return on sponsor equity
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-ink-muted">MoM</div>
                    <HeroFigure value={lbo.exit.mom} format={fmtMom} />
                    <div className="mt-1.5 text-xs text-ink-muted">
                      Multiple of money, exit equity over sponsor equity
                    </div>
                  </div>
                </div>
                <div className="mt-5 grid gap-x-10 gap-y-3 sm:grid-cols-3">
                  <Figure
                    label="Exit EBITDA"
                    value={fmtCurrency(lbo.exit.exit_ebitda, currency)}
                  />
                  <Figure
                    label="Exit EV"
                    value={fmtCurrency(lbo.exit.exit_ev, currency)}
                  />
                  <Figure
                    label="Exit equity"
                    value={fmtCurrency(lbo.exit.exit_equity, currency)}
                  />
                </div>

                {lbo.scenarios.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold text-ink">
                      Underwriting cases
                    </h3>
                    <p className="mt-0.5 text-xs text-ink-muted">
                      The base case bracketed by a strategic-buyer upside and a
                      downturn downside. A range, not a point estimate.
                    </p>
                    <ScenarioCards scenarios={lbo.scenarios} />
                  </div>
                )}
              </section>

              <section className="divider-dashed mt-8 pt-8">
                <SectionHeader
                  title={`${lbo.assumptions.holding_period}-year projection`}
                  subtitle={`All figures ${
                    currency ?? "USD"
                  }. ΔNWC is the change in net working capital.`}
                />
                <Card>
                  <DataTable
                    columns={yearColumns(currency)}
                    rows={lbo.years}
                    rowKey={(row) => row.year}
                  />
                </Card>
              </section>

              {lbo.entry.opening_debt !== null && lbo.years.length > 0 && (
                <section className="divider-dashed mt-8 pt-8">
                  <SectionHeader
                    title="Debt paydown"
                    subtitle="Ending debt and ending cash by year; year 0 is the opening debt at entry."
                  />
                  <Card>
                    <DebtPaydownChart
                      openingDebt={lbo.entry.opening_debt}
                      years={lbo.years}
                      currency={currency}
                    />
                  </Card>
                </section>
              )}

              {lbo.covenants && lbo.covenants.years.length > 0 && (
                <section className="divider-dashed mt-8 pt-8">
                  <SectionHeader
                    title="Covenant headroom"
                    subtitle="The debt path tested against a standard maintenance package, year by year."
                  />
                  <Card>
                    <CovenantPanel covenants={lbo.covenants} />
                  </Card>
                </section>
              )}

              <div className="divider-dashed mt-8 pt-8">
                <ValueCreationBridge lbo={lbo} currency={currency} />
              </div>

              <section className="divider-dashed mt-8 pt-8">
                <SectionHeader
                  title="Sensitivities"
                  subtitle="The full model is recomputed for each cell. The base case cell is outlined."
                />
                <div className="space-y-5">
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      IRR: exit multiple vs revenue growth shift
                    </h3>
                    <SensitivityTable
                      grid={lbo.sensitivities.irr_exit_vs_growth}
                      format="percent"
                      rowFormat="multiple"
                      colFormat="shift"
                      baseRow={lbo.assumptions.exit_multiple}
                      baseCol={0}
                    />
                  </Card>
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      {lbo.assumptions.valuation_basis === "revenue"
                        ? "IRR: entry EV/Revenue vs exit EV/EBITDA"
                        : "IRR: entry multiple vs exit multiple"}
                    </h3>
                    <SensitivityTable
                      grid={lbo.sensitivities.irr_entry_vs_exit}
                      format="percent"
                      rowFormat="multiple"
                      colFormat="multiple"
                      baseRow={lbo.assumptions.entry_multiple}
                      baseCol={lbo.assumptions.exit_multiple}
                    />
                  </Card>
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      MoM: exit multiple vs EBITDA margin shift
                    </h3>
                    <SensitivityTable
                      grid={lbo.sensitivities.mom_exit_vs_margin}
                      format="multiple"
                      rowFormat="multiple"
                      colFormat="shift"
                      baseRow={lbo.assumptions.exit_multiple}
                      baseCol={0}
                    />
                  </Card>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>

      <Disclaimer />
    </div>
  );
}
