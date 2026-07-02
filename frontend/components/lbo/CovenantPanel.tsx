"use client";

// Covenant-headroom stress: turns the LBO cash flows into a credit view. Each
// modeled year is tested against a standard maintenance package (net leverage,
// interest coverage, DSCR); breached cells and years are flagged, and the panel
// leads with the tightest EBITDA cushion to a leverage breach.

import { fmtMultiple, fmtPercent } from "@/lib/format";
import type { CovenantYear, LboCovenants } from "@/lib/types";

type RatioKey = "net_debt_to_ebitda" | "interest_coverage" | "fcf_dscr";

export default function CovenantPanel({
  covenants,
}: {
  covenants: LboCovenants;
}) {
  const { limits, years, any_breach, min_ebitda_cushion_pct } = covenants;

  const cols: {
    key: RatioKey;
    label: string;
    limit: string;
    ok: (v: number) => boolean;
  }[] = [
    {
      key: "net_debt_to_ebitda",
      label: "Net debt / EBITDA",
      limit: `≤ ${fmtMultiple(limits.max_net_debt_to_ebitda)}`,
      ok: (v) => v <= limits.max_net_debt_to_ebitda,
    },
    {
      key: "interest_coverage",
      label: "Interest coverage",
      limit: `≥ ${fmtMultiple(limits.min_interest_coverage)}`,
      ok: (v) => v >= limits.min_interest_coverage,
    },
    {
      key: "fcf_dscr",
      label: "FCF DSCR",
      limit: `≥ ${fmtMultiple(limits.min_fcf_dscr)}`,
      ok: (v) => v >= limits.min_fcf_dscr,
    },
  ];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
            any_breach ? "bg-negative-soft text-negative" : "text-positive"
          }`}
        >
          {any_breach
            ? "Covenant breach during the hold"
            : "Covenants hold every year"}
        </span>
        {min_ebitda_cushion_pct !== null && (
          <span className="text-xs text-ink-muted">
            ~{fmtPercent(min_ebitda_cushion_pct)} EBITDA cushion to a leverage
            breach (approximate)
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-xs text-ink-muted">
              <th className="px-3 py-2 text-left font-medium">Year</th>
              {cols.map((c) => (
                <th key={c.key} className="px-3 py-2 text-right font-medium">
                  {c.label}
                  <span className="ml-1 font-normal text-ink-muted">
                    ({c.limit})
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {years.map((y) => (
              <tr
                key={y.year}
                className={`border-b border-line ${
                  y.breached ? "bg-negative-soft" : ""
                }`}
              >
                <td className="px-3 py-2 text-ink-secondary">Year {y.year}</td>
                {cols.map((c) => {
                  const v = y[c.key];
                  const bad = v !== null && !c.ok(v);
                  return (
                    <td
                      key={c.key}
                      className={`px-3 py-2 text-right tabular-nums ${
                        bad ? "font-semibold text-negative" : "text-ink"
                      }`}
                    >
                      {fmtMultiple(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-ink-muted">
        Each modeled year is tested against a standard maintenance package. The
        EBITDA cushion holds the debt path fixed, so it is approximate. A dash is
        a ratio that is not binding (for example no interest, or a pre-profit
        year).
      </p>
    </div>
  );
}

// Re-exported for callers that only need the row shape.
export type { CovenantYear };
