"use client";

// Screen results at workspace density: rules rather than cards, mono tabular
// figures, and every figure traceable. Clicking a number opens the source
// record showing which XBRL tag it came from and, for EBITDA, the arithmetic.

import Link from "next/link";
import { useState } from "react";
import SourceDrawer, { type SourceRecord } from "@/components/source/SourceDrawer";
import { fmtDate, fmtPercent } from "@/lib/format";
import type { ScreenRow } from "@/lib/types";

/** Compact money for a dense table: $12.7m, $1.4bn. */
function money(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

const SORTABLE: { key: string; label: string; numeric: boolean }[] = [
  { key: "entity_name", label: "Company", numeric: false },
  { key: "revenue", label: "Revenue", numeric: true },
  { key: "ebitda", label: "EBITDA", numeric: true },
  { key: "ebitda_margin", label: "Margin", numeric: true },
];

function periodLabel(row: ScreenRow): string {
  const year = row.period.replace("CY", "");
  return row.period_end ? `${year} · to ${fmtDate(row.period_end)}` : year;
}

/** The provenance record behind one figure. */
function buildRecord(row: ScreenRow, field: "revenue" | "ebitda"): SourceRecord {
  const filing = {
    filing: "Annual report (10-K / 20-F), XBRL company facts",
    sourceUrl: row.filing_url ?? undefined,
    sourceLabel: row.filing_url ? "Open the filing on SEC EDGAR" : undefined,
    period: periodLabel(row),
    unit: "USD, reported in full",
    statement: "Income statement",
  };

  if (field === "revenue") {
    return {
      ...filing,
      metric: "Revenue",
      displayValue: money(row.revenue),
      classification: "filed",
      note:
        row.revenue_tag === "Revenues"
          ? "Taken from the total revenue tag."
          : "Taken from the revenue-from-contracts tag, which this filer uses " +
            "as its revenue line. It excludes any non-contract revenue.",
    };
  }

  if (row.ebitda === null) {
    return {
      ...filing,
      metric: "EBITDA",
      displayValue: "Not disclosed",
      classification: "missing",
      note:
        row.coverage === "ebit_only"
          ? "EBITDA cannot be calculated: this filer does not tag depreciation " +
            "and amortisation separately. Operating income is " +
            `${money(row.operating_income)}, but adding an assumed D&A figure ` +
            "would be a guess, so nothing is shown."
          : "This filer disclosed revenue but not operating income for the period.",
    };
  }

  return {
    ...filing,
    metric: "EBITDA",
    displayValue: money(row.ebitda),
    classification: "calculated",
    formula: "Operating income + depreciation and amortisation",
    inputs: [
      { label: "Operating income", value: money(row.operating_income) },
      { label: "D&A", value: money(row.depreciation_amortization) },
    ],
    note:
      row.quality_flag === "ebitda_exceeds_revenue"
        ? "EBITDA exceeds revenue here, which normally means a one-off gain " +
          "sits inside reported operating income. Treat it as a filing " +
          "artifact rather than an operating margin, and check the filing."
        : undefined,
  };
}

function FigureButton({
  row,
  field,
  onOpen,
}: {
  row: ScreenRow;
  field: "revenue" | "ebitda";
  onOpen: (record: SourceRecord) => void;
}) {
  const value = field === "revenue" ? row.revenue : row.ebitda;
  const undisclosed = value === null;
  return (
    <button
      type="button"
      onClick={() => onOpen(buildRecord(row, field))}
      title="Show where this figure came from"
      className={`w-full whitespace-nowrap text-right font-mono text-[0.8125rem] tabular-nums underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent ${
        undisclosed ? "text-ink-muted" : "text-ink"
      }`}
    >
      {undisclosed ? "not disclosed" : money(value)}
    </button>
  );
}

export default function ScreenTable({
  rows,
  sort,
  direction,
  onSort,
}: {
  rows: ScreenRow[];
  sort: string;
  direction: "asc" | "desc";
  onSort: (key: string) => void;
}) {
  const [record, setRecord] = useState<SourceRecord | null>(null);

  if (rows.length === 0) {
    return (
      <p className="border-t border-line py-10 text-center text-[0.875rem] text-ink-secondary">
        No companies match these criteria. Widen the revenue band, or clear the
        EBITDA filter to include filers that do not disclose D&amp;A.
      </p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        {/* Sized to fit beside the filter rail at desktop width; narrower
            viewports scroll the table rather than crushing the figures. */}
        <table className="w-full min-w-[40rem] border-collapse text-left">
          <thead>
            <tr className="border-y border-line-strong">
              {SORTABLE.map((col) => {
                const active = sort === col.key;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={`py-2 font-mono text-[11px] font-normal uppercase tracking-[0.04em] ${
                      col.numeric ? "text-right" : "text-left"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onSort(col.key)}
                      aria-sort={
                        active
                          ? direction === "asc"
                            ? "ascending"
                            : "descending"
                          : "none"
                      }
                      // Font is restated here: the global button reset would
                      // otherwise drop the mono/uppercase set on the cell.
                      className={`whitespace-nowrap font-mono text-[11px] uppercase tracking-[0.04em] transition-colors hover:text-ink ${
                        active ? "text-ink" : "text-ink-muted"
                      }`}
                    >
                      {col.label}
                      {active && (
                        <span aria-hidden="true">
                          {direction === "asc" ? " ↑" : " ↓"}
                        </span>
                      )}
                    </button>
                  </th>
                );
              })}
              <th
                scope="col"
                className="py-2 pl-5 text-left font-mono text-[11px] font-normal uppercase tracking-[0.04em] text-ink-muted"
              >
                Sector
              </th>
              <th
                scope="col"
                className="w-[4.5rem] whitespace-nowrap py-2 pl-3 text-right font-mono text-[11px] font-normal uppercase tracking-[0.04em] text-ink-muted"
              >
                Period
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.cik} className="border-b border-line align-baseline">
                <td className="py-2 pr-4">
                  <div className="flex items-baseline gap-2">
                    {row.ticker ? (
                      <Link
                        href={`/company/${encodeURIComponent(row.ticker)}/dashboard`}
                        className="font-mono text-[0.8125rem] text-link underline-offset-2 hover:underline"
                      >
                        {row.ticker}
                      </Link>
                    ) : (
                      <span className="font-mono text-[0.8125rem] text-ink-muted">
                        —
                      </span>
                    )}
                    <span className="text-[0.8125rem] text-ink">{row.name}</span>
                    {row.quality_flag && (
                      <span
                        title={row.quality_note ?? undefined}
                        className="border border-assumption px-1 font-mono text-[10px] leading-4 text-assumption"
                      >
                        one-off gain
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-2 pl-2">
                  <FigureButton row={row} field="revenue" onOpen={setRecord} />
                </td>
                <td className="py-2 pl-2">
                  <FigureButton row={row} field="ebitda" onOpen={setRecord} />
                </td>
                <td className="whitespace-nowrap py-2 pl-3 text-right font-mono text-[0.8125rem] tabular-nums text-ink-secondary">
                  {row.ebitda_margin === null ? "—" : fmtPercent(row.ebitda_margin)}
                </td>
                <td className="max-w-[13rem] truncate py-2 pl-5 text-[0.8125rem] text-ink-secondary">
                  {row.sector ?? "—"}
                </td>
                <td className="whitespace-nowrap py-2 pl-3 text-right font-mono text-[11px] text-ink-muted">
                  {row.period.replace("CY", "FY")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SourceDrawer record={record} onClose={() => setRecord(null)} />
    </>
  );
}
