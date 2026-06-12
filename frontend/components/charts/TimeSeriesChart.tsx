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
import {
  CHART_AXIS_FONT_SIZE,
  useChartTheme,
} from "@/components/charts/chartTheme";
import { fmtCurrency, fmtPercent } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

interface TimeSeriesChartProps {
  data: SeriesPoint[];
  format: "currency" | "percent";
  /** Reporting currency code for currency-formatted axes; null means USD. */
  currency?: string | null;
  variant?: "line" | "bar";
  /** Series color override; defaults to the theme brand color. */
  color?: string;
  height?: number;
}

export default function TimeSeriesChart({
  data,
  format,
  currency = null,
  variant = "bar",
  color,
  height = 240,
}: TimeSeriesChartProps) {
  const chart = useChartTheme();
  const seriesColor = color ?? chart.brand;

  const formatValue = (v: number): string =>
    format === "currency" ? fmtCurrency(v, currency) : fmtPercent(v);

  const axisProps = {
    stroke: chart.axis,
    fontSize: CHART_AXIS_FONT_SIZE,
    tickLine: false,
  } as const;

  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? formatValue(value) : String(value);

  const chartChildren = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} vertical={false} />
      <XAxis dataKey="fiscal_year" {...axisProps} />
      <YAxis
        {...axisProps}
        width={72}
        tickFormatter={(v: number) => formatValue(v)}
      />
      <Tooltip
        formatter={tooltipFormatter}
        labelFormatter={(label) => `FY${String(label)}`}
        contentStyle={chart.tooltip.contentStyle}
        labelStyle={chart.tooltip.labelStyle}
        cursor={variant === "bar" ? { fill: chart.cursorFill } : undefined}
      />
    </>
  );

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        {variant === "bar" ? (
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            {chartChildren}
            <Bar
              dataKey="value"
              fill={seriesColor}
              radius={[2, 2, 0, 0]}
              {...chart.animation}
            />
          </BarChart>
        ) : (
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            {chartChildren}
            <Line
              type="monotone"
              dataKey="value"
              stroke={seriesColor}
              strokeWidth={2}
              dot={{ r: 3 }}
              {...chart.animation}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
