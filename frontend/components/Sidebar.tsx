"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

const COMPANY_PAGES = [
  { slug: "dashboard", label: "Dashboard" },
  { slug: "kpis", label: "KPIs" },
  { slug: "valuation", label: "Valuation" },
  { slug: "peers", label: "Peer Comps" },
  { slug: "lbo", label: "LBO Model" },
  { slug: "score", label: "Deal Score" },
  { slug: "memo", label: "Memo" },
  { slug: "news", label: "News" },
];

// Inline 16px icons, 1.5px stroke (DESIGN.md Iconography).
function SunIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

/**
 * Theme toggle for the sidebar footer. Cycles light → dark → light and shows
 * the current state. The label is gated on mount: the server renders a
 * neutral placeholder because the active theme is only known on the client.
 */
function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={
        mounted
          ? `Switch to ${isDark ? "light" : "dark"} theme`
          : "Toggle theme"
      }
      className="flex w-full items-center gap-2.5 rounded px-3 py-1.5 text-xs text-white/70 transition-colors hover:bg-white/5 hover:text-white"
    >
      {isDark ? <MoonIcon /> : <SunIcon />}
      <span>{mounted ? (isDark ? "Dark theme" : "Light theme") : "Theme"}</span>
    </button>
  );
}

function linkClass(active: boolean): string {
  return `block rounded px-3 py-1.5 text-sm transition-colors ${
    active
      ? "bg-white/10 font-medium text-white"
      : "text-white/70 hover:bg-white/5 hover:text-white"
  }`;
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const match = pathname ? /^\/company\/([^/]+)/.exec(pathname) : null;
  const routeTicker = match ? decodeURIComponent(match[1]).toUpperCase() : null;

  const [storedTicker, setStoredTicker] = useState<string | null>(null);

  useEffect(() => {
    if (routeTicker) {
      window.localStorage.setItem("lastTicker", routeTicker);
      setStoredTicker(routeTicker);
    } else {
      setStoredTicker(window.localStorage.getItem("lastTicker"));
    }
  }, [routeTicker]);

  const ticker = routeTicker ?? storedTicker;

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col overflow-y-auto bg-sidebar">
      <div className="px-5 pb-4 pt-6">
        <Link href="/" className="block">
          <div className="text-base font-semibold text-white">
            LBO Deal Screener
          </div>
          <div className="mt-0.5 text-xs text-white/60">
            PE screening for public companies
          </div>
        </Link>
      </div>

      <nav className="flex-1 space-y-6 px-3">
        <div>
          <Link href="/" className={linkClass(pathname === "/")}>
            Search
          </Link>
        </div>

        <div>
          <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-white/40">
            {ticker ? ticker : "Company"}
          </div>
          {ticker ? (
            <ul className="space-y-0.5">
              {COMPANY_PAGES.map((page) => {
                const href = `/company/${encodeURIComponent(ticker)}/${page.slug}`;
                return (
                  <li key={page.slug}>
                    <Link href={href} className={linkClass(pathname === href)}>
                      {page.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : (
            <>
              <ul className="space-y-0.5">
                {COMPANY_PAGES.map((page) => (
                  <li key={page.slug}>
                    <span
                      className="block cursor-not-allowed rounded px-3 py-1.5 text-sm text-white/30"
                      title="Search a company first"
                      aria-disabled="true"
                    >
                      {page.label}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="px-3 pt-1 text-[11px] text-white/40">
                Search a company first
              </p>
            </>
          )}
        </div>

        <div>
          <Link href="/deals" className={linkClass(pathname === "/deals")}>
            Saved Deals
          </Link>
        </div>
      </nav>

      <div className="border-t border-white/10 px-3 py-4">
        <ThemeToggle />
        <div className="mt-3">
          {user ? (
          <div className="space-y-2 px-3">
            <div className="truncate text-xs text-white/60" title={user.email}>
              {user.email}
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded border border-white/20 px-2.5 py-1 text-xs text-white/80 hover:bg-white/10"
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 text-sm">
            <Link href="/login" className="text-white/70 hover:text-white">
              Log in
            </Link>
            <span className="text-white/30">·</span>
            <Link href="/register" className="text-white/70 hover:text-white">
              Register
            </Link>
          </div>
        )}
        </div>
      </div>
    </aside>
  );
}
