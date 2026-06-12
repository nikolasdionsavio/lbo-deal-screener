"use client";

import { useEffect, useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import AssumptionsPanel from "@/components/lbo/AssumptionsPanel";
import DebtPaydownChart from "@/components/lbo/DebtPaydownChart";
import ValueCreationBridge from "@/components/lbo/ValueCreationBridge";
import SensitivityTable from "@/components/charts/SensitivityTable";
import Card from "@/components/ui/Card";
import DataTable, { type Column } from "@/components/ui/DataTable";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import StatCard from "@/components/ui/StatCard";
import WarningList from "@/components/ui/WarningList";
import { getLboDefaults, runLbo } from "@/lib/api";
import { fmtCurrency, fmtMultiple, fmtPercent } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import { useCountUp } from "@/lib/useCountUp";
import type { LboAssumptions, LboResponse, LboYear } from "@/lib/types";

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

/** IRR/MoM hero value: counts up once on first mount (motion pass);
 *  recomputes after edits render directly. */
function HeroFigure({
  value,
  format,
}: {
  value: number | null;
  format: (value: number | null) => string;
}) {
  const text = useCountUp(value, format);
  return <span className="text-3xl">{text}</span>;
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums text-ink">
        {value}
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
        recomputing ? (
          <span className="text-xs text-ink-muted">Recomputing…</span>
        ) : undefined
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
                  subtitle={`Entry at ${fmtMultiple(
                    lbo.assumptions.entry_multiple,
                  )} EV/EBITDA with ${fmtMultiple(
                    lbo.assumptions.debt_multiple,
                  )} of opening debt`}
                />
                <Card>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Figure
                      label="Entry EV"
                      value={fmtCurrency(lbo.entry.entry_ev, currency)}
                    />
                    <Figure
                      label="Opening debt"
                      value={fmtCurrency(lbo.entry.opening_debt, currency)}
                    />
                    <Figure
                      label="Sponsor equity"
                      value={fmtCurrency(lbo.entry.sponsor_equity, currency)}
                    />
                    <Figure
                      label="Equity %"
                      value={fmtPercent(lbo.entry.equity_pct)}
                    />
                  </div>
                  <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
                    Entry base ({entryBaseLabel}): EBITDA{" "}
                    {fmtCurrency(lbo.entry.entry_ebitda, currency)} on revenue{" "}
                    {fmtCurrency(lbo.entry.entry_revenue, currency)}.
                  </p>
                </Card>
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
                <div className="grid gap-4 sm:grid-cols-2">
                  <StatCard
                    label="IRR"
                    value={
                      <HeroFigure value={lbo.exit.irr} format={fmtPercent} />
                    }
                    sub="Internal rate of return on sponsor equity"
                  />
                  <StatCard
                    label="MoM"
                    value={<HeroFigure value={lbo.exit.mom} format={fmtMom} />}
                    sub="Multiple of money, exit equity over sponsor equity"
                  />
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  <StatCard
                    label="Exit EBITDA"
                    value={fmtCurrency(lbo.exit.exit_ebitda, currency)}
                    sub={`Year ${lbo.assumptions.holding_period} EBITDA`}
                  />
                  <StatCard
                    label="Exit EV"
                    value={fmtCurrency(lbo.exit.exit_ev, currency)}
                    sub="Exit multiple × exit EBITDA"
                  />
                  <StatCard
                    label="Exit equity"
                    value={fmtCurrency(lbo.exit.exit_equity, currency)}
                    sub="Exit EV − ending debt + ending cash"
                  />
                </div>
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
                      IRR: entry multiple vs exit multiple
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
