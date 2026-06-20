// A hand-rolled inline SVG sparkline (no charting library) for a tiny trend
// mark beside a figure. The stroke is currentColor, so the caller sets the
// colour with a Tailwind text-* class (default: inherit, usually text-ink-muted).
// Returns null with fewer than two finite points, so a cell degrades honestly
// to its value rather than drawing a faked flat line.

interface SparklineProps {
  points: (number | null | undefined)[];
  className?: string;
  width?: number;
  height?: number;
}

export default function Sparkline({
  points,
  className = "",
  width = 64,
  height = 18,
}: SparklineProps) {
  const vs = points.filter(
    (v): v is number => typeof v === "number" && Number.isFinite(v),
  );
  if (vs.length < 2) return null;

  const min = Math.min(...vs);
  const max = Math.max(...vs);
  const span = max - min || 1;
  const x = (i: number) => ((i / (vs.length - 1)) * (width - 1)).toFixed(1);
  const y = (v: number) =>
    (height - 1 - ((v - min) / span) * (height - 2)).toFixed(1);
  const line = vs.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  // A zero baseline only when the series crosses zero (e.g. a swing to losses).
  const zeroY = min < 0 && max > 0 ? y(0) : null;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      preserveAspectRatio="none"
      aria-hidden
      className={`shrink-0 ${className}`}
    >
      {zeroY !== null && (
        <line
          x1="0"
          x2={width}
          y1={zeroY}
          y2={zeroY}
          stroke="var(--line)"
          strokeWidth="0.5"
        />
      )}
      <polyline
        points={line}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
