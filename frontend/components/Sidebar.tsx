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
import { useEffect, useRef, useState, type ComponentType } from "react";
import { createPortal } from "react-dom";
import Wordmark from "@/components/chrome/Wordmark";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { APP_VERSION } from "@/lib/version";

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

function PrinterIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M4.5 6V2.5h7V6" />
      <rect x="2.5" y="6" width="11" height="5" rx="1" />
      <path d="M4.5 9.5h7v4h-7z" />
    </svg>
  );
}

function CompassIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="m10.6 5.4-1.3 3.9-3.9 1.3 1.3-3.9z" />
    </svg>
  );
}

function SparkleIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M8 1.75 9.35 6.65 14.25 8 9.35 9.35 8 14.25 6.65 9.35 1.75 8 6.65 6.65Z" />
    </svg>
  );
}

function MarketsIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M2 13.5h12" />
      <rect x="3" y="8" width="2.2" height="3.5" rx="0.4" />
      <rect x="6.9" y="5.5" width="2.2" height="6" rx="0.4" />
      <rect x="10.8" y="3" width="2.2" height="8.5" rx="0.4" />
    </svg>
  );
}

function FilterIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M2.5 3.5h11l-4.3 5.1v4.15l-2.4 1.2V8.6z" />
    </svg>
  );
}

function GlobeIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="M1.9 8h12.2M8 1.75c1.9 1.95 1.9 10.55 0 12.5M8 1.75c-1.9 1.95-1.9 10.55 0 12.5" />
    </svg>
  );
}

function HeatmapIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="2" y="2" width="3.4" height="3.4" rx="0.6" />
      <rect x="6.3" y="2" width="3.4" height="3.4" rx="0.6" />
      <rect x="10.6" y="2" width="3.4" height="3.4" rx="0.6" />
      <rect x="2" y="6.3" width="3.4" height="3.4" rx="0.6" />
      <rect x="6.3" y="6.3" width="3.4" height="3.4" rx="0.6" />
      <rect x="10.6" y="6.3" width="3.4" height="3.4" rx="0.6" />
      <rect x="2" y="10.6" width="3.4" height="3.4" rx="0.6" />
      <rect x="6.3" y="10.6" width="3.4" height="3.4" rx="0.6" />
      <rect x="10.6" y="10.6" width="3.4" height="3.4" rx="0.6" />
    </svg>
  );
}

function CalendarDaysIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <rect x="2" y="3" width="12" height="11" rx="1.5" />
      <path d="M2 6.5h12M5 1.75v2.5M11 1.75v2.5" />
      <path d="M5 9h.01M8 9h.01M11 9h.01M5 11.5h.01M8 11.5h.01" />
    </svg>
  );
}

function ActivityIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M1.75 8h2.4l1.7-4.2 3.1 8.4 1.7-4.2h3.6" />
    </svg>
  );
}

function ChevronDownIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="m3.5 6 4.5 4.5L12.5 6" />
    </svg>
  );
}

function TargetIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="6.25" />
      <circle cx="8" cy="8" r="3.25" />
      <circle cx="8" cy="8" r="0.5" />
    </svg>
  );
}

function PieIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="M8 8V1.75M8 8l4.4 4.4" />
    </svg>
  );
}

function CoinsIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <ellipse cx="8" cy="4.5" rx="5" ry="2.25" />
      <path d="M3 4.5V8c0 1.24 2.24 2.25 5 2.25S13 9.24 13 8V4.5" />
      <path d="M3 8v3.5c0 1.24 2.24 2.25 5 2.25s5-1.01 5-2.25V8" />
    </svg>
  );
}

function ShieldIcon({ className }: IconProps) {
  return (
    <svg {...iconAttrs(className)}>
      <path d="M8 1.75 13 3.5v4c0 3.2-2.1 5.6-5 6.75-2.9-1.15-5-3.55-5-6.75v-4z" />
      <path d="M8 5.5v3M8 10.5h.01" />
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

// Company-scoped pages. `slug` builds the default /company/{ticker}/{slug}
// href; an optional `build` overrides it for pages that live outside that tree
// (the IC one-pager renders chrome-free at /onepager/{ticker}).
// Grouped by research stage, not a flat equal menu (DESIGN.md): the analysis
// path first, then the market view, then the export. KPIs -> Operations and
// Deal Score -> Screening score match the redesigned pages.
const COMPANY_PAGES: {
  slug: string;
  label: string;
  group: string;
  Icon: ComponentType<IconProps>;
  build?: (ticker: string) => string;
}[] = [
  { slug: "dashboard", label: "Overview", group: "Analysis", Icon: GridIcon },
  { slug: "kpis", label: "Operations", group: "Analysis", Icon: PercentIcon },
  { slug: "financials", label: "Financials", group: "Analysis", Icon: TableIcon },
  { slug: "valuation", label: "Valuation", group: "Analysis", Icon: ScalesIcon },
  { slug: "peers", label: "Peers", group: "Analysis", Icon: PeopleIcon },
  { slug: "lbo", label: "LBO", group: "Analysis", Icon: CalculatorIcon },
  { slug: "score", label: "Screening score", group: "Analysis", Icon: GaugeIcon },
  { slug: "memo", label: "Memo", group: "Analysis", Icon: DocumentIcon },
  { slug: "news", label: "News", group: "Analysis", Icon: NewspaperIcon },
  { slug: "analysts", label: "Analysts", group: "Market view", Icon: TargetIcon },
  { slug: "ownership", label: "Ownership", group: "Market view", Icon: PieIcon },
  { slug: "dividends", label: "Dividends", group: "Market view", Icon: CoinsIcon },
  { slug: "risks", label: "Risks", group: "Market view", Icon: ShieldIcon },
  {
    slug: "onepager",
    label: "IC one-pager",
    group: "Export",
    Icon: PrinterIcon,
    build: (ticker) => `/onepager/${encodeURIComponent(ticker)}`,
  },
];

const companyHref = (
  page: (typeof COMPANY_PAGES)[number],
  ticker: string,
): string =>
  page.build
    ? page.build(ticker)
    : `/company/${encodeURIComponent(ticker)}/${page.slug}`;

// App-level links (not company-scoped): always shown, regardless of whether a
// ticker is selected.
const APP_PAGES: {
  href: string;
  label: string;
  Icon: ComponentType<IconProps>;
}[] = [
  { href: "/whats-new", label: "What's New", Icon: SparkleIcon },
  { href: "/methodology", label: "Methodology", Icon: CompassIcon },
  { href: "/how-to-use", label: "How to use", Icon: GuideIcon },
  { href: "/about", label: "About", Icon: InfoIcon },
  { href: "/contact", label: "Contact", Icon: MailIcon },
];

// "Markets" hover-flyout tools. Global tools link to /markets/*; a company tool
// (`slug` set) links to /company/{ticker}/{slug} and is disabled without a
// ticker. All are TradingView-powered market context, distinct from the app's
// own analysis pages.
interface MarketTool {
  label: string;
  desc: string;
  Icon: ComponentType<IconProps>;
  href?: string; // global tools
  slug?: string; // company-scoped tools
}

const MARKET_TOOLS: MarketTool[] = [
  {
    label: "Stock Screener",
    desc: "Filter the market by fundamentals",
    Icon: FilterIcon,
    href: "/markets/screener",
  },
  {
    label: "Markets Overview",
    desc: "Indices, futures, bonds and FX",
    Icon: GlobeIcon,
    href: "/markets/overview",
  },
  {
    label: "Sector Heatmap",
    desc: "S&P 500 by sector and size",
    Icon: HeatmapIcon,
    href: "/markets/heatmap",
  },
  {
    label: "Economic Calendar",
    desc: "Upcoming macro releases",
    Icon: CalendarDaysIcon,
    href: "/markets/calendar",
  },
  {
    label: "Technicals",
    desc: "Indicator and oscillator read",
    Icon: ActivityIcon,
    slug: "technicals",
  },
];

/** Resolve a tool's destination, or null when a company tool has no ticker. */
function toolHref(tool: MarketTool, ticker: string | null): string | null {
  if (tool.href) return tool.href;
  if (tool.slug && ticker)
    return `/company/${encodeURIComponent(ticker)}/${tool.slug}`;
  return null;
}

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
    : "gap-2.5 py-1.5 pl-2.5 pr-3";
  // Selected item: a 2px accent line + a faint accent wash + a small weight
  // bump (DESIGN.md application shell). No pill, no raised card. The left
  // border stays 2px in both states so geometry never shifts.
  return `flex items-center border-l-2 text-[0.8125rem] transition-colors duration-150 ${shape} ${
    active
      ? "border-l-brand bg-brand-soft font-medium text-ink"
      : "border-l-transparent text-ink-secondary hover:bg-brand-soft hover:text-ink"
  }`;
}

// The Markets tool rows, shared by the desktop flyout and the mobile accordion.
function MarketToolItems({
  ticker,
  pathname,
  onNavigate,
}: {
  ticker: string | null;
  pathname: string | null;
  onNavigate: () => void;
}) {
  return (
    <>
      {MARKET_TOOLS.map((tool) => {
        const href = toolHref(tool, ticker);
        const active = href !== null && pathname === href;
        if (href === null) {
          return (
            <span
              key={tool.label}
              aria-disabled="true"
              title="Search a company first"
              className="flex cursor-not-allowed items-start gap-2.5 rounded-lg px-2.5 py-2 opacity-50"
            >
              <tool.Icon className="mt-0.5 shrink-0 text-ink-muted" />
              <span className="min-w-0">
                <span className="block text-sm text-ink">{tool.label}</span>
                <span className="block text-xs text-ink-muted">
                  Search a company first
                </span>
              </span>
            </span>
          );
        }
        return (
          <Link
            key={tool.label}
            href={href}
            role="menuitem"
            onClick={onNavigate}
            className={`flex items-start gap-2.5 rounded-lg px-2.5 py-2 transition-colors duration-150 ${
              active
                ? "bg-surface-sunken text-ink"
                : "text-ink-secondary hover:bg-brand-soft hover:text-ink"
            }`}
          >
            <tool.Icon className="mt-0.5 shrink-0 text-ink-muted" />
            <span className="min-w-0">
              <span className="block text-sm font-medium text-ink">
                {tool.label}
              </span>
              <span className="block text-xs text-ink-muted">{tool.desc}</span>
            </span>
          </Link>
        );
      })}
    </>
  );
}

// "Markets" nav entry. Desktop: a hover/focus flyout, positioned fixed so it
// escapes the sidebar's overflow clip; closes on Esc, scroll, resize, route
// change, and blur-out. Mobile drawer: an inline accordion (no hover on touch).
function MarketsNav({
  collapsed,
  isDrawer,
  ticker,
  pathname,
}: {
  collapsed: boolean;
  isDrawer: boolean;
  ticker: string | null;
  pathname: string | null;
}) {
  const anyActive = MARKET_TOOLS.some((t) => {
    const h = toolHref(t, ticker);
    return h !== null && pathname === h;
  });

  const [expanded, setExpanded] = useState(anyActive);
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(
    null,
  );
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    // The panel is portaled to <body>, so it is not a DOM descendant of the
    // trigger; "inside" is measured against both refs explicitly.
    const inside = (node: Node | null) =>
      node !== null &&
      (triggerRef.current?.contains(node) ||
        panelRef.current?.contains(node)) === true;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    function onFocusIn(e: FocusEvent) {
      if (!inside(e.target as Node | null)) setOpen(false);
    }
    function onPointerDown(e: Event) {
      if (!inside(e.target as Node | null)) setOpen(false);
    }
    function dismiss() {
      setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", dismiss);
    // Capture phase so the sidebar's own scroll container also dismisses.
    window.addEventListener("scroll", dismiss, true);
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", dismiss);
      window.removeEventListener("scroll", dismiss, true);
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  if (isDrawer) {
    return (
      <li>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className={`${linkClass(anyActive, false)} w-full`}
        >
          <MarketsIcon className="shrink-0" />
          <span className="flex-1 text-left">Markets</span>
          <ChevronDownIcon
            className={`shrink-0 transition-transform duration-150 ${
              expanded ? "" : "-rotate-90"
            }`}
          />
        </button>
        {expanded && (
          <div className="mt-0.5 space-y-0.5 pl-3.5">
            <MarketToolItems
              ticker={ticker}
              pathname={pathname}
              onNavigate={() => {}}
            />
          </div>
        )}
      </li>
    );
  }

  function openNow() {
    const el = triggerRef.current;
    if (el) {
      const r = el.getBoundingClientRect();
      const estPanelHeight = 300;
      const top = Math.max(
        8,
        Math.min(r.top, window.innerHeight - estPanelHeight - 8),
      );
      setCoords({ top, left: r.right + 6 });
    }
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpen(true);
  }
  function closeSoon() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setOpen(false), 140);
  }

  return (
    <li onMouseEnter={openNow} onMouseLeave={closeSoon} onFocus={openNow}>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        title={collapsed ? "Markets" : undefined}
        className={`${linkClass(anyActive, collapsed)} w-full`}
        onKeyDown={(e) => {
          // The portaled panel is outside the tab order, so open on
          // ArrowDown / Enter / Space and move focus into the first tool.
          if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openNow();
            setTimeout(() => {
              (
                panelRef.current?.querySelector(
                  'a[role="menuitem"]',
                ) as HTMLElement | null
              )?.focus();
            }, 0);
          }
        }}
      >
        <MarketsIcon className="shrink-0" />
        {!collapsed && <span className="flex-1 text-left">Markets</span>}
        {!collapsed && <ChevronRightIcon className="shrink-0 opacity-50" />}
      </button>
      {open &&
        coords &&
        typeof document !== "undefined" &&
        createPortal(
          // Portaled to <body> so the fixed panel escapes the sticky sidebar's
          // stacking context (otherwise page content, e.g. an embed iframe,
          // paints over it).
          <div
            ref={panelRef}
            role="menu"
            aria-label="Markets tools"
            onMouseEnter={openNow}
            onMouseLeave={closeSoon}
            style={{ position: "fixed", top: coords.top, left: coords.left }}
            className="z-50 w-64 rounded-xl border border-line bg-surface p-1.5 shadow-[0_8px_28px_rgba(15,23,42,0.14)]"
          >
            <MarketToolItems
              ticker={ticker}
              pathname={pathname}
              onNavigate={() => setOpen(false)}
            />
          </div>,
          document.body,
        )}
    </li>
  );
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
              className="font-display text-[1.1rem] font-semibold leading-none text-ink"
              aria-label="Investment Intelligence home"
              title="Investment Intelligence"
            >
              II
            </Link>
            {toggleButton}
          </div>
        ) : (
          <div className="flex items-start justify-between gap-2">
            <Wordmark size="compact" />
            {!isDrawer && <span className="shrink-0">{toggleButton}</span>}
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
              {COMPANY_PAGES.map((page, i) => {
                const href = companyHref(page, ticker);
                const showGroup =
                  !collapsed &&
                  (i === 0 || COMPANY_PAGES[i - 1].group !== page.group);
                return (
                  <li key={page.slug} className={showGroup ? "pt-2 first:pt-0" : ""}>
                    {showGroup && (
                      <div className="px-2.5 pb-1 pt-1 font-mono text-[10px] uppercase tracking-[0.04em] text-ink-muted">
                        {page.group}
                      </div>
                    )}
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
                          ? `${page.label}: search a company first`
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

        <ul
          className={`space-y-0.5 ${
            collapsed ? "flex flex-col items-center" : ""
          }`}
        >
          <MarketsNav
            collapsed={collapsed}
            isDrawer={isDrawer}
            ticker={ticker}
            pathname={pathname}
          />
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
        {user ? (
          !collapsed && (
            <div className="mt-3 space-y-2 px-3">
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
          )
        ) : collapsed ? (
          // Collapsed rail: a single teal sign-up tile so the CTA never
          // disappears when the sidebar is narrowed.
          <div className="mt-3 flex justify-center">
            <Link
              href="/register"
              title="Register"
              aria-label="Register"
              className="flex h-9 w-9 items-center justify-center rounded bg-brand text-white transition-colors duration-150 hover:bg-brand-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <svg {...iconAttrs()}>
                <circle cx="6" cy="5.5" r="2.5" />
                <path d="M2 13.5a4 4 0 0 1 7.2-2.4" />
                <path d="M12.5 8v4M10.5 10h4" />
              </svg>
            </Link>
          </div>
        ) : (
          // Expanded: Register primary (green), Log in outline.
          <div className="mt-3 space-y-2 px-1">
            <Link
              href="/register"
              className="flex w-full items-center justify-center rounded bg-brand px-4 py-2 text-sm font-semibold text-white transition-colors duration-150 hover:bg-brand-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Register
            </Link>
            <Link
              href="/login"
              className="flex w-full items-center justify-center rounded border border-line-strong px-4 py-2 text-sm font-medium text-brand-text transition-colors duration-150 hover:border-brand hover:bg-brand-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Log in
            </Link>
          </div>
        )}
        {!collapsed && (
          <Link
            href="/whats-new"
            title="What's new"
            className="mt-3 block px-3 text-[11px] text-ink-muted transition-colors duration-150 hover:text-ink"
          >
            v{APP_VERSION} · What&apos;s new
          </Link>
        )}
      </div>
    </aside>
  );
}
