import type { ReactNode } from "react";

type Variant = "page" | "section" | "document";

interface SectionHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /**
   * "page": the route's page title, set in the display serif.
   * "document": memo-style serif section heading (document character).
   * "section" (default): quiet UI section heading in the body face.
   */
  variant?: Variant;
  /**
   * Heading element override. Company pages pass "h2" on their page-variant
   * titles because the company layout already renders the page's single h1.
   */
  as?: "h1" | "h2" | "h3";
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
  as,
  className = "",
}: SectionHeaderProps) {
  const Heading = as ?? (variant === "page" ? "h1" : "h2");
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
