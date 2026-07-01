"use client";

// A calm amber notice for data-availability caveats. A short list shows inline;
// a long one (a data-poor company can produce dozens) collapses to its first
// line with a quiet toggle, so the page shows one line of context rather than a
// wall of warnings (DESIGN.md: degraded states look designed, not apologetic).

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

  const many = warnings.length > 3;
  const showAll = !many || expanded;

  return (
    <div
      className={`rounded-lg bg-warn-soft px-4 py-2.5 text-sm text-warn-text ${className}`}
    >
      {showAll ? (
        <ul className="space-y-1">
          {warnings.map((warning, i) => (
            <li key={i}>{warning}</li>
          ))}
        </ul>
      ) : (
        <p>{warnings[0]}</p>
      )}
      {many && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="mt-1.5 text-xs font-medium text-warn-text underline decoration-dotted underline-offset-2 hover:decoration-solid"
        >
          {expanded ? "Show fewer" : `Show all ${warnings.length} notes`}
        </button>
      )}
    </div>
  );
}
