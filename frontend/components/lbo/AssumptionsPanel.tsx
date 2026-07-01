"use client";

import AssumptionField from "@/components/ui/AssumptionField";
import Card from "@/components/ui/Card";
import type { LboAssumptions } from "@/lib/types";

const HOLDING_PERIODS = [1, 2, 3, 4, 5, 6, 7];

/** Resize a per-year series to `length`, repeating the last value when growing. */
function resizeYears(series: number[], length: number): number[] {
  if (series.length >= length) return series.slice(0, length);
  const last = series.length > 0 ? series[series.length - 1] : 0;
  return series.concat(new Array<number>(length - series.length).fill(last));
}

interface AssumptionsPanelProps {
  values: LboAssumptions;
  basis: Record<string, string>;
  onChange: (next: LboAssumptions) => void;
  onReset: () => void;
}

export default function AssumptionsPanel({
  values,
  basis,
  onChange,
  onReset,
}: AssumptionsPanelProps) {
  function patch(partial: Partial<LboAssumptions>) {
    onChange({ ...values, ...partial });
  }

  function setHoldingPeriod(holdingPeriod: number) {
    onChange({
      ...values,
      holding_period: holdingPeriod,
      revenue_growth: resizeYears(values.revenue_growth, holdingPeriod),
      ebitda_margin: resizeYears(values.ebitda_margin, holdingPeriod),
    });
  }

  function setGrowthYear(index: number, value: number) {
    const series = values.revenue_growth.slice();
    series[index] = value;
    patch({ revenue_growth: series });
  }

  function setMarginYear(index: number, value: number) {
    const series = values.ebitda_margin.slice();
    series[index] = value;
    patch({ ebitda_margin: series });
  }

  const revenueBasis = values.valuation_basis === "revenue";

  return (
    <div>
      {revenueBasis && (
        <div className="mb-3 rounded-lg border border-line bg-surface-sunken px-3.5 py-2.5 text-xs leading-relaxed text-ink-secondary">
          Priced on <span className="font-medium text-ink">EV/Revenue</span>{" "}
          because this company is not yet EBITDA-profitable. The exit prices on
          EV/EBITDA once the margin turns positive, so value is predicated on the
          projected ramp to profitability.
        </div>
      )}
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Assumptions</h2>
          <button
            type="button"
            onClick={onReset}
            className="btn btn-secondary px-2.5 py-1 text-xs"
          >
            Reset to defaults
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <AssumptionField
            label={revenueBasis ? "Entry EV/Revenue" : "Entry multiple"}
            value={values.entry_multiple}
            unit="x"
            step={0.5}
            min={0}
            onChange={(v) => patch({ entry_multiple: v })}
          />
          {revenueBasis ? (
            <AssumptionField
              label="Leverage (% of EV)"
              value={values.entry_leverage_pct}
              unit="%"
              step={5}
              min={0}
              max={70}
              onChange={(v) => patch({ entry_leverage_pct: v })}
            />
          ) : (
            <AssumptionField
              label="Debt multiple"
              value={values.debt_multiple}
              unit="x"
              step={0.5}
              min={0}
              onChange={(v) => patch({ debt_multiple: v })}
            />
          )}
          <AssumptionField
            label="Capex (% of revenue)"
            value={values.capex_pct_revenue}
            unit="%"
            step={0.5}
            onChange={(v) => patch({ capex_pct_revenue: v })}
          />
          <AssumptionField
            label="Change in NWC (% of revenue growth)"
            value={values.nwc_pct_revenue}
            unit="%"
            step={0.5}
            onChange={(v) => patch({ nwc_pct_revenue: v })}
          />
          <AssumptionField
            label="Tax rate"
            value={values.tax_rate}
            unit="%"
            step={1}
            onChange={(v) => patch({ tax_rate: v })}
          />
          <AssumptionField
            label="Interest rate"
            value={values.interest_rate}
            unit="%"
            step={0.5}
            onChange={(v) => patch({ interest_rate: v })}
          />
          <AssumptionField
            label="Mandatory repayment"
            value={values.mandatory_repayment_pct}
            unit="%"
            step={1}
            onChange={(v) => patch({ mandatory_repayment_pct: v })}
          />
          <AssumptionField
            label="Exit multiple"
            value={values.exit_multiple}
            unit="x"
            step={0.5}
            min={0}
            onChange={(v) => patch({ exit_multiple: v })}
          />
        </div>

        <label className="mt-3 block">
          <span className="mb-1 block text-xs font-medium text-ink-secondary">
            Holding period
          </span>
          <select
            className="input px-2 py-1.5"
            value={values.holding_period}
            onChange={(event) => setHoldingPeriod(Number(event.target.value))}
          >
            {HOLDING_PERIODS.map((n) => (
              <option key={n} value={n}>
                {n} {n === 1 ? "year" : "years"}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4">
          <div className="mb-1.5 text-xs font-semibold text-ink-secondary">
            Revenue growth by year
          </div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(4.5rem,1fr))] gap-2">
            {values.revenue_growth.map((growth, i) => (
              <AssumptionField
                key={`growth-${i}`}
                label={`Y${i + 1}`}
                value={growth}
                unit="%"
                step={0.5}
                onChange={(v) => setGrowthYear(i, v)}
              />
            ))}
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1.5 text-xs font-semibold text-ink-secondary">
            EBITDA margin by year
          </div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(4.5rem,1fr))] gap-2">
            {values.ebitda_margin.map((margin, i) => (
              <AssumptionField
                key={`margin-${i}`}
                label={`Y${i + 1}`}
                value={margin}
                unit="%"
                step={0.5}
                onChange={(v) => setMarginYear(i, v)}
              />
            ))}
          </div>
        </div>
      </Card>

      <div className="mt-3 space-y-1 text-xs text-ink-muted">
        <p>Assumptions are editable; defaults derived from company data.</p>
        {Object.entries(basis).map(([key, note]) => (
          <p key={key}>
            <span className="font-medium">{key.replace(/_/g, " ")}</span>: {note}
          </p>
        ))}
      </div>
    </div>
  );
}
