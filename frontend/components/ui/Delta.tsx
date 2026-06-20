import { fmtPercent } from "@/lib/format";

// A directional year-on-year delta, triple-encoded so colour is never the sole
// carrier of meaning: an SVG caret (up / down / flat), the signed percent, and
// a semantic colour. Callers pass null when a prior-year value was <= 0 (a
// percent change across a sign flip is meaningless), so it renders nothing.
export default function Delta({ pct }: { pct: number | null }) {
  if (pct === null || !Number.isFinite(pct)) return null;
  const flat = Math.abs(pct) < 0.0005;
  const cls = flat
    ? "text-ink-muted"
    : pct > 0
      ? "text-positive-text"
      : "text-negative-text";
  return (
    <span className={`flex items-center gap-0.5 text-xs tabular-nums ${cls}`}>
      <svg width="7" height="7" viewBox="0 0 8 8" fill="currentColor" aria-hidden>
        {flat ? (
          <rect x="1" y="3.5" width="6" height="1" />
        ) : pct > 0 ? (
          <path d="M4 1l3 5H1z" />
        ) : (
          <path d="M4 7L1 2h6z" />
        )}
      </svg>
      {fmtPercent(pct, { signed: true, digits: 1 })}
    </span>
  );
}
