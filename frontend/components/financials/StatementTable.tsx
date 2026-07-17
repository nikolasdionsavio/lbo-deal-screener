// Annual statement table (BUILD_SPEC sections 19.7/19.8): years as columns
// newest-left, line items as rows in filing order, sticky first column over
// horizontal scroll, one consistent scale per table (millions or billions,
// chosen from the max magnitude) noted in the top-left header cell.
//
// Section 19.8 row plans: components are indented under their subtotal;
// quiet subtotals (gross profit, operating income, EBITDA, pretax, current
// assets/liabilities, the cash-flow group totals) carry a hairline top rule
// and 600 weight; strong subtotals (net income, total assets/liabilities/
// equity) carry a line-strong top rule. EPS renders as an exact per-share
// figure and diluted shares as a count in millions ("m"), neither
// currency-scaled. Rows that are null across every shown year are hidden.
// Derived values carry a superscript dagger with a single footnote line;
// null renders as an em dash.

import type {
  BalanceSheetLines,
  CashFlowLines,
  IncomeStatementLines,
  StatementYear,
} from "@/lib/types";
import { fmtDate, fmtPerShare, fmtShareCount } from "@/lib/format";
import type { SourceRecord } from "@/components/source/SourceDrawer";

export type StatementKey = "income_statement" | "balance_sheet" | "cash_flow";

const STATEMENT_LABEL: Record<StatementKey, string> = {
  income_statement: "Income statement",
  balance_sheet: "Balance sheet",
  cash_flow: "Cash flow statement",
};

type RowStyle = "item" | "subtotal" | "strong";
type RowFormat = "money" | "per_share" | "shares";

interface LineDef {
  key: string;
  label: string;
  /** Component lines are indented under the subtotal they roll into. */
  indent?: boolean;
  style?: RowStyle;
  /** "money" (default) follows the table scale; the others never do. */
  format?: RowFormat;
}

// Filing order per the section 19.8 response shape.
const LINES: Record<StatementKey, LineDef[]> = {
  income_statement: [
    { key: "revenue", label: "Revenue" },
    { key: "cost_of_revenue", label: "Cost of revenue", indent: true },
    { key: "gross_profit", label: "Gross profit", style: "subtotal" },
    {
      key: "research_development",
      label: "Research & development",
      indent: true,
    },
    {
      key: "selling_general_admin",
      label: "Selling, general & administrative",
      indent: true,
    },
    { key: "operating_income", label: "Operating income", style: "subtotal" },
    {
      key: "depreciation_amortization",
      label: "Depreciation & amortization",
    },
    { key: "ebitda", label: "EBITDA", style: "subtotal" },
    { key: "interest_expense", label: "Interest expense" },
    { key: "pretax_income", label: "Pretax income", style: "subtotal" },
    { key: "tax_expense", label: "Tax expense" },
    { key: "net_income", label: "Net income", style: "strong" },
    { key: "eps_basic", label: "EPS, basic", format: "per_share" },
    { key: "eps_diluted", label: "EPS, diluted", format: "per_share" },
    { key: "shares_diluted", label: "Diluted shares", format: "shares" },
  ],
  balance_sheet: [
    { key: "cash_and_equivalents", label: "Cash & equivalents", indent: true },
    { key: "receivables", label: "Receivables", indent: true },
    { key: "inventory", label: "Inventory", indent: true },
    { key: "current_assets", label: "Current assets", style: "subtotal" },
    {
      key: "ppe_net",
      label: "Property, plant & equipment, net",
      indent: true,
    },
    { key: "goodwill", label: "Goodwill", indent: true },
    { key: "intangible_assets", label: "Intangible assets", indent: true },
    { key: "total_assets", label: "Total assets", style: "strong" },
    { key: "accounts_payable", label: "Accounts payable", indent: true },
    {
      key: "current_liabilities",
      label: "Current liabilities",
      style: "subtotal",
    },
    { key: "long_term_debt", label: "Long-term debt", indent: true },
    { key: "total_debt", label: "Total debt", style: "subtotal" },
    { key: "total_liabilities", label: "Total liabilities", style: "strong" },
    { key: "retained_earnings", label: "Retained earnings", indent: true },
    { key: "total_equity", label: "Total equity", style: "strong" },
  ],
  cash_flow: [
    {
      key: "stock_based_compensation",
      label: "Stock-based compensation",
      indent: true,
    },
    {
      key: "operating_cash_flow",
      label: "Operating cash flow",
      style: "subtotal",
    },
    { key: "capex", label: "Capital expenditure", indent: true },
    {
      key: "investing_cash_flow",
      label: "Investing cash flow",
      style: "subtotal",
    },
    { key: "dividends_paid", label: "Dividends paid", indent: true },
    { key: "share_buybacks", label: "Share buybacks", indent: true },
    {
      key: "financing_cash_flow",
      label: "Financing cash flow",
      style: "subtotal",
    },
    { key: "free_cash_flow", label: "Free cash flow", style: "subtotal" },
  ],
};

type StatementLines = IncomeStatementLines & BalanceSheetLines & CashFlowLines;

function lineValue(
  year: StatementYear,
  statement: StatementKey,
  key: string,
): number | null {
  const block = year[statement] as Partial<StatementLines>;
  const value = block[key as keyof StatementLines];
  return value === undefined ? null : value;
}

interface Scale {
  divisor: number;
  /** Unit note for the header cell, e.g. "USD millions". */
  label: string;
  digits: number;
}

/** One scale per table, chosen from the largest money magnitude shown. */
function chooseScale(
  years: StatementYear[],
  statement: StatementKey,
  lines: LineDef[],
  currency: string | null,
): Scale {
  let maxAbs = 0;
  for (const year of years) {
    for (const line of lines) {
      if (line.format !== undefined && line.format !== "money") continue;
      const value = lineValue(year, statement, line.key);
      if (value !== null && Number.isFinite(value)) {
        maxAbs = Math.max(maxAbs, Math.abs(value));
      }
    }
  }
  const code = currency ?? "USD";
  if (maxAbs >= 1e10) {
    return { divisor: 1e9, label: `${code} billions`, digits: 1 };
  }
  return {
    divisor: 1e6,
    label: `${code} millions`,
    digits: maxAbs >= 1e9 ? 0 : 1,
  };
}

function fmtScaled(value: number | null, scale: Scale): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return (value / scale.divisor).toLocaleString("en-US", {
    minimumFractionDigits: scale.digits,
    maximumFractionDigits: scale.digits,
  });
}

function fmtCell(
  value: number | null,
  line: LineDef,
  scale: Scale,
  currency: string | null,
): string {
  if (line.format === "per_share") return fmtPerShare(value, currency);
  if (line.format === "shares") return fmtShareCount(value);
  return fmtScaled(value, scale);
}

// Row borders: line items flow without dividers; subtotal rows draw the
// accountant's rule above the total (border-top, so it never collides with
// a previous row's border under border-collapse).
const ROW_BORDER: Record<RowStyle, string> = {
  item: "",
  subtotal: "border-t border-line",
  strong: "border-t border-line-strong",
};

const ROW_TEXT: Record<RowStyle, string> = {
  item: "text-ink-secondary",
  subtotal: "font-semibold text-ink",
  strong: "font-semibold text-ink",
};

// Sticky first column: opaque surface base so scrolled cells never show
// through; on row hover a brand-soft gradient layer reproduces the
// translucent row tint over that opaque base.
const STICKY_CELL =
  "sticky left-0 z-10 whitespace-nowrap bg-surface " +
  "group-hover:[background-image:linear-gradient(var(--brand-soft),var(--brand-soft))]";

interface StatementTableProps {
  statement: StatementKey;
  /** Fiscal years, newest first (rendered left to right as given). */
  years: StatementYear[];
  currency: string | null;
  className?: string;
  /** Opens the source record for a cell (makes values clickable). */
  onInspect?: (record: SourceRecord) => void;
  /** SEC EDGAR filing list for the issuer, linked from each source record. */
  filingsUrl?: string;
}

export default function StatementTable({
  statement,
  years,
  currency,
  className = "",
  onInspect,
  filingsUrl,
}: StatementTableProps) {
  // Hide rows that carry no value in any shown year (older backends and
  // sparse filers simply lack the line).
  const lines = LINES[statement].filter((line) =>
    years.some((year) => lineValue(year, statement, line.key) !== null),
  );
  const scale = chooseScale(years, statement, lines, currency);
  const hasDerived = years.some((year) =>
    lines.some(
      (line) =>
        year.derived_fields.includes(line.key) &&
        lineValue(year, statement, line.key) !== null,
    ),
  );

  return (
    <div className={className}>
      <div className="scroll-x">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line">
              <th
                scope="col"
                className={`${STICKY_CELL} min-w-[12rem] px-3 py-2 text-left text-xs font-medium text-ink-muted`}
              >
                {scale.label}
              </th>
              {years.map((year) => (
                <th
                  key={year.fiscal_year}
                  scope="col"
                  className="whitespace-nowrap px-3 py-2 text-right align-bottom text-xs font-medium text-ink-muted"
                >
                  <div className="tabular-nums text-ink-secondary">
                    FY{year.fiscal_year}
                  </div>
                  {year.period_end !== null && (
                    <div className="mt-0.5 text-[11px] font-normal tabular-nums">
                      {fmtDate(year.period_end)}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => {
              const style = line.style ?? "item";
              return (
                <tr
                  key={line.key}
                  className={`group transition-colors duration-150 hover:bg-brand-soft ${ROW_BORDER[style]}`}
                >
                  <th
                    scope="row"
                    className={`${STICKY_CELL} h-8 py-0 pr-3 text-left font-normal group-hover:text-ink ${
                      line.indent === true ? "pl-7" : "pl-3"
                    } ${ROW_TEXT[style]}`}
                  >
                    {line.label}
                  </th>
                  {years.map((year) => {
                    const value = lineValue(year, statement, line.key);
                    const derived =
                      value !== null && year.derived_fields.includes(line.key);
                    const display = fmtCell(value, line, scale, currency);

                    if (value === null) {
                      return (
                        <td
                          key={year.fiscal_year}
                          className="h-8 whitespace-nowrap px-3 py-0 text-right font-mono text-[12px] tabular-nums text-ink-muted"
                          title="Not reported for this period"
                        >
                          n/a
                        </td>
                      );
                    }

                    const cellText = `font-mono text-[12px] tabular-nums group-hover:text-ink ${ROW_TEXT[style]}`;
                    // Calculated values carry a dotted underline; filed values
                    // are plain ink (DESIGN.md source-state treatment).
                    const mark = derived
                      ? "underline decoration-dotted decoration-line-strong underline-offset-[3px]"
                      : "";

                    if (!onInspect) {
                      return (
                        <td
                          key={year.fiscal_year}
                          className={`h-8 whitespace-nowrap px-3 py-0 text-right ${cellText}`}
                        >
                          <span className={mark}>{display}</span>
                        </td>
                      );
                    }

                    return (
                      <td
                        key={year.fiscal_year}
                        className={`h-8 whitespace-nowrap p-0 text-right ${cellText}`}
                      >
                        <button
                          type="button"
                          onClick={() =>
                            onInspect(
                              buildRecord(
                                line,
                                year,
                                statement,
                                display,
                                scale,
                                currency,
                                derived,
                                filingsUrl,
                              ),
                            )
                          }
                          title={`${line.label} — ${
                            derived ? "calculated" : "filed"
                          }. Open source record.`}
                          className="h-8 w-full px-3 text-right transition-colors hover:text-brand-text focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent"
                        >
                          <span className={mark}>{display}</span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-2 font-mono text-[11px] text-ink-muted">
        <span>
          <span className="text-ink-secondary">Filed</span> plain ·{" "}
          <span className="underline decoration-dotted decoration-line-strong underline-offset-2">
            Calculated
          </span>{" "}
          dotted · <span>n/a</span> not reported
        </span>
        {onInspect && <span>Click any figure for its source record</span>}
      </p>
    </div>
  );
}

// Known derivations, shown in the source record for calculated lines. The
// /statements API flags a value as derived but does not return the exact tag;
// these are the app's documented reconstructions.
const FORMULA_BY_KEY: Record<string, string> = {
  gross_profit: "Revenue − cost of revenue",
  operating_income: "Gross profit − operating expenses",
  ebitda: "Operating income + depreciation & amortization",
  pretax_income: "Operating income − interest expense",
  net_income: "Pretax income − tax expense",
  total_debt: "Short-term debt + long-term debt",
  free_cash_flow: "Operating cash flow − capital expenditure",
};

function buildRecord(
  line: LineDef,
  year: StatementYear,
  statement: StatementKey,
  display: string,
  scale: Scale,
  currency: string | null,
  derived: boolean,
  filingsUrl?: string,
): SourceRecord {
  const unit =
    line.format === "per_share"
      ? `${currency ?? "USD"} per share`
      : line.format === "shares"
        ? "share count (millions)"
        : scale.label;
  const period = `FY${year.fiscal_year}${
    year.period_end ? ` · period ended ${fmtDate(year.period_end)}` : ""
  }`;
  return {
    metric: line.label,
    displayValue: display,
    classification: derived ? "calculated" : "filed",
    period,
    unit,
    statement: STATEMENT_LABEL[statement],
    filing: "Annual report (10-K / 20-F / 40-F)",
    formula: derived
      ? (FORMULA_BY_KEY[line.key] ?? "Derived from other filed figures")
      : undefined,
    sourceUrl: filingsUrl,
    sourceLabel: "See the company's filings on SEC EDGAR",
    note: derived
      ? "This figure is calculated by the app from filed line items. The exact XBRL tag is not shown here; open the filing to see the reported components."
      : "Reported in the company's annual filing. Open the filing on SEC EDGAR to see it in context.",
  };
}
