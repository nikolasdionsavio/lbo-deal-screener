// Single source of truth for the platform version and the What's New changelog.
// Bump APP_VERSION and prepend a Release entry whenever a user-facing change
// ships. The sidebar shows APP_VERSION; /whats-new renders RELEASES.

export const APP_VERSION = "1.7.0";

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
    version: "1.7.0",
    date: "3 July 2026",
    title: "Risk assessment",
    changes: [
      "A new Risks page: a rating-agency-style read combining a financial risk profile, sector context, and the company's own disclosed risk factors.",
      "Quantitative: Altman Z''-distress score, Piotroski F-score, and red-amber-green credit metrics (leverage, coverage, liquidity, cash runway, earnings-quality accruals) with the formula shown on each.",
      "Qualitative: the company's actual risk factors pulled verbatim from its 10-K (Item 1A), keyword-categorised and linked to the SEC filing — never summarised.",
      "Sector context: how the company's risk metrics compare to its peers, and a going-concern flag when the filing uses that language.",
    ],
  },
  {
    version: "1.6.0",
    date: "3 July 2026",
    title: "Analysts, Ownership & Dividends",
    changes: [
      "Analysts: sell-side consensus rating, mean/high/low price targets with implied upside, and forward estimates (the Bloomberg ANR / EE / ERN view).",
      "Ownership: institutional and insider holdings, public float and short interest, sourced from SEC filings for US names (the HDS view).",
      "Dividends: yield, rate, payout ratio, five-year average and ex-date (the DVD view).",
      "Coverage is honest: figures thin outside large-cap US names show clear \"unavailable\" states rather than blanks.",
    ],
  },
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
