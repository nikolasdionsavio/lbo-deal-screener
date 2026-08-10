"use client";

// Screen results at workspace density. Rules rather than cards, mono tabular
// figures, every figure traceable to its filing.
//
// Colour is used once, on leverage, because leverage is read by band: under 3x,
// 3-5x and above 5x mean different things to anyone sizing a deal. The number
// is always shown alongside, so colour is never the only signal.

import Link from "next/link";
import { useState } from "react";
import SourceDrawer, { type SourceRecord } from "@/components/source/SourceDrawer";
import { fmtDate, fmtPercent } from "@/lib/format";
import type { ScreenRow } from "@/lib/types";

/** Compact money for a dense table: $12.7m, $1.4bn. */
function money(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

function multiple(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${value.toFixed(1)}x`;
}

/** Credit-convention bands. Net cash reads as conservative, not as an error. */
function leverageTone(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-ink-muted";
  if (value < 3) return "text-lev-low";
  if (value <= 5) return "text-lev-mid";
  return "text-lev-high";
}

/** Passed to every cell so a figure can open its own provenance record. */
export interface CellContext {
  openSource: (record: SourceRecord) => void;
}

export interface Column {
  key: string;
  label: string;
  /** Sortable columns map to an API sort key. */
  sortKey?: string;
  align: "left" | "right";
  render: (row: ScreenRow, ctx: CellContext) => React.ReactNode;
}

export default function ScreenTable({
  rows,
  columns,
  sort,
  direction,
  onSort,
}: {
  rows: ScreenRow[];
  columns: Column[];
  sort: string;
  direction: "asc" | "desc";
  onSort: (key: string) => void;
}) {
  const [record, setRecord] = useState<SourceRecord | null>(null);

  if (rows.length === 0) {
    return (
      <p className="border-y border-line-strong py-10 text-center text-[0.9375rem] text-ink-secondary">
        No companies match these criteria. Widen a range, or clear an EBITDA
        filter to include filers that do not disclose D&amp;A.
      </p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[48rem] border-collapse text-left">
          <thead>
            <tr className="border-y-2 border-line-strong">
              {columns.map((col, index) => {
                const active = col.sortKey && sort === col.sortKey;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={`whitespace-nowrap py-2 ${
                      col.align === "right"
                        ? "pl-4 text-right"
                        : index === 0
                          ? "pr-3 text-left"
                          : "pl-5 pr-3 text-left"
                    }`}
                    aria-sort={
                      active
                        ? direction === "asc"
                          ? "ascending"
                          : "descending"
                        : undefined
                    }
                  >
                    {col.sortKey ? (
                      <button
                        type="button"
                        onClick={() => onSort(col.sortKey as string)}
                        className={`label-mono press-tint hover:!text-ink ${
                          active ? "!text-ink" : ""
                        }`}
                      >
                        {col.label}
                        <span aria-hidden className={active ? "" : "opacity-0"}>
                          {direction === "asc" ? " ↑" : " ↓"}
                        </span>
                      </button>
                    ) : (
                      <span className="label-mono">{col.label}</span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.cik}
                className="border-b border-line align-baseline transition-colors hover:bg-surface"
              >
                {columns.map((col, index) => (
                  <td
                    key={col.key}
                    className={`py-2 ${
                      col.align === "right"
                        ? "whitespace-nowrap pl-4 text-right"
                        : index === 0
                          ? "pr-3"
                          : "pl-5 pr-3"
                    }`}
                  >
                    {col.render(row, { openSource: setRecord })}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SourceDrawer record={record} onClose={() => setRecord(null)} />
    </>
  );
}

export { money, multiple, leverageTone };
