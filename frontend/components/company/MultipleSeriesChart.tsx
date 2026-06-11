"use client";

// Line chart for multiple-denominated series (e.g. net debt / EBITDA).
// The shared TimeSeriesChart wrapper only supports "currency" and "percent"
// formats, so this local wrapper mirrors its styling with "x" tick labels.

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtMultiple } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

interface MultipleSeriesChartProps {
  data: SeriesPoint[];
  color?: string;
  height?: number;
}

export default function MultipleSeriesChart({
  data,
  color = "#1e3a5f",
  height = 240,
}: MultipleSeriesChartProps) {
  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? fmtMultiple(value) : String(value);

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
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
            width={56}
            tickFormatter={(v: number) => fmtMultiple(v)}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label) => `FY${String(label)}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
