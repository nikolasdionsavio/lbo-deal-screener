"use client";

// App sidebar (DESIGN.md Aesthetic v2): sits on --bg with a hairline right
// border in both themes (navy retired). Brand block, dashed-divider section
// rhythm, 16px 1.5px-stroke nav icons, and a raised-card active item.
// Manually collapsible (BUILD_SPEC section 19.8 app chrome): a chevron in
// the brand block toggles a 64px icon rail (title-attr tooltips, raised
// active icon card, icon-only theme toggle), persisted in
// localStorage("sidebar_collapsed"); never auto-collapses.
//
// Two variants: "desktop" (default) is the sticky lg+ sidebar, hidden below
// lg; "drawer" renders the same content inside the mobile off-canvas panel
// (components/chrome/MobileNav.tsx) — always expanded, no collapse toggle,
// sized by the panel.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ComponentType } from "react";
import Logo from "@/components/Logo";
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

function GuideIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M3 2.5h6a2 2 0 0 1 2 2v9a1.5 1.5 0 0 0-1.5-1.5H3V2.5Z" />
      <path d="M13 2.5H9a2 2 0 0 0-2 2v9a1.5 1.5 0 0 1 1.5-1.5H13V2.5Z" />
    </svg>
  );
}

function InfoIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="M8 7.25v3.75" />
      <path d="M8 5h.01" />
    </svg>
  );
}

function MailIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="1.75" y="3.5" width="12.5" height="9" rx="1.5" />
      <path d="m2.5 4.5 5.5 4 5.5-4" />
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

function ChevronLeftIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M10 3 5 8l5 5" />
    </svg>
  );
}

function ChevronRightIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="m6 3 5 5-5 5" />
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

// App-level links (not company-scoped): always shown, regardless of whether a
// ticker is selected.
const APP_PAGES: {
  href: string;
  label: string;
  Icon: ComponentType<IconProps>;
}[] = [
  { href: "/how-to-use", label: "How to use", Icon: GuideIcon },
  { href: "/about", label: "About", Icon: InfoIcon },
  { href: "/contact", label: "Contact", Icon: MailIcon },
];

/**
 * Theme toggle for the sidebar footer. Cycles light → dark → light and shows
 * the current state. The label is gated on mount: the server renders a
 * neutral placeholder because the active theme is only known on the client.
 * Collapsed rail: icon-only with the label moved to title/aria-label.
 */
function ThemeToggle({ collapsed }: { collapsed: boolean }) {
  const { theme, toggle } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && theme === "dark";
  const label = mounted
    ? `Switch to ${isDark ? "light" : "dark"} theme`
    : "Toggle theme";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={collapsed ? label : undefined}
      className={`flex items-center rounded-full text-xs text-ink-muted transition-colors duration-150 hover:bg-brand-soft hover:text-ink ${
        collapsed
          ? "mx-auto h-8 w-8 justify-center"
          : "w-full gap-2.5 px-3 py-1.5"
      }`}
    >
      {isDark ? <MoonIcon /> : <SunIcon />}
      {!collapsed && (
        <span>
          {mounted ? (isDark ? "Dark theme" : "Light theme") : "Theme"}
        </span>
      )}
    </button>
  );
}

// Active item: raised card (surface, hairline border, card shadow, 8px
// radius). Inactive: quiet ink-muted with a soft hover. The transparent
// border on inactive items keeps geometry stable across states. The
// collapsed rail keeps both treatments on a centered icon square.
function linkClass(active: boolean, collapsed: boolean): string {
  const shape = collapsed
    ? "h-9 w-10 justify-center"
    : "gap-2.5 px-3 py-1.5";
  return `flex items-center rounded border text-sm transition-colors duration-150 ${shape} ${
    active
      ? "border-line bg-surface font-medium text-ink shadow-card"
      : "border-transparent text-ink-muted hover:bg-brand-soft hover:text-ink"
  }`;
}

const COLLAPSE_KEY = "sidebar_collapsed";

interface SidebarProps {
  variant?: "desktop" | "drawer";
}

export default function Sidebar({ variant = "desktop" }: SidebarProps) {
  const isDrawer = variant === "drawer";
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const match = pathname ? /^\/company\/([^/]+)/.exec(pathname) : null;
  const routeTicker = match ? decodeURIComponent(match[1]).toUpperCase() : null;

  const [storedTicker, setStoredTicker] = useState<string | null>(null);

  // Collapse state restores from localStorage after mount (the server cannot
  // know it); the width transition only arms after that restore so a reload
  // into a collapsed rail does not animate.
  const [collapsed, setCollapsed] = useState(false);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    // The drawer never collapses; only the desktop sidebar restores the rail.
    if (isDrawer) return;
    setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === "1");
    setRestored(true);
  }, [isDrawer]);

  function toggleCollapsed() {
    setCollapsed((value) => {
      const next = !value;
      try {
        window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        // Persistence is best-effort; the in-session state still applies.
      }
      return next;
    });
  }

  useEffect(() => {
    if (routeTicker) {
      window.localStorage.setItem("lastTicker", routeTicker);
      setStoredTicker(routeTicker);
    } else {
      setStoredTicker(window.localStorage.getItem("lastTicker"));
    }
  }, [routeTicker]);

  const ticker = routeTicker ?? storedTicker;

  const toggleButton = (
    <button
      type="button"
      onClick={toggleCollapsed}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-ink-muted transition-colors duration-150 hover:bg-brand-soft hover:text-ink"
    >
      {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
    </button>
  );

  return (
    <aside
      className={
        isDrawer
          ? "flex h-full w-full flex-col overflow-y-auto overflow-x-hidden bg-bg"
          : `sticky top-0 hidden h-screen shrink-0 flex-col overflow-y-auto overflow-x-hidden border-r border-line bg-bg lg:flex ${
              collapsed ? "w-16" : "w-60"
            } ${restored ? "transition-[width] duration-200 ease-out" : ""}`
      }
    >
      <div className={collapsed ? "px-2 pb-4 pt-6" : "px-5 pb-4 pt-6"}>
        {collapsed ? (
          <div className="flex flex-col items-center gap-3">
            <Link
              href="/"
              className="flex justify-center"
              aria-label="Investment Intelligence home"
              title="Investment Intelligence"
            >
              <Logo size={24} />
            </Link>
            {toggleButton}
          </div>
        ) : (
          <div className="flex items-start justify-between gap-2">
            <Link href="/" className="flex min-w-0 items-center gap-2.5">
              <Logo size={26} className="shrink-0" />
              <span className="min-w-0">
                <span className="block whitespace-nowrap text-[15px] font-semibold leading-tight text-ink">
                  Investment Intelligence
                </span>
                <span className="mt-0.5 block whitespace-nowrap text-xs text-ink-muted">
                  Public company analysis
                </span>
              </span>
            </Link>
            {!isDrawer && toggleButton}
          </div>
        )}
      </div>
      <div className={`divider-dashed ${collapsed ? "mx-2" : "mx-5"}`} />

      <nav className={`flex-1 py-4 ${collapsed ? "px-2" : "px-3"}`}>
        <ul className={collapsed ? "flex flex-col items-center" : undefined}>
          <li>
            <Link
              href="/"
              className={linkClass(pathname === "/", collapsed)}
              title={collapsed ? "Search" : undefined}
            >
              <SearchIcon className="shrink-0" />
              {!collapsed && <span>Search</span>}
            </Link>
          </li>
        </ul>

        <div className="divider-dashed mx-2 my-4" />

        <div>
          {!collapsed && (
            <div className="px-3 pb-1.5 text-[11px] font-medium text-ink-muted">
              {ticker ? ticker : "Company"}
            </div>
          )}
          {ticker ? (
            <ul
              className={`space-y-0.5 ${
                collapsed ? "flex flex-col items-center" : ""
              }`}
            >
              {COMPANY_PAGES.map((page) => {
                const href = `/company/${encodeURIComponent(ticker)}/${page.slug}`;
                return (
                  <li key={page.slug}>
                    <Link
                      href={href}
                      className={linkClass(pathname === href, collapsed)}
                      title={collapsed ? page.label : undefined}
                    >
                      <page.Icon className="shrink-0" />
                      {!collapsed && <span>{page.label}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : (
            <>
              <ul
                className={`space-y-0.5 ${
                  collapsed ? "flex flex-col items-center" : ""
                }`}
              >
                {COMPANY_PAGES.map((page) => (
                  <li key={page.slug}>
                    <span
                      className={`flex cursor-not-allowed items-center rounded border border-transparent text-sm text-ink-muted opacity-50 ${
                        collapsed
                          ? "h-9 w-10 justify-center"
                          : "gap-2.5 px-3 py-1.5"
                      }`}
                      title={
                        collapsed
                          ? `${page.label} — search a company first`
                          : "Search a company first"
                      }
                      aria-disabled="true"
                    >
                      <page.Icon className="shrink-0" />
                      {!collapsed && <span>{page.label}</span>}
                    </span>
                  </li>
                ))}
              </ul>
              {!collapsed && (
                <p className="px-3 pt-1.5 text-[11px] text-ink-muted">
                  Search a company first
                </p>
              )}
            </>
          )}
        </div>

        <div className="divider-dashed mx-2 my-4" />

        <ul className={collapsed ? "flex flex-col items-center" : undefined}>
          <li>
            <Link
              href="/deals"
              className={linkClass(pathname === "/deals", collapsed)}
              title={collapsed ? "Saved Deals" : undefined}
            >
              <BookmarkIcon className="shrink-0" />
              {!collapsed && <span>Saved Deals</span>}
            </Link>
          </li>
        </ul>

        <div className="divider-dashed mx-2 my-4" />

        <ul
          className={`space-y-0.5 ${
            collapsed ? "flex flex-col items-center" : ""
          }`}
        >
          {APP_PAGES.map((page) => (
            <li key={page.href}>
              <Link
                href={page.href}
                className={linkClass(pathname === page.href, collapsed)}
                title={collapsed ? page.label : undefined}
              >
                <page.Icon className="shrink-0" />
                {!collapsed && <span>{page.label}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className={`divider-dashed ${collapsed ? "mx-2" : "mx-5"}`} />
      <div className={`py-4 ${collapsed ? "px-2" : "px-3"}`}>
        <ThemeToggle collapsed={collapsed} />
        {!collapsed && (
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
        )}
      </div>
    </aside>
  );
}
