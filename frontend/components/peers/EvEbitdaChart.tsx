"use client";

// EV/EBITDA peer comparison bar chart (BUILD_SPEC section 19.5): one bar per
// company, target highlighted in the accent color. Companies without an
// EV/EBITDA value are omitted; the chart hides itself when nothing remains.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
import type { PeerRow } from "@/lib/types";

interface ChartRow {
  ticker: string;
  name: string;
  value: number;
  isTarget: boolean;
}

interface EvEbitdaChartProps {
  target: PeerRow;
  peers: PeerRow[];
  height?: number;
}

export default function EvEbitdaChart({
  target,
  peers,
  height = 260,
}: EvEbitdaChartProps) {
  const chart = useChartTheme();

  const rows: ChartRow[] = [
    { peer: target, isTarget: true },
    ...peers.map((peer) => ({ peer, isTarget: false })),
  ].flatMap(({ peer, isTarget }) =>
    peer.ev_ebitda !== null
      ? [
          {
            ticker: peer.ticker,
            name: peer.name,
            value: peer.ev_ebitda,
            isTarget,
          },
        ]
      : [],
  );

  if (rows.length === 0) return null;

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
            dataKey="ticker"
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
            formatter={(value: number | string) =>
              typeof value === "number" ? fmtMultiple(value) : String(value)
            }
            labelFormatter={(label: string) => {
              const row = rows.find((r) => r.ticker === label);
              return row ? `${row.name} (${row.ticker})` : label;
            }}
            contentStyle={chart.tooltip.contentStyle}
            labelStyle={chart.tooltip.labelStyle}
            cursor={{ fill: chart.cursorFill }}
          />
          <Bar
            dataKey="value"
            name="EV / EBITDA"
            radius={[2, 2, 0, 0]}
            {...chart.animation}
          >
            {rows.map((row) => (
              <Cell
                key={row.ticker}
                fill={row.isTarget ? chart.accent : chart.brand}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
