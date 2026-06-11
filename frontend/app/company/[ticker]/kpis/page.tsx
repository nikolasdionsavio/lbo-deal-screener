"use client";

// KPI dashboard: traceable KPI table (KPI / Value / Period / Formula, with
// inputs shown via title tooltip and warnings as inline amber badges) plus
// fiscal-year trend charts. Data from GET /api/companies/{ticker}/kpis.

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

function kpiColumns(currency: string | null): Column<TracedValue>[] {
  return [
    {
      key: "kpi",
      header: "KPI",
      render: (kpi) => (
        <div title={inputsTitle(kpi, currency)}>
          <span className="font-medium text-ink underline decoration-slate-300 decoration-dotted underline-offset-2">
            {kpi.label}
          </span>
          {kpi.warnings.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {kpi.warnings.map((warning, i) => (
                <span
                  key={i}
                  className="inline-flex items-center rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[11px] text-warn"
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
      render: (kpi) => (
        <span
          className="font-medium text-ink"
          title={kpi.value === null ? "Not available" : undefined}
        >
          {fmtTraced(kpi, currency)}
        </span>
      ),
    },
    {
      key: "period",
      header: "Period",
      render: (kpi) => <span className="text-slate-600">{kpi.period}</span>,
    },
    {
      key: "formula",
      header: "Formula",
      render: (kpi) => <span className="text-slate-500">{kpi.formula}</span>,
    },
  ];
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
    <div>
      <section>
        <SectionHeader
          title="Key performance indicators"
          subtitle={`Source: ${data.data_source} · Data as of ${data.as_of}`}
        />
        <Card>
          <DataTable
            columns={kpiColumns(currency)}
            rows={data.kpis}
            rowKey={(kpi) => kpi.key}
          />
          <p className="mt-3 text-xs text-slate-500">
            Hover a KPI name to see the inputs behind the calculation.
          </p>
        </Card>
      </section>

      {diagnostics.length > 0 && (
        <section className="mt-10">
          <SectionHeader
            title="PE diagnostics"
            subtitle="Working-capital efficiency and capital-return metrics, latest fiscal year"
          />
          <Card>
            <DataTable
              columns={kpiColumns(currency)}
              rows={diagnostics}
              rowKey={(kpi) => kpi.key}
            />
            <p className="mt-3 text-xs text-slate-500">
              Hover a metric name to see the inputs behind the calculation.
            </p>
          </Card>
        </section>
      )}

      {showCharts && (
        <section className="mt-10">
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
    </div>
  );
}
