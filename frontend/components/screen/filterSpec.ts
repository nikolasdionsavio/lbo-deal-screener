// The screen's filter surface, declared once as data.
//
// The rail, the applied-filter chips, the URL round-trip and the API call are
// all generated from this spec, so adding a dimension is one entry here rather
// than four edits that can drift apart.
//
// Grouping follows how a financial screen is actually read (income statement,
// then balance sheet, then classification) rather than alphabetically, and the
// research on complex filtering: keep a small always-visible core, put the rest
// behind groups the user opens deliberately.

import type { ScreenQuery } from "@/lib/types";

/** How a typed value converts to the units the API expects. */
export type Unit = "money" | "percent" | "ratio";

export interface FieldSpec {
  /** API field stem: `${key}_min` / `${key}_max`. */
  key: string;
  label: string;
  unit: Unit;
  /** Placeholder shown in the min box, e.g. "3". */
  hint?: string;
  /** Short explanation shown when the group is open. */
  note?: string;
}

export interface GroupSpec {
  key: string;
  label: string;
  /** Tailwind text colour token for the group marker. */
  marker: string;
  /** Open by default. Only the core group is. */
  defaultOpen?: boolean;
  fields: FieldSpec[];
}

export const UNIT_SUFFIX: Record<Unit, string> = {
  money: "$m",
  percent: "%",
  ratio: "x",
};

/** Multiplier from what the user types to what the API stores. */
export const UNIT_SCALE: Record<Unit, number> = {
  money: 1e6,
  percent: 0.01,
  ratio: 1,
};

export const GROUPS: GroupSpec[] = [
  {
    key: "size",
    label: "Size",
    marker: "text-group-size",
    defaultOpen: true,
    fields: [
      { key: "revenue", label: "Revenue", unit: "money", hint: "3" },
      { key: "ebitda", label: "EBITDA", unit: "money" },
      { key: "assets", label: "Total assets", unit: "money" },
    ],
  },
  {
    key: "profitability",
    label: "Profitability",
    marker: "text-group-profit",
    fields: [
      {
        key: "margin",
        label: "EBITDA margin",
        unit: "percent",
        note: "Operating income plus D&A, over revenue.",
      },
      { key: "operating_margin", label: "Operating margin", unit: "percent" },
      {
        key: "gross_margin",
        label: "Gross margin",
        unit: "percent",
        note: "Only filers that tag gross profit separately.",
      },
      { key: "net_margin", label: "Net margin", unit: "percent" },
    ],
  },
  {
    key: "balance",
    label: "Leverage and balance sheet",
    marker: "text-group-balance",
    fields: [
      {
        key: "leverage",
        label: "Net debt / EBITDA",
        unit: "ratio",
        hint: "0",
        note: "Only where EBITDA is positive. A multiple against negative EBITDA has no meaning.",
      },
      {
        key: "net_debt",
        label: "Net debt",
        unit: "money",
        note: "Debt less cash. Negative means net cash.",
      },
      { key: "cash", label: "Cash", unit: "money" },
    ],
  },
];

/** Toggles, which are not ranges. */
export interface ToggleSpec {
  key: "ebitdaPositive" | "profitable" | "excludeFlagged";
  label: string;
  note: string;
}

export const TOGGLES: ToggleSpec[] = [
  {
    key: "ebitdaPositive",
    label: "Positive EBITDA only",
    note: "Excludes filers that do not disclose D&A, whose EBITDA cannot be calculated.",
  },
  {
    key: "profitable",
    label: "Profitable only",
    note: "Positive net income for the period.",
  },
  {
    key: "excludeFlagged",
    label: "Hide filing artifacts",
    note: "Rows where EBITDA exceeds revenue, which normally means a one-off gain sits inside operating income.",
  },
];

export type RangeValue = { min: string; max: string };

export interface ScreenFilterState {
  ranges: Record<string, RangeValue>;
  ebitdaPositive: boolean;
  profitable: boolean;
  excludeFlagged: boolean;
  sector: string;
  exchange: string;
  period: string;
  coverage: string;
  q: string;
}

export const EMPTY_FILTERS: ScreenFilterState = {
  ranges: {},
  ebitdaPositive: false,
  profitable: false,
  excludeFlagged: true,
  sector: "",
  exchange: "",
  period: "",
  coverage: "",
  q: "",
};

export const ALL_FIELDS: FieldSpec[] = GROUPS.flatMap((g) => g.fields);

export function fieldSpec(key: string): FieldSpec | undefined {
  return ALL_FIELDS.find((f) => f.key === key);
}

function num(raw: string | undefined): number | null {
  if (raw === undefined || raw.trim() === "") return null;
  const n = Number.parseFloat(raw);
  return Number.isFinite(n) ? n : null;
}

/** Count of active constraints in a group, for the collapsed group badge. */
export function activeInGroup(
  group: GroupSpec,
  state: ScreenFilterState,
): number {
  return group.fields.reduce((total, field) => {
    const value = state.ranges[field.key];
    if (!value) return total;
    return total + (num(value.min) !== null ? 1 : 0) + (num(value.max) !== null ? 1 : 0);
  }, 0);
}

/** Build the API query from filter state. */
export function toQuery(state: ScreenFilterState): ScreenQuery {
  const query: Record<string, unknown> = {};
  for (const field of ALL_FIELDS) {
    const value = state.ranges[field.key];
    if (!value) continue;
    const scale = UNIT_SCALE[field.unit];
    const min = num(value.min);
    const max = num(value.max);
    if (min !== null) query[`${field.key}_min`] = min * scale;
    if (max !== null) query[`${field.key}_max`] = max * scale;
  }
  if (state.ebitdaPositive) query.ebitda_positive = true;
  if (state.profitable) query.profitable = true;
  if (state.excludeFlagged) query.exclude_flagged = true;
  if (state.sector) query.sector = state.sector;
  if (state.exchange) query.exchange = state.exchange;
  if (state.period) query.period = state.period;
  if (state.coverage) query.coverage = state.coverage;
  if (state.q.trim()) query.q = state.q.trim();
  return query as ScreenQuery;
}

/** Serialise to URL params, so a screen can be linked and shared. */
export function toSearchParams(state: ScreenFilterState): string {
  const query = toQuery(state) as Record<string, unknown>;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") continue;
    params.set(key, String(value));
  }
  // Written in BOTH states, unlike the API query which omits the default.
  // A shared link has to record that this was switched off, while a link
  // written by hand (with no such param) should still get the page default.
  params.set("exclude_flagged", String(state.excludeFlagged));
  return params.toString();
}

/** Inverse of toQuery: rebuild state from URL params. */
export function fromSearchParams(search: string): ScreenFilterState | null {
  const params = new URLSearchParams(search);
  if ([...params.keys()].length === 0) return null;
  const state: ScreenFilterState = {
    ...EMPTY_FILTERS,
    ranges: {},
    // Absent means "use the page default", so a hand-written link behaves the
    // same as arriving at /screen fresh. Links the app writes always state it
    // explicitly, so switching it off still survives being shared.
    excludeFlagged: params.has("exclude_flagged")
      ? params.get("exclude_flagged") === "true"
      : EMPTY_FILTERS.excludeFlagged,
  };
  for (const field of ALL_FIELDS) {
    const scale = UNIT_SCALE[field.unit];
    const min = params.get(`${field.key}_min`);
    const max = params.get(`${field.key}_max`);
    if (min === null && max === null) continue;
    const conv = (raw: string | null) => {
      if (raw === null) return "";
      const n = Number.parseFloat(raw);
      if (!Number.isFinite(n)) return "";
      // Round to kill float noise from the unit round-trip (0.30000000000000004).
      return String(Math.round((n / scale) * 1e6) / 1e6);
    };
    state.ranges[field.key] = { min: conv(min), max: conv(max) };
  }
  state.ebitdaPositive = params.get("ebitda_positive") === "true";
  state.profitable = params.get("profitable") === "true";
  state.sector = params.get("sector") ?? "";
  state.exchange = params.get("exchange") ?? "";
  state.period = params.get("period") ?? "";
  state.coverage = params.get("coverage") ?? "";
  state.q = params.get("q") ?? "";
  return state;
}

export interface AppliedChip {
  /** Stable id used to remove just this constraint. */
  id: string;
  label: string;
  marker: string;
}

/** Everything currently constraining the screen, for the chip row. */
export function appliedChips(state: ScreenFilterState): AppliedChip[] {
  const chips: AppliedChip[] = [];
  for (const group of GROUPS) {
    for (const field of group.fields) {
      const value = state.ranges[field.key];
      if (!value) continue;
      const suffix = UNIT_SUFFIX[field.unit];
      const min = num(value.min);
      const max = num(value.max);
      if (min !== null && max !== null) {
        chips.push({
          id: `range:${field.key}`,
          label: `${field.label} ${min}${suffix} to ${max}${suffix}`,
          marker: group.marker,
        });
      } else if (min !== null) {
        chips.push({
          id: `range:${field.key}`,
          label: `${field.label} from ${min}${suffix}`,
          marker: group.marker,
        });
      } else if (max !== null) {
        chips.push({
          id: `range:${field.key}`,
          label: `${field.label} up to ${max}${suffix}`,
          marker: group.marker,
        });
      }
    }
  }
  for (const toggle of TOGGLES) {
    if (state[toggle.key]) {
      chips.push({
        id: `toggle:${toggle.key}`,
        label: toggle.label,
        marker: "text-group-quality",
      });
    }
  }
  for (const [key, label, value] of [
    ["sector", "Sector", state.sector],
    ["exchange", "Exchange", state.exchange],
    ["period", "Period", state.period],
    ["coverage", "Data", state.coverage],
    ["q", "Search", state.q.trim()],
  ] as const) {
    if (value) {
      chips.push({
        id: `text:${key}`,
        label: `${label}: ${value}`,
        marker: "text-group-classify",
      });
    }
  }
  return chips;
}

/** Remove one chip's constraint. */
export function withoutChip(
  state: ScreenFilterState,
  id: string,
): ScreenFilterState {
  const [kind, key] = id.split(":");
  if (kind === "range") {
    const ranges = { ...state.ranges };
    delete ranges[key];
    return { ...state, ranges };
  }
  if (kind === "toggle") {
    return { ...state, [key]: false } as ScreenFilterState;
  }
  return { ...state, [key]: "" } as ScreenFilterState;
}
