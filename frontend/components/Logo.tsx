// Brand mark for Investment Intelligence. A navy rounded tile holding an
// "II" monogram drawn as two ascending bars (the initials doubling as a
// growth/analysis chart) with a focal dot above the taller bar — the moment
// of insight. Stays the brand navy in both themes (a constant anchor) and
// reads cleanly down to favicon size. The standalone favicon lives at
// app/icon.svg and mirrors this geometry with hardcoded colors.

interface LogoProps {
  size?: number;
  className?: string;
}

export default function Logo({ size = 28, className = "" }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Investment Intelligence"
      className={className}
    >
      <rect width="32" height="32" rx="8" fill="#1e3a5f" />
      {/* Ascending "II" bars */}
      <rect x="9.5" y="15" width="4" height="9" rx="2" fill="#f5f6f8" />
      <rect x="18.5" y="10.5" width="4" height="13.5" rx="2" fill="#f5f6f8" />
      {/* Focal dot — the insight, in the brand accent */}
      <circle cx="20.5" cy="7" r="2" fill="#2dd4bf" />
    </svg>
  );
}
