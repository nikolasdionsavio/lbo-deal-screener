import type { ReactNode } from "react";

type Variant = "page" | "section" | "document";

interface SectionHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /**
   * "page": the route's h1 title, set in the display serif (one per page).
   * "document": memo-style serif section heading (document character).
   * "section" (default): quiet UI section heading in the body face.
   */
  variant?: Variant;
  className?: string;
}

const TITLE_CLASS: Record<Variant, string> = {
  page: "font-display text-[1.375rem] font-semibold leading-snug text-ink",
  section: "text-lg font-semibold text-ink",
  document: "font-display text-lg font-semibold text-ink",
};

export default function SectionHeader({
  title,
  subtitle,
  actions,
  variant = "section",
  className = "",
}: SectionHeaderProps) {
  const Heading = variant === "page" ? "h1" : "h2";
  return (
    <div className={`mb-4 flex items-end justify-between gap-4 ${className}`}>
      <div>
        <Heading className={TITLE_CLASS[variant]}>{title}</Heading>
        {subtitle !== undefined && subtitle !== null && (
          <p className="mt-0.5 text-sm text-ink-muted">{subtitle}</p>
        )}
      </div>
      {actions !== undefined && actions !== null && (
        <div className="shrink-0">{actions}</div>
      )}
    </div>
  );
}
