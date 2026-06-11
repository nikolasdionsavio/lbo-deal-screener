"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtCurrency, fmtPercent } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

interface TimeSeriesChartProps {
  data: SeriesPoint[];
  format: "currency" | "percent";
  variant?: "line" | "bar";
  color?: string;
  height?: number;
}

export default function TimeSeriesChart({
  data,
  format,
  variant = "bar",
  color = "#1e3a5f",
  height = 240,
}: TimeSeriesChartProps) {
  const formatValue = (v: number): string =>
    format === "currency" ? fmtCurrency(v) : fmtPercent(v);

  const axisProps = {
    stroke: "#64748b",
    fontSize: 12,
    tickLine: false,
  } as const;

  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? formatValue(value) : String(value);

  const chartChildren = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
      <XAxis dataKey="fiscal_year" {...axisProps} />
      <YAxis
        {...axisProps}
        width={72}
        tickFormatter={(v: number) => formatValue(v)}
      />
      <Tooltip
        formatter={tooltipFormatter}
        labelFormatter={(label) => `FY${String(label)}`}
        contentStyle={{ fontSize: 12 }}
      />
    </>
  );

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        {variant === "bar" ? (
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            {chartChildren}
            <Bar dataKey="value" fill={color} radius={[2, 2, 0, 0]} />
          </BarChart>
        ) : (
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            {chartChildren}
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
