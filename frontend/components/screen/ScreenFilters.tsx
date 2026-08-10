"use client";

// Filter rail, rendered entirely from filterSpec so every group behaves the
// same way: collapsible, badged with the number of constraints it holds, and
// carrying its own marker colour.
//
// Order is the order a screen gets built. Search first, because looking one
// company up is the most direct thing anyone does. Then presets, then size,
// profitability, leverage, classification, and data quality last. Inside a
// group, toggles come before typed ranges, since a checkbox filters more per
// unit of effort than a number does.

import { useState } from "react";
import {
  GROUPS,
  UNIT_SUFFIX,
  activeInGroup,
  type GroupSpec,
  type ScreenFilterState,
  type SelectSpec,
} from "@/components/screen/filterSpec";
import type { ScreenFacets } from "@/lib/types";

/** Named screens. Origination usually starts from one of these, not a blank form. */
const PRESETS: { label: string; note: string; apply: (s: ScreenFilterState) => ScreenFilterState }[] = [
  {
    label: "Add-on targets",
    note: "$3-20m revenue, profitable at EBITDA",
    apply: (s) => ({
      ...s,
      ranges: { ...s.ranges, revenue: { min: "3", max: "20" } },
      ebitdaPositive: true,
    }),
  },
  {
    label: "Lower mid-market",
    note: "$20-100m revenue, 15%+ EBITDA margin",
    apply: (s) => ({
      ...s,
      ranges: {
        ...s.ranges,
        revenue: { min: "20", max: "100" },
        margin: { min: "15", max: "" },
      },
      ebitdaPositive: true,
    }),
  },
  {
    label: "Conservatively levered",
    note: "Under 3.0x net debt / EBITDA",
    apply: (s) => ({
      ...s,
      ranges: { ...s.ranges, leverage: { min: "0", max: "3" } },
      ebitdaPositive: true,
    }),
  },
  {
    label: "Net cash",
    note: "More cash than debt",
    apply: (s) => ({
      ...s,
      ranges: { ...s.ranges, net_debt: { min: "", max: "0" } },
    }),
  },
];

const inputClass =
  "w-full border border-line-strong bg-surface px-2 py-1.5 font-mono text-[0.8125rem] font-medium tabular-nums text-ink " +
  "placeholder:font-normal placeholder:text-ink-muted " +
  "focus:border-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-accent";

const selectClass =
  "w-full border border-line-strong bg-surface px-2 py-1.5 text-[0.8125rem] font-medium text-ink " +
  "focus:border-accent focus:outline-none focus-visible:ring-1 focus-visible:ring-accent";

function Group({
  group,
  state,
  facets,
  onChange,
}: {
  group: GroupSpec;
  state: ScreenFilterState;
  facets: ScreenFacets | null;
  onChange: (next: ScreenFilterState) => void;
}) {
  const active = activeInGroup(group, state);
  const [open, setOpen] = useState(Boolean(group.defaultOpen));
  // Opening is sticky, but a group holding an active constraint can never be
  // collapsed shut: hiding a filter that is changing the table is how a screen
  // starts lying to you.
  const expanded = open || active > 0;

  const setRange = (key: string, side: "min" | "max", value: string) => {
    const current = state.ranges[key] ?? { min: "", max: "" };
    onChange({
      ...state,
      ranges: { ...state.ranges, [key]: { ...current, [side]: value } },
    });
  };

  const optionsFor = (select: SelectSpec) => {
    if (select.source === "static") return select.options ?? [];
    if (select.source === "sectors")
      return (facets?.sectors ?? []).map((s) => ({
        value: s.name,
        label: `${s.name} (${s.count})`,
      }));
    if (select.source === "exchanges")
      return (facets?.exchanges ?? []).map((x) => ({ value: x, label: x }));
    return (facets?.periods ?? []).map((p) => ({
      value: p,
      label: p.replace("CY", "FY"),
    }));
  };

  return (
    <section className="border-t border-line pt-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2 text-left"
      >
        <span aria-hidden className={`text-[0.6875rem] leading-none ${group.marker}`}>
          ●
        </span>
        <span className="label-mono flex-1 !text-ink-secondary">{group.label}</span>
        {active > 0 && (
          <span className="border border-accent px-1 font-mono text-[0.625rem] font-semibold leading-4 text-accent">
            {active}
          </span>
        )}
        <span aria-hidden className="text-[0.75rem] text-ink-muted">
          {expanded ? "−" : "+"}
        </span>
      </button>

      {expanded && (
        <div className="mt-2.5 space-y-3">
          {/* Toggles first: one click, no typing, so they carry the most
              filtering per unit of effort. */}
          {(group.toggles ?? []).map((toggle) => (
            <label key={toggle.key} className="flex cursor-pointer items-start gap-2">
              <input
                type="checkbox"
                className="mt-[0.2rem] h-3.5 w-3.5 accent-[var(--accent)]"
                checked={state[toggle.key]}
                onChange={(e) =>
                  onChange({ ...state, [toggle.key]: e.target.checked })
                }
              />
              <span>
                <span className="text-[0.8125rem] font-medium text-ink">
                  {toggle.label}
                </span>
                <span className="note-sm mt-0.5 block">{toggle.note}</span>
              </span>
            </label>
          ))}

          {(group.selects ?? []).map((select) => (
            <label key={select.key} className="block">
              <span className="text-[0.8125rem] font-medium text-ink">
                {select.label}
              </span>
              <select
                className={`${selectClass} mt-1`}
                value={state[select.key]}
                onChange={(e) =>
                  onChange({ ...state, [select.key]: e.target.value })
                }
              >
                <option value="">{select.anyLabel}</option>
                {optionsFor(select).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {select.note && <p className="note-sm mt-1">{select.note}</p>}
            </label>
          ))}

          {(group.fields ?? []).map((field) => {
            const value = state.ranges[field.key] ?? { min: "", max: "" };
            const suffix = UNIT_SUFFIX[field.unit];
            return (
              <div key={field.key}>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[0.8125rem] font-medium text-ink">
                    {field.label}
                  </span>
                  <span className="font-mono text-[0.625rem] font-semibold text-ink-muted">
                    {suffix}
                  </span>
                </div>
                <div className="mt-1 grid grid-cols-2 gap-1.5">
                  <input
                    className={inputClass}
                    inputMode="decimal"
                    placeholder={field.hint ? `min ${field.hint}` : "min"}
                    aria-label={`Minimum ${field.label} in ${suffix}`}
                    value={value.min}
                    onChange={(e) => setRange(field.key, "min", e.target.value)}
                  />
                  <input
                    className={inputClass}
                    inputMode="decimal"
                    placeholder="max"
                    aria-label={`Maximum ${field.label} in ${suffix}`}
                    value={value.max}
                    onChange={(e) => setRange(field.key, "max", e.target.value)}
                  />
                </div>
                {field.note && <p className="note-sm mt-1">{field.note}</p>}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function ScreenFilters({
  value,
  onChange,
  facets,
  onReset,
}: {
  value: ScreenFilterState;
  onChange: (next: ScreenFilterState) => void;
  facets: ScreenFacets | null;
  onReset: () => void;
}) {
  const set = <K extends keyof ScreenFilterState>(
    key: K,
    next: ScreenFilterState[K],
  ) => onChange({ ...value, [key]: next });

  return (
    <div className="space-y-4">
      {/* Search sits above everything: looking a company up by name is the most
          direct thing anyone does here, and it used to be the fourth control
          inside a group near the bottom of the rail. */}
      <label className="block">
        <span className="label-mono">Find a company</span>
        <input
          className={`${inputClass} mt-1.5 !font-sans`}
          placeholder="Name or ticker"
          aria-label="Search by company name or ticker"
          value={value.q}
          onChange={(e) => set("q", e.target.value)}
        />
      </label>

      <div className="border-t border-line pt-3">
        <span className="label-mono">Start from</span>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              title={preset.note}
              onClick={() => onChange(preset.apply(value))}
              className="border border-line-strong px-2 py-1 text-[0.75rem] font-medium text-ink-secondary transition-colors hover:border-accent hover:text-accent"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {GROUPS.map((group) => (
        <Group
          key={group.key}
          group={group}
          state={value}
          facets={facets}
          onChange={onChange}
        />
      ))}

      <button
        type="button"
        onClick={onReset}
        className="border-t border-line pt-3 text-[0.8125rem] font-medium text-link underline-offset-2 hover:underline"
      >
        Reset all filters
      </button>
    </div>
  );
}
