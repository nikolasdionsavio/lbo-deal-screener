"use client";

// Screen results at workspace density. Rules rather than cards, mono tabular
// figures, every figure traceable to its filing.
//
// Colour does two separate jobs here, and they must not be confused.
//
// Column headers take their DOMAIN colour (DESIGN.md "Domain colours"), so the
// table says what kind of question each column answers: scale, profitability,
// leverage, classification. That colour marks the axis, never the value.
//
// Leverage figures additionally take a BAND colour, because under 3x, 3-5x and
// above 5x mean different things to anyone sizing a deal. The number is always
// shown alongside, so colour is never the only signal.

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import SourceDrawer, {
  type SourceRecord,
} from "@/components/source/SourceDrawer";
import { fmtDate, fmtPercent } from "@/lib/format";
import type { ScreenRow } from "@/lib/types";

/** Compact money for a dense table: $12.7m, $1.4bn. */
function money(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value))
    return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

function multiple(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value))
    return "—";
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

/** The five data domains from DESIGN.md. A column's domain says what kind of
 *  question it answers, and the header takes that colour so the table carries
 *  its own legend. */
export type Domain = "size" | "profit" | "balance" | "classify" | "quality";

export const DOMAIN_TEXT: Record<Domain, string> = {
  size: "!text-group-size",
  profit: "!text-group-profit",
  balance: "!text-group-balance",
  classify: "!text-group-classify",
  quality: "!text-group-quality",
};

export interface Column {
  key: string;
  label: string;
  /** Sortable columns map to an API sort key. */
  sortKey?: string;
  align: "left" | "right";
  /** Colours the header. Omitted for identity columns like the company name,
   *  which are not a measure of anything. */
  domain?: Domain;
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
  const scroller = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);

  // Seven columns of financials do not fit beside the filter rail on a narrow
  // desktop, so the table scrolls. Mark which way there is more to see, so a
  // half-visible Sector column reads as "keep going" rather than as a bug.
  useEffect(() => {
    const box = scroller.current;
    const edge = frame.current;
    if (!box || !edge) return;
    const update = () => {
      const remaining = box.scrollWidth - box.clientWidth - box.scrollLeft;
      edge.dataset.moreRight = remaining > 1 ? "true" : "false";
      edge.dataset.moreLeft = box.scrollLeft > 1 ? "true" : "false";
    };
    update();
    box.addEventListener("scroll", update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(box);
    return () => {
      box.removeEventListener("scroll", update);
      observer.disconnect();
    };
  }, [rows, columns]);

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
      <div ref={frame} className="scroll-frame">
        <div ref={scroller} className="scroll-x">
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
                          className={`label-mono press-tint hit-target hover:!text-ink ${
                            active
                              ? "!text-ink"
                              : col.domain
                                ? DOMAIN_TEXT[col.domain]
                                : ""
                          }`}
                        >
                          {col.label}
                          <span
                            aria-hidden
                            className="sortable-glyph"
                            data-active={active ? "true" : "false"}
                          >
                            {active
                              ? direction === "asc"
                                ? " ↑"
                                : " ↓"
                              : " ↕"}
                          </span>
                        </button>
                      ) : (
                        <span
                          className={`label-mono ${
                            col.domain ? DOMAIN_TEXT[col.domain] : ""
                          }`}
                        >
                          {col.label}
                        </span>
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
      </div>
      <SourceDrawer record={record} onClose={() => setRecord(null)} />
    </>
  );
}

export { money, multiple, leverageTone };
