"use client";

import { useEffect, useState, type ChangeEvent } from "react";

interface AssumptionFieldProps {
  label: string;
  /** Stored value. For unit "%" this is a decimal (0.05 = 5%). */
  value: number;
  /** Unit suffix: "%" displays value * 100 and stores a decimal; "x" and "" are raw. */
  unit?: "%" | "x" | "";
  onChange: (value: number) => void;
  step?: number;
  min?: number;
  max?: number;
  className?: string;
}

function toDisplay(value: number, unit: string): number {
  if (unit === "%") {
    // Trim float noise AND long derived decimals (e.g. an averaged capex ratio
    // of 2.17727276313%) to a clean, readable figure. 4 dp is finer than any
    // assumption needs and preserves the underlying value until the user edits.
    return Number((value * 100).toFixed(4));
  }
  return value;
}

export default function AssumptionField({
  label,
  value,
  unit = "",
  onChange,
  step,
  min,
  max,
  className = "",
}: AssumptionFieldProps) {
  const display = toDisplay(value, unit);
  const [text, setText] = useState<string>(String(display));

  // Sync the input when the external value changes (e.g. defaults loaded),
  // without clobbering in-progress typing that parses to the same number.
  useEffect(() => {
    const parsed = Number(text);
    if (!Number.isFinite(parsed) || Math.abs(parsed - display) > 1e-9) {
      setText(String(display));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [display]);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.value;
    setText(next);
    if (next.trim() === "") return;
    const parsed = Number(next);
    if (!Number.isFinite(parsed)) return;
    onChange(unit === "%" ? parsed / 100 : parsed);
  }

  // Editable assumptions are ochre, never blue form fields (DESIGN.md: ochre is
  // reserved for user-editable model inputs), and their values use the data
  // font so they line up like a model sheet.
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-[11px] font-medium text-ink-secondary">
        {label}
      </span>
      <span className="flex items-center rounded-[3px] border border-line-strong bg-assumption-soft transition-colors duration-150 focus-within:border-assumption focus-within:ring-1 focus-within:ring-assumption">
        <input
          type="number"
          inputMode="decimal"
          className="w-full min-w-0 rounded-[3px] bg-transparent px-2 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink outline-none"
          value={text}
          step={step}
          min={min}
          max={max}
          onChange={handleChange}
        />
        {unit !== "" && (
          <span className="pr-2 font-mono text-[11px] text-assumption">{unit}</span>
        )}
      </span>
    </label>
  );
}
