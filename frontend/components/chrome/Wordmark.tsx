import Link from "next/link";

// The identity is the product name, composed. No mark, no monogram, no glyph
// (DESIGN.md: the product name carries the identity).

export default function Wordmark({
  className = "",
  size = "default",
}: {
  className?: string;
  size?: "default" | "compact";
}) {
  const name =
    size === "compact"
      ? "text-[0.9375rem] leading-[1.1]"
      : "text-[1.0625rem] leading-[1.1]";

  return (
    <Link
      href="/"
      className={`group inline-block ${className}`}
      aria-label="Investment Intelligence, by Nikolas Savio"
    >
      <span
        className={`block font-display ${name} tracking-[-0.01em] text-ink transition-colors group-hover:text-brand-text`}
      >
        Investment Intelligence
      </span>
      <span className="mt-[3px] block font-mono text-[10px] tracking-[0.02em] text-ink-muted">
        by Nikolas Savio
      </span>
    </Link>
  );
}
