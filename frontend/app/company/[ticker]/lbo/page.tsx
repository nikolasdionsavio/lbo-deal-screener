"use client";

import { useEffect, useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import AssumptionsPanel from "@/components/lbo/AssumptionsPanel";
import HighlightedSensitivityTable from "@/components/lbo/HighlightedSensitivityTable";
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
import type { LboAssumptions, LboResponse, LboYear } from "@/lib/types";

/** MoM rendered as X.XXx per spec; fmtMultiple is one decimal, so not reused here. */
function fmtMom(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(2)}x`;
}

const YEAR_COLUMNS: Column<LboYear>[] = [
  { key: "year", header: "Year", render: (r) => `Year ${r.year}` },
  {
    key: "revenue",
    header: "Revenue",
    numeric: true,
    render: (r) => fmtCurrency(r.revenue),
  },
  {
    key: "ebitda",
    header: "EBITDA",
    numeric: true,
    render: (r) => fmtCurrency(r.ebitda),
  },
  {
    key: "capex",
    header: "Capex",
    numeric: true,
    render: (r) => fmtCurrency(r.capex),
  },
  {
    key: "delta_nwc",
    header: "ΔNWC",
    numeric: true,
    render: (r) => fmtCurrency(r.delta_nwc),
  },
  {
    key: "interest",
    header: "Interest",
    numeric: true,
    render: (r) => fmtCurrency(r.interest),
  },
  {
    key: "taxes",
    header: "Taxes",
    numeric: true,
    render: (r) => fmtCurrency(r.taxes),
  },
  { key: "fcf", header: "FCF", numeric: true, render: (r) => fmtCurrency(r.fcf) },
  {
    key: "debt_repaid",
    header: "Debt repaid",
    numeric: true,
    render: (r) => fmtCurrency(r.debt_repaid),
  },
  {
    key: "ending_debt",
    header: "Ending debt",
    numeric: true,
    render: (r) => fmtCurrency(r.ending_debt),
  },
  {
    key: "ending_cash",
    header: "Ending cash",
    numeric: true,
    render: (r) => fmtCurrency(r.ending_cash),
  },
];

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
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
      title="LBO Model"
      subtitle={`${profile.data_source} · Data as of ${
        profile.data_as_of ?? "not available"
      }`}
      actions={
        recomputing ? (
          <span className="text-xs text-slate-500">Recomputing…</span>
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
        <AssumptionsPanel
          values={current}
          basis={defaults.basis}
          onChange={(values) => setEdited({ ticker, values })}
          onReset={() => setEdited(null)}
        />

        <div className="min-w-0 space-y-8">
          {lboApi.error ? (
            <ErrorState message={lboApi.error.message} onRetry={lboApi.retry} />
          ) : !lbo ? (
            <LoadingState lines={10} />
          ) : (
            <>
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
                      value={fmtCurrency(lbo.entry.entry_ev)}
                    />
                    <Figure
                      label="Opening debt"
                      value={fmtCurrency(lbo.entry.opening_debt)}
                    />
                    <Figure
                      label="Sponsor equity"
                      value={fmtCurrency(lbo.entry.sponsor_equity)}
                    />
                    <Figure
                      label="Equity %"
                      value={fmtPercent(lbo.entry.equity_pct)}
                    />
                  </div>
                  <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
                    Entry base ({entryBaseLabel}): EBITDA{" "}
                    {fmtCurrency(lbo.entry.entry_ebitda)} on revenue{" "}
                    {fmtCurrency(lbo.entry.entry_revenue)}.
                  </p>
                </Card>
              </section>

              <section>
                <SectionHeader
                  title={`${lbo.assumptions.holding_period}-year projection`}
                  subtitle="All figures USD. ΔNWC is the change in net working capital."
                />
                <Card>
                  <DataTable
                    columns={YEAR_COLUMNS}
                    rows={lbo.years}
                    rowKey={(row) => row.year}
                  />
                </Card>
              </section>

              <section>
                <SectionHeader
                  title="Exit"
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
                      <span className="text-3xl">{fmtPercent(lbo.exit.irr)}</span>
                    }
                    sub="Internal rate of return on sponsor equity"
                  />
                  <StatCard
                    label="MoM"
                    value={
                      <span className="text-3xl">{fmtMom(lbo.exit.mom)}</span>
                    }
                    sub="Multiple of money, exit equity over sponsor equity"
                  />
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                  <StatCard
                    label="Exit EBITDA"
                    value={fmtCurrency(lbo.exit.exit_ebitda)}
                    sub={`Year ${lbo.assumptions.holding_period} EBITDA`}
                  />
                  <StatCard
                    label="Exit EV"
                    value={fmtCurrency(lbo.exit.exit_ev)}
                    sub="Exit multiple × exit EBITDA"
                  />
                  <StatCard
                    label="Exit equity"
                    value={fmtCurrency(lbo.exit.exit_equity)}
                    sub="Exit EV − ending debt + ending cash"
                  />
                </div>
              </section>

              <section>
                <SectionHeader
                  title="Sensitivities"
                  subtitle="The full model is recomputed for each cell. The base case cell is outlined."
                />
                <div className="space-y-5">
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      IRR: exit multiple vs revenue growth shift
                    </h3>
                    <HighlightedSensitivityTable
                      grid={lbo.sensitivities.irr_exit_vs_growth}
                      format="percent"
                      baseRow={lbo.assumptions.exit_multiple}
                      baseCol={0}
                    />
                  </Card>
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      IRR: entry multiple vs exit multiple
                    </h3>
                    <HighlightedSensitivityTable
                      grid={lbo.sensitivities.irr_entry_vs_exit}
                      format="percent"
                      baseRow={lbo.assumptions.entry_multiple}
                      baseCol={lbo.assumptions.exit_multiple}
                    />
                  </Card>
                  <Card>
                    <h3 className="mb-3 text-sm font-semibold text-ink">
                      MoM: exit multiple vs EBITDA margin shift
                    </h3>
                    <HighlightedSensitivityTable
                      grid={lbo.sensitivities.mom_exit_vs_margin}
                      format="multiple"
                      baseRow={lbo.assumptions.exit_multiple}
                      baseCol={0}
                    />
                  </Card>
                </div>
              </section>
            </>
          )}
        </div>
      </div>

      <Disclaimer />
    </div>
  );
}
