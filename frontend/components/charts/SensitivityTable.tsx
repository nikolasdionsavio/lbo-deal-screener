import { fmtMultiple, fmtPercent } from "@/lib/format";
import type { SensitivityGrid } from "@/lib/types";

interface SensitivityTableProps {
  grid: SensitivityGrid;
  format: "percent" | "multiple";
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

export default function SensitivityTable({
  grid,
  format,
  className = "",
}: SensitivityTableProps) {
  const fmtCell = format === "percent" ? fmtPercent : fmtMultiple;

  const flat = grid.values
    .flat()
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const min = flat.length > 0 ? Math.min(...flat) : 0;
  const max = flat.length > 0 ? Math.max(...flat) : 0;

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
                return (
                  <td
                    key={j}
                    className="px-3 py-2 text-right tabular-nums"
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
