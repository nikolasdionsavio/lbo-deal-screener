"use client";

// Amber warning block. Beyond three entries the list collapses to the first
// three with a quiet text toggle (BUILD_SPEC section 19.7 presentation pass).

import { useState } from "react";

interface WarningListProps {
  warnings: string[];
  className?: string;
}

export default function WarningList({
  warnings,
  className = "",
}: WarningListProps) {
  const [expanded, setExpanded] = useState(false);

  if (warnings.length === 0) return null;

  const collapsible = warnings.length > 3;
  const visible = collapsible && !expanded ? warnings.slice(0, 3) : warnings;

  return (
    <div
      className={`rounded-lg border border-transparent bg-warn-soft px-4 py-3 text-sm text-warn-text ${className}`}
    >
      <ul className="space-y-1">
        {visible.map((warning, i) => (
          <li key={i}>{warning}</li>
        ))}
      </ul>
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="mt-1.5 text-xs font-medium text-warn-text underline decoration-dotted underline-offset-2 hover:decoration-solid"
        >
          {expanded ? "Show fewer" : `Show all ${warnings.length} warnings`}
        </button>
      )}
    </div>
  );
}
