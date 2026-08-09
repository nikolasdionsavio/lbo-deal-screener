"use client";

// Filter rail for the deal screen. Money is entered in millions because that is
// how the criteria are actually written down ("$3-20m revenue"), and converted
// to full units at the API boundary.

import type { ScreenSector } from "@/lib/types";

export interface ScreenFilterState {
  revenueMinM: string;
  revenueMaxM: string;
  ebitdaPositive: boolean;
  marginMinPct: string;
  sector: string;
  q: string;
  excludeFlagged: boolean;
}

export const EMPTY_FILTERS: ScreenFilterState = {
  revenueMinM: "",
  revenueMaxM: "",
  ebitdaPositive: false,
  marginMinPct: "",
  sector: "",
  q: "",
  excludeFlagged: true,
};

/** Bands an origination screen is usually written in. */
const PRESETS: { label: string; note: string; min: string; max: string }[] = [
  { label: "Add-on", note: "$3-20m", min: "3", max: "20" },
  { label: "Lower mid-market", note: "$20-100m", min: "20", max: "100" },
  { label: "Mid-market", note: "$100m-1bn", min: "100", max: "1000" },
];

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-muted">
        {label}
      </span>
      <div className="mt-1.5">{children}</div>
      {hint && (
        <span className="mt-1 block text-[11px] leading-tight text-ink-muted">
          {hint}
        </span>
      )}
    </label>
  );
}

const inputClass =
  "w-full border border-line bg-surface px-2.5 py-1.5 font-mono text-[0.8125rem] tabular-nums text-ink " +
  "focus:border-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-accent";

export default function ScreenFilters({
  value,
  onChange,
  sectors,
  onReset,
}: {
  value: ScreenFilterState;
  onChange: (next: ScreenFilterState) => void;
  sectors: ScreenSector[];
  onReset: () => void;
}) {
  const set = <K extends keyof ScreenFilterState>(
    key: K,
    next: ScreenFilterState[K],
  ) => onChange({ ...value, [key]: next });

  const activePreset = PRESETS.find(
    (p) => p.min === value.revenueMinM && p.max === value.revenueMaxM,
  );

  return (
    <div className="space-y-5">
      <div>
        <span className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-muted">
          Revenue band
        </span>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {PRESETS.map((preset) => {
            const on = activePreset?.label === preset.label;
            return (
              <button
                key={preset.label}
                type="button"
                onClick={() =>
                  onChange({
                    ...value,
                    revenueMinM: on ? "" : preset.min,
                    revenueMaxM: on ? "" : preset.max,
                  })
                }
                aria-pressed={on}
                className={`border px-2 py-1 text-[11px] transition-colors ${
                  on
                    ? "border-accent text-accent"
                    : "border-line text-ink-secondary hover:border-line-strong hover:text-ink"
                }`}
                title={`${preset.label}: revenue ${preset.note}`}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <input
            className={inputClass}
            inputMode="decimal"
            placeholder="min $m"
            aria-label="Minimum revenue in millions"
            value={value.revenueMinM}
            onChange={(e) => set("revenueMinM", e.target.value)}
          />
          <input
            className={inputClass}
            inputMode="decimal"
            placeholder="max $m"
            aria-label="Maximum revenue in millions"
            value={value.revenueMaxM}
            onChange={(e) => set("revenueMaxM", e.target.value)}
          />
        </div>
      </div>

      <div className="border-t border-line pt-4">
        <label className="flex cursor-pointer items-start gap-2.5">
          <input
            type="checkbox"
            className="mt-0.5 accent-[var(--accent)]"
            checked={value.ebitdaPositive}
            onChange={(e) => set("ebitdaPositive", e.target.checked)}
          />
          <span>
            <span className="text-[0.8125rem] text-ink">Positive EBITDA only</span>
            <span className="mt-0.5 block text-[11px] leading-tight text-ink-muted">
              Excludes filers that do not disclose D&amp;A, whose EBITDA cannot
              be calculated.
            </span>
          </span>
        </label>
      </div>

      <Field label="Min EBITDA margin" hint="Percent, e.g. 15">
        <input
          className={inputClass}
          inputMode="decimal"
          placeholder="%"
          value={value.marginMinPct}
          onChange={(e) => set("marginMinPct", e.target.value)}
        />
      </Field>

      <Field label="Sector">
        <select
          className={inputClass}
          value={value.sector}
          onChange={(e) => set("sector", e.target.value)}
        >
          <option value="">All sectors</option>
          {sectors.map((s) => (
            <option key={`${s.sic}-${s.name}`} value={s.name}>
              {s.name} ({s.count})
            </option>
          ))}
        </select>
      </Field>

      <Field label="Company or ticker">
        <input
          className={inputClass}
          placeholder="Search"
          value={value.q}
          onChange={(e) => set("q", e.target.value)}
        />
      </Field>

      <div className="border-t border-line pt-4">
        <label className="flex cursor-pointer items-start gap-2.5">
          <input
            type="checkbox"
            className="mt-0.5 accent-[var(--accent)]"
            checked={value.excludeFlagged}
            onChange={(e) => set("excludeFlagged", e.target.checked)}
          />
          <span>
            <span className="text-[0.8125rem] text-ink">Hide filing artifacts</span>
            <span className="mt-0.5 block text-[11px] leading-tight text-ink-muted">
              Rows where EBITDA exceeds revenue, which normally means a one-off
              gain sits inside operating income.
            </span>
          </span>
        </label>
      </div>

      <button
        type="button"
        onClick={onReset}
        className="text-[0.8125rem] text-link underline-offset-2 hover:underline"
      >
        Reset filters
      </button>
    </div>
  );
}
