"use client";

// Public chrome. A composed wordmark, a short set of text links, a thin rule.
// No app navigation, no second search competing with the page's own search
// field, no stacked CTAs.
//
// The nav carries one piece of motion and it is a functional one: a single
// indicator that TRAVELS between links rather than each link lighting up
// independently. That is spatial continuity applied to navigation, and it is
// the difference between a menu that reads as one object and a menu that reads
// as five unrelated ones. The indicator is measured from the live DOM, so it
// stays correct when the labels, the font or the language change.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import Wordmark from "@/components/chrome/Wordmark";
import Container from "@/components/ui/Container";
import { useAuth } from "@/lib/auth";
import { prefersReducedMotion } from "@/lib/motion";

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
  const pathname = usePathname() ?? "/";
  const navRef = useRef<HTMLDivElement | null>(null);
  const [rail, setRail] = useState<{ x: number; w: number; on: boolean }>({
    x: 0,
    w: 0,
    on: false,
  });

  const active = LINKS.findIndex((l) => pathname.startsWith(l.href));

  // Park the indicator under the current route so it has somewhere to rest,
  // and somewhere to return to when the pointer leaves.
  const measure = useCallback((index: number, showWhenInactive = false) => {
    const nav = navRef.current;
    if (!nav) return;
    if (index < 0) {
      setRail((r) => ({ ...r, on: showWhenInactive }));
      return;
    }
    const el = nav.querySelectorAll<HTMLElement>("[data-nav]")[index];
    if (!el) return;
    const navBox = nav.getBoundingClientRect();
    const box = el.getBoundingClientRect();
    setRail({ x: box.left - navBox.left, w: box.width, on: true });
  }, []);

  useEffect(() => {
    measure(active, false);
    const onResize = () => measure(active, false);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [active, measure, pathname]);

  const reduced = typeof window !== "undefined" && prefersReducedMotion();

  return (
    <header className="glass-chrome sticky top-0 z-30 border-b border-line">
      <Container>
        <div className="flex items-center justify-between gap-6 py-5">
          <Wordmark />

          <nav className="flex items-center gap-6" aria-label="Site">
            <div
              ref={navRef}
              className="relative hidden items-center gap-6 sm:flex"
              onPointerLeave={() => measure(active, false)}
            >
              {LINKS.map((l, i) => (
                <Link
                  key={l.href}
                  href={l.href}
                  data-nav
                  aria-current={i === active ? "page" : undefined}
                  onPointerEnter={() => measure(i, true)}
                  onFocus={() => measure(i, true)}
                  className={`nav-link py-1 text-[0.875rem] transition-colors ${
                    i === active
                      ? "text-ink"
                      : "text-ink-secondary hover:text-ink"
                  }`}
                >
                  {l.label}
                </Link>
              ))}

              {/* One indicator for the whole nav. It slides; the links do not
                  each grow their own underline. */}
              <span
                aria-hidden
                className="nav-rail"
                style={{
                  transform: `translate3d(${rail.x}px, 0, 0) scaleX(${rail.w})`,
                  opacity: rail.on ? 1 : 0,
                  transition: reduced
                    ? "opacity var(--dur-fast) linear"
                    : "transform var(--spring-responsive-ms) var(--spring-responsive), opacity var(--dur-fast) var(--ease-smooth)",
                }}
              />
            </div>

            <Link
              href={user ? "/deals" : "/login"}
              className="link-slide text-[0.875rem] text-link"
            >
              {user ? "Saved deals" : "Log in"}
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
          {LINKS.map((l, i) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={i === active ? "page" : undefined}
              className={`hit-target whitespace-nowrap text-[0.8125rem] transition-colors ${
                i === active
                  ? "text-ink underline decoration-brand decoration-2 underline-offset-[6px]"
                  : "text-ink-secondary"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </Container>
    </header>
  );
}
