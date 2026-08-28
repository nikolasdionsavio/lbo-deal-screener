// The public grid from DESIGN.md ("max 1240px, outer margins 48-72 desktop,
// 28-40 tablet, 18-22 mobile"), as one component instead of the same three
// padding utilities retyped on every page.
//
// It exists so a section can opt OUT of the column: pages apply Container per
// section rather than once around everything, which lets a band run the full
// width of the viewport while its contents stay on the same grid lines as the
// sections above and below it.

import type { ReactNode } from "react";

export default function Container({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`mx-auto w-full max-w-[1240px] px-[18px] sm:px-8 lg:px-12 ${className}`}
    >
      {children}
    </div>
  );
}
