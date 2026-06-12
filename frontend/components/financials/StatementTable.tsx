// Annual statement table (BUILD_SPEC section 19.7): years as columns
// newest-left, line items as rows in filing order, sticky first column over
// horizontal scroll, one consistent scale per table (millions or billions,
// chosen from the max magnitude) noted in the top-left header cell. Derived
// values carry a superscript dagger with a single footnote line; null
// renders as an em dash. Dense, bank-grade, no charts.

import type {
  BalanceSheetLines,
  CashFlowLines,
  IncomeStatementLines,
  StatementYear,
} from "@/lib/types";
import { fmtDate } from "@/lib/format";

export type StatementKey = "income_statement" | "balance_sheet" | "cash_flow";

interface LineDef {
  key: string;
  label: string;
  /** Subtotal-style rows (gross profit, EBITDA, ...) render medium weight. */
  emphasis?: boolean;
}

// Filing order per the section 19.7 response shape.
const LINES: Record<StatementKey, LineDef[]> = {
  income_statement: [
    { key: "revenue", label: "Revenue" },
    { key: "cost_of_revenue", label: "Cost of revenue" },
    { key: "gross_profit", label: "Gross profit", emphasis: true },
    { key: "operating_income", label: "Operating income", emphasis: true },
    { key: "depreciation_amortization", label: "Depreciation & amortization" },
    { key: "ebitda", label: "EBITDA", emphasis: true },
    { key: "interest_expense", label: "Interest expense" },
    { key: "tax_expense", label: "Tax expense" },
    { key: "net_income", label: "Net income", emphasis: true },
  ],
  balance_sheet: [
    { key: "cash_and_equivalents", label: "Cash & equivalents" },
    { key: "receivables", label: "Receivables" },
    { key: "inventory", label: "Inventory" },
    { key: "current_assets", label: "Current assets", emphasis: true },
    { key: "accounts_payable", label: "Accounts payable" },
    { key: "current_liabilities", label: "Current liabilities", emphasis: true },
    { key: "total_debt", label: "Total debt", emphasis: true },
    { key: "total_equity", label: "Total equity", emphasis: true },
  ],
  cash_flow: [
    { key: "operating_cash_flow", label: "Operating cash flow" },
    { key: "capex", label: "Capital expenditure" },
    { key: "free_cash_flow", label: "Free cash flow", emphasis: true },
    { key: "dividends_paid", label: "Dividends paid" },
    { key: "share_buybacks", label: "Share buybacks" },
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

/** One scale per table, chosen from the largest magnitude shown in it. */
function chooseScale(
  years: StatementYear[],
  statement: StatementKey,
  currency: string | null,
): Scale {
  let maxAbs = 0;
  for (const year of years) {
    for (const line of LINES[statement]) {
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
}

export default function StatementTable({
  statement,
  years,
  currency,
  className = "",
}: StatementTableProps) {
  const scale = chooseScale(years, statement, currency);
  const lines = LINES[statement];
  const hasDerived = years.some((year) =>
    lines.some(
      (line) =>
        year.derived_fields.includes(line.key) &&
        lineValue(year, statement, line.key) !== null,
    ),
  );

  return (
    <div className={className}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line">
              <th
                scope="col"
                className={`${STICKY_CELL} min-w-[11rem] px-3 py-2 text-left text-xs font-medium text-ink-muted`}
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
            {lines.map((line) => (
              <tr
                key={line.key}
                className="group border-b border-line transition-colors duration-150 last:border-b-0 hover:bg-brand-soft"
              >
                <th
                  scope="row"
                  className={`${STICKY_CELL} px-3 py-2 text-left font-normal ${
                    line.emphasis === true
                      ? "font-medium text-ink"
                      : "text-ink-secondary"
                  }`}
                >
                  {line.label}
                </th>
                {years.map((year) => {
                  const value = lineValue(year, statement, line.key);
                  const derived =
                    value !== null && year.derived_fields.includes(line.key);
                  return (
                    <td
                      key={year.fiscal_year}
                      className={`whitespace-nowrap px-3 py-2 text-right tabular-nums ${
                        line.emphasis === true
                          ? "font-medium text-ink"
                          : "text-ink-secondary"
                      }`}
                      title={value === null ? "Not available" : undefined}
                    >
                      {fmtScaled(value, scale)}
                      {derived && (
                        <sup
                          className="ml-0.5 text-[10px] text-ink-muted"
                          title="Derived from filed figures"
                        >
                          †
                        </sup>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasDerived && (
        <p className="mt-2 text-xs text-ink-muted">
          † derived from filed figures
        </p>
      )}
    </div>
  );
}
