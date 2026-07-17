"use client";

// KPI dashboard: traceable KPI table (KPI / Value / Period / Formula, with
// inputs shown via title tooltip and warnings as inline amber badges) plus
// fiscal-year trend charts. Data from GET /api/companies/{ticker}/kpis.
// The 14 KPIs render as one table with four quiet group subheads
// (BUILD_SPEC section 19.7): Growth, Margins, Cash flow, Leverage & returns.

import { Fragment, useState } from "react";
import SourceDrawer, {
  type SourceRecord,
} from "@/components/source/SourceDrawer";
import CapitalReturnsChart from "@/components/charts/CapitalReturnsChart";
import MarginChart, {
  type MarginSeries,
} from "@/components/charts/MarginChart";
import TimeSeriesChart from "@/components/charts/TimeSeriesChart";
import { useCompany } from "@/components/company/CompanyContext";
import MultipleSeriesChart from "@/components/company/MultipleSeriesChart";
import Card from "@/components/ui/Card";
import DataTable, { type Column } from "@/components/ui/DataTable";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import { getKpis } from "@/lib/api";
import {
  fmtCurrency,
  fmtDays,
  fmtMultiple,
  fmtNumber,
  fmtPercent,
} from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SeriesPoint, TracedValue } from "@/lib/types";

function fmtTraced(kpi: TracedValue, currency: string | null): string {
  if (kpi.value === null) return "—";
  switch (kpi.unit) {
    case "percent":
      return fmtPercent(kpi.value);
    case "multiple":
      return fmtMultiple(kpi.value);
    case "ratio":
      return fmtNumber(kpi.value, { digits: 2 });
    case "days":
      return fmtDays(kpi.value);
    case "currency":
    case "per_share":
      return fmtCurrency(kpi.value, currency);
  }
}

function fmtInputValue(value: number | null, currency: string | null): string {
  if (value === null) return "—";
  // KPI inputs are predominantly monetary; small magnitudes (ratios, rates)
  // are shown as plain numbers.
  if (Math.abs(value) >= 1e5) return fmtCurrency(value, currency);
  return fmtNumber(value, { digits: 2 });
}

function inputsTitle(kpi: TracedValue, currency: string | null): string {
  if (kpi.inputs.length === 0) return "No recorded inputs";
  return (
    "Inputs: " +
    kpi.inputs
      .map(
        (input) =>
          `${input.field} = ${fmtInputValue(input.value, currency)} (${
            input.period
          })`,
      )
      .join("; ")
  );
}

/** A KPI as a source record: it is a calculated value, so the drawer leads with
 *  the formula and lists each reported input. */
function kpiRecord(kpi: TracedValue, currency: string | null): SourceRecord {
  return {
    metric: kpi.label,
    displayValue: fmtTraced(kpi, currency),
    classification: "calculated",
    period: kpi.period,
    statement: "Operating & credit KPI",
    formula: kpi.formula,
    inputs: kpi.inputs.map((input) => ({
      label: `${input.field} · ${input.period}`,
      value: fmtInputValue(input.value, currency),
    })),
    note: "Computed by the app from filed figures. Each input is a reported line item; open Financials to see them in the statements.",
  };
}

function kpiColumns(
  currency: string | null,
  onInspect: (record: SourceRecord) => void,
): Column<TracedValue>[] {
  return [
    {
      key: "kpi",
      header: "KPI",
      render: (kpi) => (
        <div title={inputsTitle(kpi, currency)}>
          <span className="font-medium text-ink underline decoration-line-strong decoration-dotted underline-offset-2">
            {kpi.label}
          </span>
          {kpi.warnings.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {kpi.warnings.map((warning, i) => (
                <span
                  key={i}
                  className="inline-flex items-center rounded-full border border-transparent bg-warn-soft px-2 py-0.5 text-[11px] text-warn-text"
                >
                  {warning}
                </span>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "value",
      header: "Value",
      numeric: true,
      render: (kpi) =>
        kpi.value === null ? (
          <span className="font-mono text-ink-muted" title="Not available">
            n/a
          </span>
        ) : (
          <button
            type="button"
            onClick={() => onInspect(kpiRecord(kpi, currency))}
            title={`${kpi.label} — calculated. Open source record.`}
            className="font-mono font-medium text-ink underline decoration-line-strong decoration-dotted underline-offset-[3px] transition-colors hover:text-brand-text focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
          >
            {fmtTraced(kpi, currency)}
          </button>
        ),
    },
    {
      key: "period",
      header: "Period",
      render: (kpi) => <span className="text-ink-secondary">{kpi.period}</span>,
    },
    {
      key: "formula",
      header: "Formula",
      render: (kpi) => <span className="text-ink-muted">{kpi.formula}</span>,
    },
  ];
}

// Section 19.7 grouping of the 14 KPIs. Keys missing from a payload are
// skipped; keys outside the groups fall into a trailing "Other" section so
// nothing the API sends is silently dropped.
const KPI_GROUPS: { label: string; keys: string[] }[] = [
  { label: "Growth", keys: ["revenue_growth_yoy", "revenue_cagr_3y"] },
  {
    label: "Margins",
    keys: ["gross_margin", "ebitda_margin", "net_income_margin", "fcf_margin"],
  },
  {
    label: "Cash flow",
    keys: ["fcf_conversion", "capex_pct_revenue", "nwc_pct_revenue"],
  },
  {
    label: "Leverage & returns",
    keys: [
      "net_debt_to_ebitda",
      "debt_to_ebitda",
      "interest_coverage",
      "roic",
      "current_ratio",
    ],
  },
];

/** One table, four sections: quiet subhead rows between the traced rows. */
function GroupedKpiTable({
  kpis,
  currency,
  onInspect,
}: {
  kpis: TracedValue[];
  currency: string | null;
  onInspect: (record: SourceRecord) => void;
}) {
  const columns = kpiColumns(currency, onInspect);
  const byKey = new Map(kpis.map((kpi) => [kpi.key, kpi]));
  const groups = KPI_GROUPS.map((group) => ({
    label: group.label,
    rows: group.keys.flatMap((key) => {
      const kpi = byKey.get(key);
      return kpi !== undefined ? [kpi] : [];
    }),
  })).filter((group) => group.rows.length > 0);

  const groupedKeys = new Set(KPI_GROUPS.flatMap((group) => group.keys));
  const leftover = kpis.filter((kpi) => !groupedKeys.has(kpi.key));
  if (leftover.length > 0) groups.push({ label: "Other", rows: leftover });

  return (
    <div className="scroll-x">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-3 py-2 text-xs font-medium text-ink-muted ${
                  col.numeric ? "text-right" : "text-left"
                }`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group.label}>
              <tr>
                <th
                  colSpan={columns.length}
                  scope="colgroup"
                  className="px-3 pb-1.5 pt-4 text-left font-mono text-[10px] uppercase tracking-[0.04em] text-ink-muted"
                >
                  {group.label}
                </th>
              </tr>
              {group.rows.map((kpi) => (
                <tr
                  key={kpi.key}
                  className="border-b border-line transition-colors duration-150 last:border-b-0 hover:bg-brand-soft"
                >
                  {columns.map((col, index) => (
                    <td
                      key={col.key}
                      className={`px-3 py-2 ${
                        col.numeric ? "text-right tabular-nums" : "text-left"
                      }`}
                    >
                      {col.render(kpi, index)}
                    </td>
                  ))}
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const CURRENCY_CHARTS = [
  { key: "revenue", title: "Revenue" },
  { key: "ebitda", title: "EBITDA" },
  { key: "free_cash_flow", title: "Free cash flow" },
  { key: "total_debt", title: "Total debt" },
];

const MARGIN_DEFS = [
  { key: "gross_margin", name: "Gross margin" },
  { key: "ebitda_margin", name: "EBITDA margin" },
  { key: "net_income_margin", name: "Net income margin" },
  { key: "fcf_margin", name: "FCF margin" },
];

function hasData(points: SeriesPoint[]): boolean {
  return points.length > 0 && points.some((p) => p.value !== null);
}

export default function KpisPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const currency = profile.currency ?? null;
  const { data, error, loading, retry } = useApi(
    () => getKpis(ticker),
    [ticker],
  );
  const [record, setRecord] = useState<SourceRecord | null>(null);

  if (loading) {
    return <LoadingState lines={8} />;
  }
  if (error !== null || data === null) {
    return (
      <ErrorState
        message={
          error !== null ? error.message : `Could not load KPIs for ${ticker}.`
        }
        onRetry={retry}
      />
    );
  }

  const series = data.series;
  const currencyCharts = CURRENCY_CHARTS.flatMap((chart) => {
    const points = series[chart.key];
    return points !== undefined && hasData(points)
      ? [{ ...chart, points }]
      : [];
  });
  const marginSeries: MarginSeries[] = MARGIN_DEFS.flatMap((def) => {
    const points = series[def.key];
    return points !== undefined && hasData(points)
      ? [{ name: def.name, data: points }]
      : [];
  });
  const leverage = series["net_debt_to_ebitda"];
  const showLeverage = leverage !== undefined && hasData(leverage);
  const dividends = series["dividends_paid"];
  const buybacks = series["share_buybacks"];
  const showCapitalReturns =
    (dividends !== undefined && hasData(dividends)) ||
    (buybacks !== undefined && hasData(buybacks));
  const showCharts =
    currencyCharts.length > 0 ||
    marginSeries.length > 0 ||
    showLeverage ||
    showCapitalReturns;
  const diagnostics = data.diagnostics ?? [];

  return (
    // fade-in: the LoadingState resolving to the KPI content.
    <div className="fade-in">
      <section>
        <SectionHeader
          variant="page"
          as="h2"
          title="Key performance indicators"
          subtitle="Fourteen traced metrics; every value carries its formula, inputs, and period."
        />
        <Card>
          <GroupedKpiTable
            kpis={data.kpis}
            currency={currency}
            onInspect={setRecord}
          />
          <p className="mt-3 text-xs text-ink-muted">
            Click any value for its source record: the formula and the reported
            inputs behind it.
          </p>
        </Card>
      </section>

      {diagnostics.length > 0 && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader
            title="PE diagnostics"
            subtitle="Working-capital efficiency and capital-return metrics, latest fiscal year"
          />
          <Card>
            <DataTable
              columns={kpiColumns(currency, setRecord)}
              rows={diagnostics}
              rowKey={(kpi) => kpi.key}
            />
            <p className="mt-3 text-xs text-ink-muted">
              Hover a metric name to see the inputs behind the calculation.
            </p>
          </Card>
        </section>
      )}

      {showCharts && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader
            title="Trends"
            subtitle="Fiscal-year series from reported and derived financials"
          />
          <div className="grid gap-5 lg:grid-cols-2">
            {currencyCharts.map((chart) => (
              <Card key={chart.key}>
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  {chart.title}
                </h3>
                <TimeSeriesChart
                  data={chart.points}
                  format="currency"
                  currency={currency}
                />
              </Card>
            ))}
            {marginSeries.length > 0 && (
              <Card>
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  Margins
                </h3>
                <MarginChart series={marginSeries} />
              </Card>
            )}
            {showLeverage && (
              <Card>
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  Net debt / EBITDA
                </h3>
                <MultipleSeriesChart data={leverage} />
              </Card>
            )}
            {showCapitalReturns && (
              <Card>
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  Capital returns
                </h3>
                <CapitalReturnsChart
                  dividends={dividends}
                  buybacks={buybacks}
                  currency={currency}
                />
              </Card>
            )}
          </div>
        </section>
      )}

      <Disclaimer />
      <SourceDrawer record={record} onClose={() => setRecord(null)} />
    </div>
  );
}
