"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtPercent } from "@/lib/format";
import type { SeriesPoint } from "@/lib/types";

export interface MarginSeries {
  name: string;
  data: SeriesPoint[];
}

interface MarginChartProps {
  series: MarginSeries[];
  height?: number;
}

const COLORS = ["#1e3a5f", "#0d9488", "#b45309", "#b91c1c", "#475569"];

type Row = Record<string, number | null> & { fiscal_year: number };

function mergeSeries(series: MarginSeries[]): Row[] {
  const byYear = new Map<number, Row>();
  for (const s of series) {
    for (const point of s.data) {
      let row = byYear.get(point.fiscal_year);
      if (!row) {
        row = { fiscal_year: point.fiscal_year };
        byYear.set(point.fiscal_year, row);
      }
      row[s.name] = point.value;
    }
  }
  return Array.from(byYear.values()).sort(
    (a, b) => a.fiscal_year - b.fiscal_year,
  );
}

export default function MarginChart({ series, height = 260 }: MarginChartProps) {
  const rows = mergeSeries(series);

  const tooltipFormatter = (value: number | string): string =>
    typeof value === "number" ? fmtPercent(value) : String(value);

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="fiscal_year" stroke="#64748b" fontSize={12} tickLine={false} />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) => fmtPercent(v)}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label) => `FY${String(label)}`}
            contentStyle={{ fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Line
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
