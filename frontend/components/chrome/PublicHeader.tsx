"use client";

// Public chrome (DESIGN.md: public pages are editorial and are NOT forced into
// the application shell). A composed wordmark, a short set of text links, and a
// thin rule. No app navigation, no second search competing with the page's own
// search field, no stacked CTAs.

import Link from "next/link";
import Wordmark from "@/components/chrome/Wordmark";
import { useAuth } from "@/lib/auth";

// The screen comes first: it is the one tool here, and the rest are reference
// pages. Without it the screen is only reachable from inside a company page,
// which makes it invisible to anyone arriving at the site.
const LINKS = [
  { href: "/screen", label: "Deal screen" },
  { href: "/methodology", label: "Methodology" },
  { href: "/changelog", label: "Changelog" },
  { href: "/about", label: "About" },
];

export default function PublicHeader() {
  const { user } = useAuth();

  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-[1240px] items-center justify-between gap-6 px-[18px] py-5 sm:px-8 lg:px-12">
        <Wordmark />

        <nav className="flex items-center gap-5" aria-label="Site">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hidden text-[0.875rem] text-ink-secondary transition-colors hover:text-ink sm:inline"
            >
              {l.label}
            </Link>
          ))}
          {user ? (
            <Link
              href="/deals"
              className="text-[0.875rem] text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover"
            >
              Saved deals
            </Link>
          ) : (
            <Link
              href="/login"
              className="text-[0.875rem] text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover"
            >
              Log in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
