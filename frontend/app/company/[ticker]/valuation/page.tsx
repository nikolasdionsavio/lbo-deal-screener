"use client";

import { useEffect, useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import AssumptionField from "@/components/ui/AssumptionField";
import Card from "@/components/ui/Card";
import DataTable, { type Column } from "@/components/ui/DataTable";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import MultiplesGrid from "@/components/valuation/MultiplesGrid";
import { runValuation } from "@/lib/api";
import { fmtCurrency, fmtMultiple, fmtPercent } from "@/lib/format";
import { useApi, useDebounced } from "@/lib/hooks";
import type { ValuationAssumptions, ValuationCase } from "@/lib/types";

function caseLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function PremiumCell({ value }: { value: number | null }) {
  const color =
    value === null ? "" : value > 0 ? "text-accent" : value < 0 ? "text-negative" : "";
  return <span className={color}>{fmtPercent(value, { signed: true })}</span>;
}

// All monetary columns are in the company's reporting currency
// (BUILD_SPEC section 4 currency contract); implied share price uses the
// same code as implied EV/equity.
function rangeColumns(currency: string | null): Column<ValuationCase>[] {
  return [
    { key: "case", header: "Case", render: (row) => caseLabel(row.case) },
    {
      key: "multiple",
      header: "EV/EBITDA",
      numeric: true,
      render: (row) => fmtMultiple(row.multiple),
    },
    {
      key: "implied_ev",
      header: "Implied EV",
      numeric: true,
      render: (row) => fmtCurrency(row.implied_ev, currency),
    },
    {
      key: "implied_equity",
      header: "Implied equity",
      numeric: true,
      render: (row) => fmtCurrency(row.implied_equity, currency),
    },
    {
      key: "implied_share_price",
      header: "Implied share price",
      numeric: true,
      render: (row) => fmtCurrency(row.implied_share_price, currency),
    },
    {
      key: "premium_vs_current",
      header: "Premium vs current",
      numeric: true,
      render: (row) => <PremiumCell value={row.premium_vs_current} />,
    },
  ];
}

export default function ValuationPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const currency = profile.currency ?? null;

  useEffect(() => {
    window.localStorage.setItem("lastTicker", ticker);
  }, [ticker]);

  // Edits are keyed by ticker so stale assumptions from a previous company are
  // never posted (or displayed) after navigation.
  const [edited, setEdited] = useState<{
    ticker: string;
    values: ValuationAssumptions;
  } | null>(null);
  const debounced = useDebounced(edited, 400);

  const editedValues = edited && edited.ticker === ticker ? edited.values : null;
  const debouncedValues =
    debounced && debounced.ticker === ticker ? debounced.values : null;

  const { data, error, loading, retry } = useApi(
    () => runValuation(ticker, debouncedValues ?? {}),
    [ticker, debouncedValues],
  );

  // Fields are initialised from the response defaults and stay visible while
  // recomputing or after a failed recompute.
  const assumptions = editedValues ?? data?.assumptions ?? null;
  const recomputing = loading && data !== null;

  function setAssumption(field: keyof ValuationAssumptions, value: number) {
    if (!assumptions) return;
    const next = { ...assumptions };
    next[field] = value;
    setEdited({ ticker, values: next });
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        title="Valuation"
        subtitle={`${profile.data_source} · Data as of ${
          profile.data_as_of ?? "not available"
        }`}
        actions={
          recomputing ? (
            <span className="text-xs text-slate-500">Recomputing…</span>
          ) : undefined
        }
      />

      {data && data.warnings.length > 0 && <WarningList warnings={data.warnings} />}

      {loading && !data && <LoadingState lines={6} />}
      {error && !assumptions && (
        <ErrorState message={error.message} onRetry={retry} />
      )}

      {data && (
        <section>
          <SectionHeader
            title="Current multiples"
            subtitle={`As of ${data.as_of}`}
          />
          <MultiplesGrid multiples={data.multiples} currency={currency} />
        </section>
      )}

      {assumptions && (
        <section>
          <SectionHeader
            title="Valuation range"
            subtitle="EV/EBITDA multiples applied to latest fiscal year EBITDA. Implied equity = implied EV less net debt."
          />
          <Card>
            <div className="grid max-w-md grid-cols-3 gap-3">
              <AssumptionField
                label="Low"
                value={assumptions.low}
                unit="x"
                step={0.5}
                min={0}
                onChange={(v) => setAssumption("low", v)}
              />
              <AssumptionField
                label="Base"
                value={assumptions.base}
                unit="x"
                step={0.5}
                min={0}
                onChange={(v) => setAssumption("base", v)}
              />
              <AssumptionField
                label="High"
                value={assumptions.high}
                unit="x"
                step={0.5}
                min={0}
                onChange={(v) => setAssumption("high", v)}
              />
            </div>
            <div className="mt-5">
              {error ? (
                <ErrorState message={error.message} onRetry={retry} />
              ) : data ? (
                <DataTable
                  columns={rangeColumns(currency)}
                  rows={data.range}
                  rowKey={(row) => row.case}
                />
              ) : (
                <LoadingState lines={3} />
              )}
            </div>
          </Card>
        </section>
      )}

      <Disclaimer />
    </div>
  );
}
