import type { ReactNode } from "react";

// Route-change entrance (DESIGN.md Motion; PRODUCT register: motion conveys
// state — "a new page arrived"). The template remounts on every navigation,
// re-running the 180ms fade + 4px rise defined in globals.css. CSS-only, so
// content is visible by default without JS and under reduced motion.
export default function Template({ children }: { children: ReactNode }) {
  return <div className="route-enter">{children}</div>;
}
