import Link from "next/link";
import type { ReactNode } from "react";

/** Em dash for a missing figure, muted so it reads as "no data", not zero. */
export const MISSING = (
  <span title="Not available" className="font-normal text-ink-muted">
    —
  </span>
);

function ChevronRight({ className = "" }: { className?: string }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={className}
    >
      <path d="M6 4l4 4-4 4" />
    </svg>
  );
}

/** A titled column of figure rows inside a ledger (e.g. "At market"). */
export function FigureGroup({
  heading,
  className = "",
  children,
}: {
  heading: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={className}>
      <div className="mb-1.5 text-xs font-medium text-ink-muted">{heading}</div>
      <div>{children}</div>
    </div>
  );
}

/** One label/value line of a key-figures ledger: label (and optional sub) on
 *  the left, right-aligned tabular value on the right, a hairline rule above
 *  (the first row in a group drops it). A linked row is the whole line and, on
 *  hover, shifts its value to brand ink and reveals a chevron, signalling the
 *  drill-down without a box or a lift. */
export function FigureRow({
  label,
  value,
  sub,
  emphasis = false,
  href,
  hrefTitle,
}: {
  label: ReactNode;
  value: ReactNode;
  sub?: ReactNode;
  emphasis?: boolean;
  href?: string;
  hrefTitle?: string;
}) {
  const valueClass = `shrink-0 tabular-nums tracking-tight text-ink ${
    emphasis ? "text-base font-semibold" : "text-[15px] font-semibold"
  }`;
  const rowClass =
    "flex items-baseline justify-between gap-6 border-t border-line py-2.5 first:border-t-0";

  const labelBlock = (
    <div className="min-w-0">
      <div className="text-sm text-ink-secondary transition-colors group-hover:text-ink">
        {label}
      </div>
      {sub !== undefined && sub !== null && (
        <div className="mt-0.5 text-xs leading-snug text-ink-muted">{sub}</div>
      )}
    </div>
  );

  if (href !== undefined) {
    return (
      <Link
        href={href}
        title={hrefTitle}
        className={`group -mx-2 rounded-md px-2 transition-colors duration-150 hover:bg-brand-soft ${rowClass}`}
      >
        {labelBlock}
        <div className={`flex items-baseline gap-1 group-hover:text-brand-text ${valueClass}`}>
          {value}
          <ChevronRight className="h-3 w-3 shrink-0 -translate-x-0.5 text-ink-muted opacity-0 transition-[transform,opacity,color] duration-150 group-hover:translate-x-0 group-hover:text-brand-text group-hover:opacity-100" />
        </div>
      </Link>
    );
  }
  return (
    <div className={rowClass}>
      {labelBlock}
      <div className={valueClass}>{value}</div>
    </div>
  );
}
