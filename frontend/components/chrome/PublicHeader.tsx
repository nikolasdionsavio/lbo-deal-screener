"use client";

// Public chrome (DESIGN.md: public pages are editorial and are NOT forced into
// the application shell). A composed wordmark, a short set of text links, and a
// thin rule. No app navigation, no second search competing with the page's own
// search field, no stacked CTAs.

import Link from "next/link";
import Wordmark from "@/components/chrome/Wordmark";
import Container from "@/components/ui/Container";
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

  // Four short labels do not need a hamburger. Hiding them behind one would
  // cost a tap and a menu to reach a link that fits on the screen. They move
  // to their own row under the wordmark instead, which is why this is a
  // two-row header on mobile and a single row from 640px up.
  const account = user
    ? { href: "/deals", label: "Saved deals" }
    : { href: "/login", label: "Log in" };

  return (
    <header className="border-b border-line">
      <Container>
        <div className="flex items-center justify-between gap-6 py-5">
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
            <Link
              href={account.href}
              className="text-[0.875rem] text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover"
            >
              {account.label}
            </Link>
          </nav>
        </div>

        {/* Mobile only. The links above are hidden below 640px; without this
            row the deal screen, methodology, changelog and about pages were
            unreachable from any public page on a phone. */}
        <nav
          className="flex gap-5 overflow-x-auto border-t border-line py-2.5 sm:hidden"
          aria-label="Site, mobile"
        >
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hit-target whitespace-nowrap text-[0.8125rem] text-ink-secondary transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </Container>
    </header>
  );
}
