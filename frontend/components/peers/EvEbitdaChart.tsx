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
import { fmtMultiple } from "@/lib/format";
import type { PeerRow } from "@/lib/types";

const BRAND = "#1e3a5f";
const ACCENT = "#0d9488";

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
            stroke="#e2e8f0"
            vertical={false}
          />
          <XAxis
            dataKey="ticker"
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
            formatter={(value: number | string) =>
              typeof value === "number" ? fmtMultiple(value) : String(value)
            }
            labelFormatter={(label: string) => {
              const row = rows.find((r) => r.ticker === label);
              return row ? `${row.name} (${row.ticker})` : label;
            }}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="value" name="EV / EBITDA" radius={[2, 2, 0, 0]}>
            {rows.map((row) => (
              <Cell
                key={row.ticker}
                fill={row.isTarget ? ACCENT : BRAND}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
