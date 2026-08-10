"use client";

// What is currently constraining the screen, above the results where it cannot
// be missed. Collapsed filter groups make it easy to forget a constraint is
// still on; this row is the answer to "why am I only seeing four companies".

import { appliedChips, type ScreenFilterState } from "@/components/screen/filterSpec";

export default function AppliedFilters({
  state,
  onRemove,
  onClear,
}: {
  state: ScreenFilterState;
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  const chips = appliedChips(state);
  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 pb-3">
      <span className="label-mono mr-0.5">Filtering on</span>
      {chips.map((chip) => (
        <button
          key={chip.id}
          type="button"
          onClick={() => onRemove(chip.id)}
          title={`Remove: ${chip.label}`}
          className="group inline-flex items-center gap-1.5 border border-line-strong bg-surface px-2 py-[0.1875rem] text-[0.75rem] font-medium text-ink transition-colors hover:border-negative hover:text-negative-text"
        >
          <span aria-hidden className={`text-[0.5625rem] leading-none ${chip.marker}`}>
            ●
          </span>
          {chip.label}
          <span aria-hidden className="text-ink-muted group-hover:text-negative-text">
            ×
          </span>
          <span className="sr-only">Remove filter</span>
        </button>
      ))}
      {chips.length > 1 && (
        <button
          type="button"
          onClick={onClear}
          className="ml-1 text-[0.75rem] font-medium text-link underline-offset-2 hover:underline"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
