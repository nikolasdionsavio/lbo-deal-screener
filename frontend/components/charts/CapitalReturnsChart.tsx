"use client";

// Capital returns to shareholders (BUILD_SPEC section 19.5): stacked bars of
// dividends paid + share buybacks per fiscal year. Currency-aware; callers
// should hide the chart when both series are absent (render returns null too).

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
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
import type { SeriesPoint } from "@/lib/types";

interface CapitalReturnsChartProps {
  dividends?: SeriesPoint[];
  buybacks?: SeriesPoint[];
  /** Reporting currency code; null means USD. */
  currency?: string | null;
  height?: number;
}

interface Row {
  fiscal_year: number;
  dividends: number | null;
  buybacks: number | null;
}

function hasValues(points: SeriesPoint[] | undefined): points is SeriesPoint[] {
  return points !== undefined && points.some((p) => p.value !== null);
}

function mergeSeries(
  dividends: SeriesPoint[] | undefined,
  buybacks: SeriesPoint[] | undefined,
): Row[] {
  const byYear = new Map<number, Row>();
  const rowFor = (year: number): Row => {
    let row = byYear.get(year);
    if (!row) {
      row = { fiscal_year: year, dividends: null, buybacks: null };
      byYear.set(year, row);
    }
    return row;
  };
  for (const point of dividends ?? []) {
    rowFor(point.fiscal_year).dividends = point.value;
  }
  for (const point of buybacks ?? []) {
    rowFor(point.fiscal_year).buybacks = point.value;
  }
  return Array.from(byYear.values()).sort(
    (a, b) => a.fiscal_year - b.fiscal_year,
  );
}

export default function CapitalReturnsChart({
  dividends,
  buybacks,
  currency = null,
  height = 240,
}: CapitalReturnsChartProps) {
  const chart = useChartTheme();

  // Hidden when both series are absent.
  if (!hasValues(dividends) && !hasValues(buybacks)) return null;

  const rows = mergeSeries(dividends, buybacks);

  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? fmtCurrency(value, currency) : String(value);

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
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
            labelFormatter={(label) => `FY${String(label)}`}
            contentStyle={chart.tooltip.contentStyle}
            labelStyle={chart.tooltip.labelStyle}
            cursor={{ fill: chart.cursorFill }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="dividends"
            name="Dividends paid"
            stackId="returns"
            fill={chart.brand}
          />
          <Bar
            dataKey="buybacks"
            name="Share buybacks"
            stackId="returns"
            fill={chart.accent}
            radius={[2, 2, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
