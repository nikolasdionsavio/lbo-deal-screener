"use client";

// Debt paydown chart (BUILD_SPEC section 19.6): ending debt bars plus an
// ending cash line over years 0..N, where year 0 is the opening debt with
// zero cash. Currency-aware; hides itself when the opening debt or the
// projection years are missing.

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
import { fmtCurrency } from "@/lib/format";
import type { LboYear } from "@/lib/types";

interface ChartRow {
  year: number;
  ending_debt: number;
  ending_cash: number;
}

interface DebtPaydownChartProps {
  openingDebt: number | null;
  years: LboYear[];
  /** Reporting currency code; null means USD. */
  currency?: string | null;
  height?: number;
}

export default function DebtPaydownChart({
  openingDebt,
  years,
  currency = null,
  height = 260,
}: DebtPaydownChartProps) {
  const chart = useChartTheme();

  // Hidden when the entry debt or the projection is missing.
  if (openingDebt === null || !Number.isFinite(openingDebt)) return null;
  if (years.length === 0) return null;

  const rows: ChartRow[] = [
    { year: 0, ending_debt: openingDebt, ending_cash: 0 },
    ...years.map((y) => ({
      year: y.year,
      ending_debt: y.ending_debt,
      ending_cash: y.ending_cash,
    })),
  ];

  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? fmtCurrency(value, currency) : String(value);

  return (
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
            dataKey="year"
            stroke={chart.axis}
            fontSize={CHART_AXIS_FONT_SIZE}
            tickLine={false}
            tickFormatter={(v: number) => `Y${v}`}
          />
          <YAxis
            stroke={chart.axis}
            fontSize={CHART_AXIS_FONT_SIZE}
            tickLine={false}
            width={72}
            tickFormatter={(v: number) => fmtCurrency(v, currency)}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label) => `Year ${String(label)}`}
            contentStyle={chart.tooltip.contentStyle}
            labelStyle={chart.tooltip.labelStyle}
            cursor={{ fill: chart.cursorFill }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="ending_debt"
            name="Ending debt"
            fill={chart.brand}
            radius={[2, 2, 0, 0]}
            {...chart.animation}
          />
          <Line
            dataKey="ending_cash"
            name="Ending cash"
            stroke={chart.accent}
            strokeWidth={2}
            dot={{ r: 3, fill: chart.accent, strokeWidth: 0 }}
            {...chart.animation}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
