"use client";

// Screening score (DESIGN.md: treat it as a methodology table, not a verdict).
// A large plain total aligned with a breakdown table: component, weight, score,
// basis, and points contributed. No gauge, ring, speedometer, or glowing
// number. The score is provisional and inspectable. GET /companies/{t}/score.

import { useCompany } from "@/components/company/CompanyContext";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getScore } from "@/lib/api";
import { fmtDate, fmtPercent } from "@/lib/format";
import { useApi } from "@/lib/hooks";

function fmtWeight(weight: number): string {
  const pct = weight * 100;
  return fmtPercent(weight, { digits: Number.isInteger(pct) ? 0 : 1 });
}

export default function ScorePage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  const { data, error, loading, retry } = useApi(
    () => getScore(ticker),
    [ticker],
  );

  if (loading) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Screening score" />
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Screening score" />
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not compute the screening score for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  return (
    <div key="content" className="fade-in">
      <SectionHeader
        variant="page"
        as="h2"
        title="Screening score"
        subtitle="A weighted summary of the operating, credit, valuation, and transaction figures shown elsewhere in the analysis."
      />

      {/* Large plain total, aligned with the breakdown. No gauge. */}
      <div className="mt-6 flex flex-wrap items-baseline gap-x-6 gap-y-2 border-t border-line pt-6">
        <div className="font-mono text-[3.25rem] leading-none tabular-nums text-ink">
          {data.total.toFixed(0)}
          <span className="ml-1 text-[1.25rem] text-ink-muted">/ 100</span>
        </div>
        <div className="font-mono text-[0.8125rem] text-ink-secondary">
          {data.rating}
        </div>
      </div>
      <p className="mt-3 max-w-[68ch] text-[0.875rem] text-ink-secondary">
        A screening aid based on the current methodology. It is not an
        investment recommendation. Computed {fmtDate(data.as_of)} from the traced
        figures on the other pages.
      </p>

      {/* The methodology table. */}
      <div className="scroll-x mt-8">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th scope="col" className="py-2 pr-3 text-left text-[11px] font-semibold uppercase tracking-[0.02em] text-ink-muted">
                Component
              </th>
              <th scope="col" className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.02em] text-ink-muted">
                Weight
              </th>
              <th scope="col" className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-[0.02em] text-ink-muted">
                Score
              </th>
              <th scope="col" className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.02em] text-ink-muted">
                Basis
              </th>
              <th scope="col" className="py-2 pl-3 text-right text-[11px] font-semibold uppercase tracking-[0.02em] text-ink-muted">
                Points
              </th>
            </tr>
          </thead>
          <tbody>
            {data.components.map((c) => {
              const maxPoints = c.effective_weight * 100;
              const weightsDiffer =
                Math.abs(c.effective_weight - c.weight) > 1e-9;
              return (
                <tr
                  key={c.key}
                  className="group border-b border-line align-top transition-colors hover:bg-brand-soft"
                >
                  <th scope="row" className="py-2.5 pr-3 text-left font-medium text-ink">
                    {c.label}
                  </th>
                  <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-ink-secondary">
                    {fmtWeight(c.effective_weight)}
                    {weightsDiffer && (
                      <span
                        className="ml-1 text-[11px] text-ink-muted"
                        title={`Base weight ${fmtWeight(c.weight)}, reweighted because another component had no data`}
                      >
                        ↻
                      </span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono tabular-nums text-ink">
                    {c.score !== null ? c.score.toFixed(0) : "n/a"}
                  </td>
                  <td className="px-3 py-2.5 text-left text-ink-secondary">
                    {c.reason}
                    <WarningList warnings={c.warnings} className="mt-1.5" />
                  </td>
                  <td className="whitespace-nowrap py-2.5 pl-3 text-right font-mono tabular-nums text-ink">
                    {c.weighted_points !== null
                      ? c.weighted_points.toFixed(1)
                      : "0.0"}
                    <span className="text-ink-muted"> / {maxPoints.toFixed(0)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t border-line-strong">
              <th scope="row" className="py-2.5 pr-3 text-left font-semibold text-ink">
                Total
              </th>
              <td />
              <td />
              <td />
              <td className="py-2.5 pl-3 text-right font-mono font-semibold tabular-nums text-ink">
                {data.total.toFixed(1)}
                <span className="text-ink-muted"> / 100</span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <section className="mt-10 border-t border-line pt-6">
        <h2 className="text-[0.8125rem] font-semibold text-ink">Methodology</h2>
        <p className="mt-2 max-w-[68ch] text-[0.875rem] leading-relaxed text-ink-secondary">
          The total is the sum of each component score multiplied by its weight.
          Each input is scored linearly between a defined worst and best
          threshold, and a component score is the average of its available input
          scores. When every input for a component is unavailable, the component
          is excluded and its weight is redistributed across the rest, so the
          weight shown ({"↻"}) can differ from the base weight. The score
          reflects the current methodology. It is a prompt for review, not a
          recommendation.
        </p>
      </section>

      <Disclaimer />
    </div>
  );
}
