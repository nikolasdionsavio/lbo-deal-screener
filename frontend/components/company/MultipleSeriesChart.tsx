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
import {
  CHART_AXIS_FONT_SIZE,
  useChartTheme,
} from "@/components/charts/chartTheme";
import { fmtMultiple } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

interface MultipleSeriesChartProps {
  data: SeriesPoint[];
  /** Series color override; defaults to the theme brand color. */
  color?: string;
  height?: number;
}

export default function MultipleSeriesChart({
  data,
  color,
  height = 240,
}: MultipleSeriesChartProps) {
  const chart = useChartTheme();
  const seriesColor = color ?? chart.brand;

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
            width={56}
            tickFormatter={(v: number) => fmtMultiple(v)}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label) => `FY${String(label)}`}
            contentStyle={chart.tooltip.contentStyle}
            labelStyle={chart.tooltip.labelStyle}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={seriesColor}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
