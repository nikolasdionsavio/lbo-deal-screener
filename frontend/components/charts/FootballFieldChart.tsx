"use client";

// Football field chart (BUILD_SPEC section 19.6): horizontal bars for the
// low/base/high implied enterprise values from the valuation range, with a
// reference line at the current enterprise value. Currency-aware; cases
// without an implied EV are omitted and the chart hides itself when nothing
// remains.

import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CHART_AXIS_FONT_SIZE,
  useChartTheme,
} from "@/components/charts/chartTheme";
import { fmtCurrency, fmtMultiple } from "@/lib/format";
import type { ValuationCase } from "@/lib/types";

interface ChartRow {
  label: string;
  implied_ev: number;
  multiple: number;
}

interface FootballFieldChartProps {
  range: ValuationCase[];
  /** Current enterprise value; the reference line is omitted when null. */
  currentEv: number | null;
  /** Reporting currency code; null means USD. */
  currency?: string | null;
  height?: number;
}

function caseLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function FootballFieldChart({
  range,
  currentEv,
  currency = null,
  height = 220,
}: FootballFieldChartProps) {
  const chart = useChartTheme();

  const rows: ChartRow[] = range.flatMap((row) =>
    row.implied_ev !== null && Number.isFinite(row.implied_ev)
      ? [
          {
            label: caseLabel(row.case),
            implied_ev: row.implied_ev,
            multiple: row.multiple,
          },
        ]
      : [],
  );

  // Hidden when no case carries an implied EV.
  if (rows.length === 0) return null;

  const refEv =
    currentEv !== null && Number.isFinite(currentEv) ? currentEv : null;

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 20, right: 24, bottom: 0, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chart.grid}
            horizontal={false}
          />
          <XAxis
            type="number"
            stroke={chart.axis}
            fontSize={CHART_AXIS_FONT_SIZE}
            tickLine={false}
            // Keep the reference line inside the plot even when the current
            // EV sits beyond the highest implied EV.
            domain={[
              0,
              (dataMax: number) =>
                Math.max(dataMax, refEv ?? 0) * 1.05,
            ]}
            tickFormatter={(v: number) => fmtCurrency(v, currency)}
          />
          <YAxis
            type="category"
            dataKey="label"
            stroke={chart.axis}
            fontSize={CHART_AXIS_FONT_SIZE}
            tickLine={false}
            width={48}
          />
          <Tooltip
            formatter={(value: number | string) =>
              typeof value === "number"
                ? fmtCurrency(value, currency)
                : String(value)
            }
            labelFormatter={(label: string) => {
              const row = rows.find((r) => r.label === label);
              return row
                ? `${row.label} · ${fmtMultiple(row.multiple)} EV/EBITDA`
                : label;
            }}
            contentStyle={chart.tooltip.contentStyle}
            labelStyle={chart.tooltip.labelStyle}
            cursor={{ fill: chart.cursorFill }}
          />
          <Bar
            dataKey="implied_ev"
            name="Implied EV"
            fill={chart.brand}
            barSize={22}
            radius={[0, 2, 2, 0]}
            {...chart.animation}
          />
          {refEv !== null && (
            <ReferenceLine
              x={refEv}
              stroke={chart.reference}
              strokeDasharray="4 4"
              label={{
                value: "Current EV",
                position: "top",
                fontSize: 11,
                fill: chart.reference,
              }}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
