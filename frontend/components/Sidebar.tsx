"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

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
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col overflow-y-auto bg-brand">
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
    </aside>
  );
}
