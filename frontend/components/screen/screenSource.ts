// Provenance records for screen figures.
//
// Kept apart from the table so the column definitions can build a record for
// any metric without the table knowing what the metrics are. Every record says
// which XBRL concept the number came from, and for derived figures it shows the
// arithmetic and the inputs rather than asserting a result.

import type { SourceRecord } from "@/components/source/SourceDrawer";
import { fmtDate } from "@/lib/format";
import type { ScreenRow } from "@/lib/types";

function money(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

function base(row: ScreenRow) {
  const year = row.period.replace("CY", "");
  return {
    filing: "Annual report (10-K / 20-F), XBRL company facts",
    sourceUrl: row.filing_url ?? undefined,
    sourceLabel: row.filing_url ? "Open the filing on SEC EDGAR" : undefined,
    period: row.period_end ? `${year} · to ${fmtDate(row.period_end)}` : year,
    unit: "USD, reported in full",
  };
}

export type MetricKey =
  | "revenue"
  | "ebitda"
  | "net_income"
  | "gross_margin"
  | "net_debt"
  | "leverage"
  | "cash"
  | "assets";

export function buildRecord(row: ScreenRow, metric: MetricKey): SourceRecord {
  const common = base(row);

  if (metric === "revenue") {
    return {
      ...common,
      statement: "Income statement",
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

  if (metric === "ebitda") {
    if (row.ebitda === null) {
      return {
        ...common,
        statement: "Income statement",
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
      ...common,
      statement: "Income statement",
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

  if (metric === "leverage") {
    if (row.leverage === null || row.leverage === undefined) {
      return {
        ...common,
        statement: "Derived",
        metric: "Net debt / EBITDA",
        displayValue: "Not available",
        classification: "missing",
        note:
          row.ebitda === null
            ? "EBITDA is not available for this filer, so no multiple can be formed."
            : row.ebitda !== null && row.ebitda <= 0
              ? "EBITDA is zero or negative for this period. A leverage multiple " +
                "against it would be arithmetic without meaning, so none is shown."
              : "Net debt is unavailable: this filer does not tag cash separately.",
      };
    }
    return {
      ...common,
      statement: "Derived",
      metric: "Net debt / EBITDA",
      displayValue: `${row.leverage.toFixed(1)}x`,
      classification: "calculated",
      formula: "(Total debt − cash) ÷ EBITDA",
      inputs: [
        { label: "Total debt", value: money(row.total_debt) },
        { label: "Cash", value: money(row.cash) },
        { label: "Net debt", value: money(row.net_debt) },
        { label: "EBITDA", value: money(row.ebitda) },
      ],
      note:
        "Balance-sheet figures are taken at the reporting instant closest to " +
        "this period's end, which for a non-calendar year end is not 31 December.",
    };
  }

  if (metric === "net_debt") {
    if (row.net_debt === null || row.net_debt === undefined) {
      return {
        ...common,
        statement: "Balance sheet",
        metric: "Net debt",
        displayValue: "Not available",
        classification: "missing",
        note:
          "This filer does not tag cash separately, so debt cannot be netted. " +
          "Showing gross debt as net debt would overstate leverage.",
      };
    }
    return {
      ...common,
      statement: "Balance sheet",
      metric: "Net debt",
      displayValue: money(row.net_debt),
      classification: "calculated",
      formula: "Total debt − cash and equivalents",
      inputs: [
        { label: "Total debt", value: money(row.total_debt) },
        { label: "Cash", value: money(row.cash) },
      ],
      note:
        row.net_debt < 0
          ? "Negative net debt means the company holds more cash than debt."
          : undefined,
    };
  }

  if (metric === "gross_margin") {
    if (row.gross_margin === null || row.gross_margin === undefined) {
      return {
        ...common,
        statement: "Income statement",
        metric: "Gross margin",
        displayValue: "Not disclosed",
        classification: "missing",
        note: "This filer does not tag gross profit separately.",
      };
    }
    return {
      ...common,
      statement: "Income statement",
      metric: "Gross margin",
      displayValue: `${(row.gross_margin * 100).toFixed(1)}%`,
      classification: "calculated",
      formula: "Gross profit ÷ revenue",
      inputs: [
        { label: "Gross profit", value: money(row.gross_profit) },
        { label: "Revenue", value: money(row.revenue) },
      ],
    };
  }

  if (metric === "net_income") {
    return {
      ...common,
      statement: "Income statement",
      metric: "Net income",
      displayValue: money(row.net_income),
      classification: row.net_income === null ? "missing" : "filed",
      note:
        row.net_income === null
          ? "This filer does not tag net income for the period."
          : undefined,
    };
  }

  const label = metric === "cash" ? "Cash and equivalents" : "Total assets";
  const value = metric === "cash" ? row.cash : row.assets;
  return {
    ...common,
    statement: "Balance sheet",
    metric: label,
    displayValue: money(value),
    classification: value === null || value === undefined ? "missing" : "filed",
    note:
      "Taken at the reporting instant closest to this period's end, which for a " +
      "non-calendar year end is not 31 December.",
  };
}
