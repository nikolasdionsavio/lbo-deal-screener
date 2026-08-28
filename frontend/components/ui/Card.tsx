import type { ReactNode } from "react";

/** How the block is separated from what surrounds it.
 *
 * DESIGN.md makes ruling the governing device: information sits directly on the
 * page, separated by hairlines, and a four-sided container has to earn itself.
 * The target is roughly ten rules to every box. This component was the main
 * reason the app sat nearer two to one, because it drew a rounded, filled,
 * bordered box 52 times over.
 *
 * So `section` is the default: a single top rule and the spacing that goes with
 * it. `panel` keeps the old enclosure, for the few places where the content
 * really is a separate interaction surface, such as a form to fill in or an
 * auth prompt, rather than just a group of figures that belongs to the page.
 */
type CardVariant = "section" | "panel";

interface CardProps {
  children: ReactNode;
  className?: string;
  variant?: CardVariant;
}

export default function Card({
  children,
  className = "",
  variant = "section",
}: CardProps) {
  if (variant === "panel") {
    return (
      <div className={`glass rounded-lg border border-line p-5 ${className}`}>
        {children}
      </div>
    );
  }
  return (
    <div className={`border-t border-line pt-4 ${className}`}>{children}</div>
  );
}
