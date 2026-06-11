import { fmtMultiple, fmtPercent } from "@/lib/format";
import type { SensitivityGrid } from "@/lib/types";

type AxisFormat = "multiple" | "shift" | "raw";

interface SensitivityTableProps {
  grid: SensitivityGrid;
  format: "percent" | "multiple";
  /** How to format row axis values (e.g. "multiple" for EV/EBITDA rows). */
  rowFormat?: AxisFormat;
  /** How to format column axis values ("shift" renders -0.04 as "-4 pp"). */
  colFormat?: AxisFormat;
  /** Axis value (not index) of the base-case row; omitted = no highlight. */
  baseRow?: number;
  /** Axis value (not index) of the base-case column; omitted = no highlight. */
  baseCol?: number;
  className?: string;
}

// Cell shading: green for high values, red for low values, relative to the
// grid min/max, in up to three alpha steps. Hues and the per-step alpha come
// from theme-scoped CSS variables (see app/globals.css: --sens-positive-rgb,
// --sens-negative-rgb, --sens-alpha-step), so the tint adapts to light and
// dark and keeps the cell text at >=4.5:1 in both. Dark mode uses a slightly
// stronger step (0.15 vs 0.12) under its light ink.
function cellBackground(
  value: number | null,
  min: number,
  max: number,
): string | undefined {
  if (value === null || max <= min) return undefined;
  const t = (value - min) / (max - min); // 0 = worst, 1 = best
  const signed = (t - 0.5) * 2; // -1 .. 1
  const steps = Math.round(Math.abs(signed) * 3); // 0..3 alpha steps
  if (steps === 0) return undefined;
  const rgbVar = signed > 0 ? "--sens-positive-rgb" : "--sens-negative-rgb";
  return `rgba(var(${rgbVar}), calc(var(--sens-alpha-step) * ${steps}))`;
}

function fmtAxisValue(v: number, axisFormat: AxisFormat): string {
  if (axisFormat === "multiple") return fmtMultiple(v);
  if (axisFormat === "shift") {
    const pp = v * 100;
    const rounded = Math.round(pp * 10) / 10;
    const text = Number.isInteger(rounded)
      ? rounded.toFixed(0)
      : rounded.toFixed(1);
    return `${rounded > 0 ? "+" : ""}${text} pp`;
  }
  if (Number.isInteger(v)) return v.toString();
  return v.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function axisIndex(axis: number[], target: number | undefined): number {
  if (target === undefined) return -1;
  return axis.findIndex((v) => Math.abs(v - target) < 1e-6);
}

export default function SensitivityTable({
  grid,
  format,
  rowFormat = "raw",
  colFormat = "raw",
  baseRow,
  baseCol,
  className = "",
}: SensitivityTableProps) {
  const fmtCell = format === "percent" ? fmtPercent : fmtMultiple;

  const flat = grid.values
    .flat()
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const min = flat.length > 0 ? Math.min(...flat) : 0;
  const max = flat.length > 0 ? Math.max(...flat) : 0;

  const baseRowIndex = axisIndex(grid.rows, baseRow);
  const baseColIndex = axisIndex(grid.cols, baseCol);

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th
              scope="col"
              className="px-3 py-2 text-left text-xs font-medium text-ink-muted"
            >
              {grid.row_label} \ {grid.col_label}
            </th>
            {grid.cols.map((col, j) => (
              <th
                key={j}
                scope="col"
                className="px-3 py-2 text-right text-xs font-medium tabular-nums text-ink-muted"
              >
                {fmtAxisValue(col, colFormat)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row, i) => (
            <tr key={i} className="border-t border-line">
              <th
                scope="row"
                className="px-3 py-2 text-left text-xs font-medium tabular-nums text-ink-secondary"
              >
                {fmtAxisValue(row, rowFormat)}
              </th>
              {grid.cols.map((_, j) => {
                const value = grid.values[i]?.[j] ?? null;
                const isBase = i === baseRowIndex && j === baseColIndex;
                return (
                  <td
                    key={j}
                    className={`px-3 py-2 text-right tabular-nums ${
                      isBase
                        ? "font-semibold outline outline-2 -outline-offset-2 outline-brand"
                        : ""
                    }`}
                    style={{ backgroundColor: cellBackground(value, min, max) }}
                  >
                    {value === null ? "—" : fmtCell(value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
