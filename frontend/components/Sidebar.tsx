"use client";

// App sidebar (DESIGN.md Aesthetic v2): sits on --bg with a hairline right
// border in both themes (navy retired). Brand block, dashed-divider section
// rhythm, 16px 1.5px-stroke nav icons, and a raised-card active item.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ComponentType } from "react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

// Inline 16px icons, 1.5px stroke (DESIGN.md Iconography). All inherit
// currentColor from the nav item text.
interface IconProps {
  className?: string;
}

function iconAttrs(className?: string) {
  return {
    width: 16,
    height: 16,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
    className,
  };
}

function SearchIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="7" cy="7" r="4.25" />
      <path d="M10.2 10.2 14 14" />
    </svg>
  );
}

function GridIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

function PercentIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M13 3 3 13" />
      <circle cx="4.5" cy="4.5" r="2" />
      <circle cx="11.5" cy="11.5" r="2" />
    </svg>
  );
}

function TableIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" />
      <path d="M1.5 6h13M1.5 9.75h13M6 6v7.5" />
    </svg>
  );
}

function ScalesIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M8 2.5v11M5.5 13.5h5M3 4.5h10" />
      <path d="m3 4.5-1.75 4.25h3.5L3 4.5ZM1.25 8.75a1.75 1.75 0 0 0 3.5 0" />
      <path d="m13 4.5-1.75 4.25h3.5L13 4.5ZM11.25 8.75a1.75 1.75 0 0 0 3.5 0" />
    </svg>
  );
}

function PeopleIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="6" cy="5" r="2.5" />
      <path d="M1.5 13.5v-.75a4.5 4.5 0 0 1 9 0v.75" />
      <path d="M10.5 2.8a2.5 2.5 0 0 1 0 4.4" />
      <path d="M14.5 13.5v-.75a4.5 4.5 0 0 0-3-4.25" />
    </svg>
  );
}

function CalculatorIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="3" y="1.5" width="10" height="13" rx="1.5" />
      <path d="M5.5 4.5h5" />
      <path d="M5.5 8h.01M8 8h.01M10.5 8h.01M5.5 11h.01M8 11h.01M10.5 11h.01" />
    </svg>
  );
}

function GaugeIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M2.6 12.5a6.25 6.25 0 1 1 10.8 0" />
      <path d="m8 10.5 2.75-2.75" />
    </svg>
  );
}

function DocumentIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M9.5 1.5h-5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V4.5l-3-3Z" />
      <path d="M9.5 1.5v3h3" />
      <path d="M5.5 8.5h5M5.5 11h5" />
    </svg>
  );
}

function NewspaperIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="1.5" y="3" width="13" height="10" rx="1.5" />
      <path d="M4 6h4.5M4 8.5h4.5M4 11h8" />
      <path d="M11 6h1.5v2.5H11z" />
    </svg>
  );
}

function BookmarkIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M3.75 2.5a1 1 0 0 1 1-1h6.5a1 1 0 0 1 1 1v12L8 11.25 3.75 14.5v-12Z" />
    </svg>
  );
}

function SunIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="2.75" />
      <path d="M8 1.5v1.5M8 13v1.5M3.4 3.4l1.06 1.06M11.54 11.54l1.06 1.06M1.5 8H3M13 8h1.5M3.4 12.6l1.06-1.06M11.54 4.46l1.06-1.06" />
    </svg>
  );
}

function MoonIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M14 8.53A6 6 0 1 1 7.47 2 4.67 4.67 0 0 0 14 8.53Z" />
    </svg>
  );
}

const COMPANY_PAGES: {
  slug: string;
  label: string;
  Icon: ComponentType<IconProps>;
}[] = [
  { slug: "dashboard", label: "Dashboard", Icon: GridIcon },
  { slug: "kpis", label: "KPIs", Icon: PercentIcon },
  { slug: "financials", label: "Financials", Icon: TableIcon },
  { slug: "valuation", label: "Valuation", Icon: ScalesIcon },
  { slug: "peers", label: "Peer Comps", Icon: PeopleIcon },
  { slug: "lbo", label: "LBO Model", Icon: CalculatorIcon },
  { slug: "score", label: "Deal Score", Icon: GaugeIcon },
  { slug: "memo", label: "Memo", Icon: DocumentIcon },
  { slug: "news", label: "News", Icon: NewspaperIcon },
];

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
      className="flex w-full items-center gap-2.5 rounded-full px-3 py-1.5 text-xs text-ink-muted transition-colors duration-150 hover:bg-brand-soft hover:text-ink"
    >
      {isDark ? <MoonIcon /> : <SunIcon />}
      <span>{mounted ? (isDark ? "Dark theme" : "Light theme") : "Theme"}</span>
    </button>
  );
}

// Active item: raised card (surface, hairline border, card shadow, 8px
// radius). Inactive: quiet ink-muted with a soft hover. The transparent
// border on inactive items keeps geometry stable across states.
function linkClass(active: boolean): string {
  return `flex items-center gap-2.5 rounded border px-3 py-1.5 text-sm transition-colors duration-150 ${
    active
      ? "border-line bg-surface font-medium text-ink shadow-card"
      : "border-transparent text-ink-muted hover:bg-brand-soft hover:text-ink"
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
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col overflow-y-auto border-r border-line bg-bg">
      <div className="px-5 pb-4 pt-6">
        <Link href="/" className="block">
          <div className="text-base font-semibold text-ink">
            LBO Deal Screener
          </div>
          <div className="mt-0.5 text-xs text-ink-muted">
            PE screening for public companies
          </div>
        </Link>
      </div>
      <div className="divider-dashed mx-5" />

      <nav className="flex-1 px-3 py-4">
        <div>
          <Link href="/" className={linkClass(pathname === "/")}>
            <SearchIcon className="shrink-0" />
            <span>Search</span>
          </Link>
        </div>

        <div className="divider-dashed mx-2 my-4" />

        <div>
          <div className="px-3 pb-1.5 text-[11px] font-medium text-ink-muted">
            {ticker ? ticker : "Company"}
          </div>
          {ticker ? (
            <ul className="space-y-0.5">
              {COMPANY_PAGES.map((page) => {
                const href = `/company/${encodeURIComponent(ticker)}/${page.slug}`;
                return (
                  <li key={page.slug}>
                    <Link href={href} className={linkClass(pathname === href)}>
                      <page.Icon className="shrink-0" />
                      <span>{page.label}</span>
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
                      className="flex cursor-not-allowed items-center gap-2.5 rounded border border-transparent px-3 py-1.5 text-sm text-ink-muted opacity-50"
                      title="Search a company first"
                      aria-disabled="true"
                    >
                      <page.Icon className="shrink-0" />
                      <span>{page.label}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="px-3 pt-1.5 text-[11px] text-ink-muted">
                Search a company first
              </p>
            </>
          )}
        </div>

        <div className="divider-dashed mx-2 my-4" />

        <div>
          <Link href="/deals" className={linkClass(pathname === "/deals")}>
            <BookmarkIcon className="shrink-0" />
            <span>Saved Deals</span>
          </Link>
        </div>
      </nav>

      <div className="divider-dashed mx-5" />
      <div className="px-3 py-4">
        <ThemeToggle />
        <div className="mt-3">
          {user ? (
            <div className="space-y-2 px-3">
              <div
                className="truncate text-xs text-ink-muted"
                title={user.email}
              >
                {user.email}
              </div>
              <button
                type="button"
                onClick={logout}
                className="rounded-full border border-line-strong px-2.5 py-1 text-xs text-ink-secondary transition-colors duration-150 hover:bg-surface-sunken hover:text-ink"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 text-sm">
              <Link
                href="/login"
                className="text-ink-muted transition-colors duration-150 hover:text-ink"
              >
                Log in
              </Link>
              <span className="text-line-strong">·</span>
              <Link
                href="/register"
                className="text-ink-muted transition-colors duration-150 hover:text-ink"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
