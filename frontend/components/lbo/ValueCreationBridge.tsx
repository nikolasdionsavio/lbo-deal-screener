"use client";

// Value creation bridge (BUILD_SPEC section 19.6): waterfall from entry
// equity to exit equity with the exact decomposition
//   EBITDA growth effect = entry multiple x (exit EBITDA - entry EBITDA)
//   multiple effect      = (exit multiple - entry multiple) x exit EBITDA
//   deleveraging         = (opening debt - exit ending debt) + exit ending cash
// The four pieces sum exactly to exit equity; this is verified with a tiny
// epsilon and the chart renders nothing on a mismatch rather than showing a
// wrong bridge. Floating bars are drawn as stacked bars over a transparent
// base series.

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
  type ChartTheme,
} from "@/components/charts/chartTheme";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import { fmtCurrency } from "@/lib/format";
import type { LboResponse } from "@/lib/types";

type RowKind = "total" | "increase" | "decrease";

interface BridgeRow {
  label: string;
  /** Invisible offset under the floating bar. */
  base: number;
  /** Rendered (always non-negative) bar height. */
  size: number;
  /** Signed delta for steps, absolute amount for endpoints. */
  display: number;
  kind: RowKind;
}

function rowColor(kind: RowKind, chart: ChartTheme): string {
  if (kind === "total") return chart.brand;
  return kind === "increase" ? chart.accent : chart.negative;
}

function totalRow(label: string, value: number): BridgeRow {
  return {
    label,
    base: Math.min(0, value),
    size: Math.abs(value),
    display: value,
    kind: "total",
  };
}

function stepRow(label: string, start: number, delta: number): BridgeRow {
  const end = start + delta;
  return {
    label,
    base: Math.min(start, end),
    size: Math.abs(delta),
    display: delta,
    kind: delta < 0 ? "decrease" : "increase",
  };
}

interface BridgeTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: BridgeRow }>;
  currency: string | null;
}

function BridgeTooltip({ active, payload, currency }: BridgeTooltipProps) {
  if (!active || payload === undefined || payload.length === 0) return null;
  const row = payload[0].payload;
  const signed =
    row.kind !== "total" && row.display > 0
      ? `+${fmtCurrency(row.display, currency)}`
      : fmtCurrency(row.display, currency);
  return (
    <div className="rounded border border-line-strong bg-surface px-3 py-2 text-xs shadow-card">
      <div className="font-medium text-ink">{row.label}</div>
      <div className="mt-0.5 tabular-nums text-ink-secondary">{signed}</div>
    </div>
  );
}

interface ValueCreationBridgeProps {
  lbo: LboResponse;
  /** Reporting currency code; null means USD. */
  currency?: string | null;
  height?: number;
}

export default function ValueCreationBridge({
  lbo,
  currency = null,
  height = 280,
}: ValueCreationBridgeProps) {
  const chart = useChartTheme();
  const { entry, exit, assumptions } = lbo;

  // The waterfall decomposes value on a single EV/EBITDA basis at both ends.
  // On the revenue basis the entry has no EBITDA multiple (entry EBITDA is
  // negative), so the decomposition is meaningless — suppress it rather than
  // show a bridge that does not reconcile. The sensitivity range carries the
  // value story for these deals instead.
  if (assumptions.valuation_basis === "revenue") {
    return null;
  }

  const entryEquity = entry.sponsor_equity; // cash invested, incl. fees
  const fees = entry.transaction_fees;
  const entryEbitda = entry.entry_ebitda;
  const openingDebt = entry.opening_debt;
  const exitEquity = exit.exit_equity;
  const exitEbitda = exit.exit_ebitda;
  const endingDebt = exit.ending_debt;
  const endingCash = exit.ending_cash;

  // Hidden when any decomposition input is missing.
  if (
    entryEquity === null ||
    fees === null ||
    entryEbitda === null ||
    openingDebt === null ||
    exitEquity === null ||
    exitEbitda === null ||
    endingDebt === null ||
    endingCash === null
  ) {
    return null;
  }

  // Sponsor equity includes transaction fees; strip them first to recover the
  // business entry equity (EV − debt) that the three value levers act on.
  const businessEntryEquity = entryEquity - fees;
  const ebitdaGrowthEffect =
    assumptions.entry_multiple * (exitEbitda - entryEbitda);
  const multipleEffect =
    (assumptions.exit_multiple - assumptions.entry_multiple) * exitEbitda;
  const deleveraging = openingDebt - endingDebt + endingCash;

  // The decomposition is algebraically exact: sponsor equity, less fees, plus
  // the three effects must reproduce exit equity. If it does not (within a tiny
  // epsilon), render nothing rather than a wrong chart.
  const reconstructed =
    businessEntryEquity + ebitdaGrowthEffect + multipleEffect + deleveraging;
  const epsilon = 1e-6 * Math.max(1, Math.abs(exitEquity));
  if (!Number.isFinite(reconstructed) || Math.abs(reconstructed - exitEquity) > epsilon) {
    return null;
  }

  const afterGrowth = businessEntryEquity + ebitdaGrowthEffect;
  const afterMultiple = afterGrowth + multipleEffect;

  const rows: BridgeRow[] = [
    totalRow("Sponsor equity", entryEquity),
    stepRow("Transaction fees", entryEquity, -fees),
    stepRow("EBITDA growth", businessEntryEquity, ebitdaGrowthEffect),
    stepRow("Multiple effect", afterGrowth, multipleEffect),
    stepRow("Deleveraging", afterMultiple, deleveraging),
    totalRow("Exit equity", exitEquity),
  ];

  return (
    <section>
      <SectionHeader
        title="Value creation"
        subtitle="Decomposition of the change in sponsor equity from entry to exit"
      />
      <Card>
        <div style={{ width: "100%", height }}>
          <ResponsiveContainer>
            <BarChart
              data={rows}
              margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={chart.grid}
                vertical={false}
              />
              <XAxis
                dataKey="label"
                stroke={chart.axis}
                fontSize={CHART_AXIS_FONT_SIZE}
                tickLine={false}
                interval={0}
              />
              <YAxis
                stroke={chart.axis}
                fontSize={CHART_AXIS_FONT_SIZE}
                tickLine={false}
                width={72}
                tickFormatter={(v: number) => fmtCurrency(v, currency)}
              />
              <Tooltip
                content={<BridgeTooltip currency={currency} />}
                cursor={{ fill: chart.cursorFill }}
              />
              <Bar
                dataKey="base"
                stackId="bridge"
                fill="transparent"
                {...chart.animation}
              />
              <Bar
                dataKey="size"
                stackId="bridge"
                radius={[2, 2, 0, 0]}
                {...chart.animation}
              >
                {rows.map((row) => (
                  <Cell key={row.label} fill={rowColor(row.kind, chart)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 border-t border-line pt-3 text-xs text-ink-muted">
          Exit equity = sponsor equity − transaction fees + entry multiple ×
          (exit EBITDA − entry EBITDA) + (exit multiple − entry multiple) × exit
          EBITDA + (debt repaid + ending cash).
        </p>
      </Card>
    </section>
  );
}
