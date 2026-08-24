// The screen page is a client component, so it cannot export metadata itself.
// Without this it inherited the site default and went into the index under
// the homepage's title.

import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Deal screen",
  description:
    "Filter every US-listed filer on revenue, EBITDA, margin and net debt / EBITDA, taken from each company's own SEC filings. Built for sourcing, when you do not yet have a company in mind.",
  alternates: { canonical: "/screen" },
};

export default function ScreenLayout({ children }: { children: ReactNode }) {
  return children;
}
