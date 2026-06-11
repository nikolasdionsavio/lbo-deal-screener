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
            stroke="#e2e8f0"
            vertical={false}
          />
          <XAxis
            dataKey="fiscal_year"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            width={72}
            tickFormatter={(v: number) => fmtCurrency(v, currency)}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label) => `FY${String(label)}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="dividends"
            name="Dividends paid"
            stackId="returns"
            fill="#1e3a5f"
          />
          <Bar
            dataKey="buybacks"
            name="Share buybacks"
            stackId="returns"
            fill="#0d9488"
            radius={[2, 2, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
