import type { ReactNode } from "react";

type Variant = "page" | "section" | "document" | "editorial";

interface SectionHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /**
   * "editorial": a PUBLIC page's title, on the editorial scale from
   *   DESIGN.md (38-46px). The public pages were using "page", which is the
   *   22px application scale, so /methodology and /how-to-use opened at a
   *   smaller size than the homepage's section headings.
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
  editorial: "ed-title text-ink",
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
  const Heading = as ?? (variant === "page" || variant === "editorial" ? "h1" : "h2");
  const editorial = variant === "editorial";
  return (
    <div
      className={`flex items-end justify-between gap-4 ${
        editorial ? "mb-8" : "mb-4"
      } ${className}`}
    >
      <div>
        <Heading className={TITLE_CLASS[variant]}>{title}</Heading>
        {subtitle !== undefined && subtitle !== null && (
          <p
            className={
              editorial ? "ed-intro mt-4" : "mt-0.5 text-sm text-ink-muted"
            }
          >
            {subtitle}
          </p>
        )}
      </div>
      {actions !== undefined && actions !== null && (
        <div className="shrink-0">{actions}</div>
      )}
    </div>
  );
}
