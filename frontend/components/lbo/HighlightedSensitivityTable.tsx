import { fmtMultiple, fmtPercent } from "@/lib/format";
import type { SensitivityGrid } from "@/lib/types";

// Local extension of components/charts/SensitivityTable (read-only UI kit):
// identical green/red shading, plus an outlined base-case cell located by the
// row/col axis values of the current assumptions. The kit component exposes no
// base-cell prop, so the rendering is duplicated here rather than edited there.

interface HighlightedSensitivityTableProps {
  grid: SensitivityGrid;
  format: "percent" | "multiple";
  /** Axis value (not index) of the base-case row; omitted = no highlight. */
  baseRow?: number;
  /** Axis value (not index) of the base-case column; omitted = no highlight. */
  baseCol?: number;
  className?: string;
}

// Cell shading: green (#0d9488) for high values, red (#b91c1c) for low values,
// relative to the grid min/max, in 12% alpha steps.
const GREEN_RGB = "13, 148, 136";
const RED_RGB = "185, 28, 28";
const ALPHA_STEP = 0.12;

function cellBackground(
  value: number | null,
  min: number,
  max: number,
): string | undefined {
  if (value === null || max <= min) return undefined;
  const t = (value - min) / (max - min); // 0 = worst, 1 = best
  const signed = (t - 0.5) * 2; // -1 .. 1
  const steps = Math.round(Math.abs(signed) * 3); // 0..3 steps of 12% alpha
  if (steps === 0) return undefined;
  const rgb = signed > 0 ? GREEN_RGB : RED_RGB;
  return `rgba(${rgb}, ${(steps * ALPHA_STEP).toFixed(2)})`;
}

function fmtAxisValue(v: number): string {
  if (Number.isInteger(v)) return v.toString();
  return v.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function axisIndex(axis: number[], target: number | undefined): number {
  if (target === undefined) return -1;
  return axis.findIndex((v) => Math.abs(v - target) < 1e-6);
}

export default function HighlightedSensitivityTable({
  grid,
  format,
  baseRow,
  baseCol,
  className = "",
}: HighlightedSensitivityTableProps) {
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
              className="px-3 py-2 text-left text-xs font-semibold text-slate-500"
            >
              {grid.row_label} \ {grid.col_label}
            </th>
            {grid.cols.map((col, j) => (
              <th
                key={j}
                scope="col"
                className="px-3 py-2 text-right text-xs font-semibold tabular-nums text-slate-500"
              >
                {fmtAxisValue(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              <th
                scope="row"
                className="px-3 py-2 text-left text-xs font-semibold tabular-nums text-slate-600"
              >
                {fmtAxisValue(row)}
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
