// Single source of truth for the platform version and the What's New changelog.
// Bump APP_VERSION and prepend a Release entry whenever a user-facing change
// ships. The sidebar shows APP_VERSION; /whats-new renders RELEASES.

export const APP_VERSION = "1.5.0";

export interface Release {
  version: string;
  /** Human-readable release date. */
  date: string;
  title: string;
  changes: string[];
}

// Newest first. Keep entries factual — only features that actually shipped.
export const RELEASES: Release[] = [
  {
    version: "1.5.0",
    date: "3 July 2026",
    title: "Markets tools",
    changes: [
      "A new Markets menu (hover to open) with five market tools: a stock screener, a markets overview, a sector heatmap, an economic calendar, and per-company technicals.",
      "Powered by TradingView, kept clearly separate from — and complementary to — the app's primary-source fundamentals.",
    ],
  },
  {
    version: "1.4.0",
    date: "2 July 2026",
    title: "Deal-memo depth",
    changes: [
      "Sources & Uses table on the LBO, with transaction fees funded as a use and pro-forma opening leverage.",
      "Underwriting scenarios — base case bracketed by a strategic-buyer upside and a downturn downside — so returns read as a range, not a point estimate.",
      "Covenant-headroom stress panel testing each modeled year against a maintenance package (net leverage, interest coverage, DSCR).",
      "IC one-pager: a print-to-PDF deal summary composing the score, the returns range and the memo, reachable from the LBO page.",
      "This What's New page, a methodology page, and an in-app version marker.",
    ],
  },
  {
    version: "1.3.0",
    date: "1 July 2026",
    title: "Growth-company LBO",
    changes: [
      "Model high-growth companies with negative EBITDA on a revenue (EV/Revenue) basis, with a margin ramp to profitability and an EV/EBITDA exit once profitable.",
      "Honest guardrails: the return is framed as predicated on the operating assumptions rather than an unearned multiple re-rating.",
    ],
  },
  {
    version: "1.2.0",
    date: "June 2026",
    title: "Accounts & infrastructure",
    changes: [
      "Sign in with Google or GitHub.",
      "Institutional number presentation across the app (a diligence-grade tearsheet).",
      "Durable database and a hardened data pipeline.",
    ],
  },
  {
    version: "1.1.0",
    date: "June 2026",
    title: "Global coverage & polish",
    changes: [
      "Worldwide public companies (US, UK and Europe) with reporting-currency handling.",
      "Dark mode, mobile navigation and motion polish.",
    ],
  },
  {
    version: "1.0.0",
    date: "June 2026",
    title: "Platform launch",
    changes: [
      "Company dashboard, traceable KPIs and full financial statements.",
      "Valuation range, peer comparables and SEC filings.",
      "Editable five-year LBO with IRR / MoM and sensitivity grids.",
      "Transparent 0–100 deal score and a deterministic investment memo.",
      "Saved deals and company news.",
    ],
  },
];
