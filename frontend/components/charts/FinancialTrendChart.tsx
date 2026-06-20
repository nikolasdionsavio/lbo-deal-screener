"use client";

// Financial trend chart (BUILD_SPEC section 19.6): revenue bars with an
// EBITDA-margin line on a secondary percent axis, computed client-side from
// GET /api/companies/{ticker}/financials (fetched lazily by this component).
// Years without revenue are skipped; the whole section is hidden while the
// data loads, on error, and whenever fewer than two valued years remain.

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CHART_AXIS_FONT_SIZE,
  useChartTheme,
} from "@/components/charts/chartTheme";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { fmtCurrency, fmtPercent } from "@/lib/format";
import type { FinancialsResponse } from "@/lib/types";

const REVENUE_NAME = "Revenue";
const MARGIN_NAME = "EBITDA margin";

interface ChartRow {
  fiscal_year: number;
  revenue: number;
  margin: number | null;
}

interface FinancialTrendChartProps {
  /** Multi-year financials, fetched once by the parent; null while loading. */
  financials: FinancialsResponse | null;
  /** Reporting currency code; null means USD. */
  currency?: string | null;
  height?: number;
}

export default function FinancialTrendChart({
  financials,
  currency = null,
  height = 260,
}: FinancialTrendChartProps) {
  const data = financials;
  const chart = useChartTheme();

  // Hidden while loading and on error; the dashboard reads fine without it.
  if (data === null) return null;

  const rows: ChartRow[] = data.years
    .flatMap((year) =>
      year.revenue !== null && Number.isFinite(year.revenue)
        ? [
            {
              fiscal_year: year.fiscal_year,
              revenue: year.revenue,
              margin:
                year.ebitda !== null && year.revenue !== 0
                  ? year.ebitda / year.revenue
                  : null,
            },
          ]
        : [],
    )
    .sort((a, b) => a.fiscal_year - b.fiscal_year);

  // Hidden entirely when fewer than two years carry revenue.
  if (rows.length < 2) return null;

  const tooltipFormatter = (
    value: number | string,
    name: string,
  ): string => {
    if (typeof value !== "number") return String(value);
    return name === MARGIN_NAME
      ? fmtPercent(value)
      : fmtCurrency(value, currency);
  };

  return (
    <section className="divider-dashed mt-8 pt-8">
      <SectionHeader
        title="Financial trend"
        subtitle={`Revenue and EBITDA margin by fiscal year · Source: ${data.data_source}`}
      />
      <Card>
        <div style={{ width: "100%", height }}>
          <ResponsiveContainer>
            <ComposedChart
              data={rows}
              margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={chart.grid}
                vertical={false}
              />
              <XAxis
                dataKey="fiscal_year"
                stroke={chart.axis}
                fontSize={CHART_AXIS_FONT_SIZE}
                tickLine={false}
                tickFormatter={(v: number) => `FY${v}`}
              />
              <YAxis
                yAxisId="revenue"
                stroke={chart.axis}
                fontSize={CHART_AXIS_FONT_SIZE}
                tickLine={false}
                width={72}
                tickFormatter={(v: number) => fmtCurrency(v, currency)}
              />
              <YAxis
                yAxisId="margin"
                orientation="right"
                stroke={chart.axis}
                fontSize={CHART_AXIS_FONT_SIZE}
                tickLine={false}
                width={56}
                tickFormatter={(v: number) => fmtPercent(v, { digits: 0 })}
              />
              <Tooltip
                formatter={tooltipFormatter}
                labelFormatter={(label) => `FY${String(label)}`}
                contentStyle={chart.tooltip.contentStyle}
                labelStyle={chart.tooltip.labelStyle}
                cursor={{ fill: chart.cursorFill }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar
                yAxisId="revenue"
                dataKey="revenue"
                name={REVENUE_NAME}
                fill={chart.brand}
                radius={[2, 2, 0, 0]}
              />
              <Line
                yAxisId="margin"
                dataKey="margin"
                name={MARGIN_NAME}
                stroke={chart.accent}
                strokeWidth={2}
                dot={{ r: 3, fill: chart.accent, strokeWidth: 0 }}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </section>
  );
}
