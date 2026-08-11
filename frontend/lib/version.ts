// Single source of truth for the platform version and the What's New changelog.
// Bump APP_VERSION and prepend a Release entry whenever a user-facing change
// ships. The sidebar shows APP_VERSION; /whats-new renders RELEASES.

export const APP_VERSION = "1.10.1";

export interface Release {
  version: string;
  /** Human-readable release date. */
  date: string;
  title: string;
  changes: string[];
}

// Newest first. Keep entries factual: only changes that actually shipped.
export const RELEASES: Release[] = [
  {
    version: "1.10.1",
    date: "11 August 2026",
    title: "Controls that look like controls",
    changes: [
      "An audit of the screen found that 165 of its 223 interactive elements had no resting appearance at all: they revealed themselves only when the pointer was already on them. Sort headers looked like column labels, clickable figures looked like plain numbers, and filter group headers gave no sign they opened. One element now remains without a resting cue, and that one is the wordmark, which is a link home by convention.",
      "Every sortable column shows its sort control at rest, and the arrow indicates the direction the column is currently sorted in rather than appearing only once you touch it.",
      "Figures that carry a source record are marked with a dotted underline, the long-standing convention for \"there is more behind this\". Clicking one still opens the filing it came from.",
      "Filter groups carry a bordered plus or minus, so it is clear which sections open and which are already open.",
      "The sidebar collapse control and the theme switch are drawn as buttons instead of as bare icons.",
      "Where the results table is wider than the space beside the filter rail, the cut edge now fades and clears as you scroll, so a half-visible column reads as more to come rather than as a broken layout.",
    ],
  },
  {
    version: "1.10.0",
    date: "10 August 2026",
    title: "Leverage, margins and a filter rail",
    changes: [
      "The screen now carries the balance sheet: net debt, cash, total assets, and net debt / EBITDA. Leverage is the ratio most screens are actually built around, and it is colour-banded by credit convention so conservative, moderate and aggressive read at a glance.",
      "Profitability filters for gross, operating, EBITDA and net margin, each with a minimum and a maximum rather than a floor only.",
      "Filters are grouped and collapsible, so a simple screen stays simple and a specific one is available without a wall of inputs. Closed groups show how many constraints they hold, and a row of chips above the results says exactly what is filtering, each removable on its own.",
      "Four named starting points: add-on targets, lower mid-market, conservatively levered, and net cash.",
      "Every screen is now a link. Filters live in the address bar, so a shortlist can be sent to someone else and it opens exactly as you left it.",
      "Balance-sheet figures are matched to each company's own year end rather than to 31 December, so filers like Apple and NVIDIA are read against the right quarter instead of being dropped or mismatched.",
      "Rules and small labels were too faint to read: table rules sat at 1.3:1 contrast and the smallest labels failed the WCAG AA floor. Both were corrected, and labels and figures gained weight, without making any row taller.",
    ],
  },
  {
    version: "1.9.0",
    date: "9 August 2026",
    title: "Deal screen",
    changes: [
      "A new Deal screen: filter every US-listed filer by revenue, EBITDA, EBITDA margin and sector, then open any result straight into its research workspace. Built for sourcing, when you do not yet have a company in mind.",
      "The index is built from the SEC's XBRL company-facts data, so every figure is the one the company filed. Each row states its own reporting period and links to the filing the revenue came from.",
      "EBITDA is calculated as operating income plus depreciation and amortisation. Roughly four in ten filers do not tag D&A separately, so their EBITDA is shown as not disclosed rather than estimated, and an EBITDA filter leaves them out instead of guessing.",
      "Companies whose EBITDA exceeds their revenue are flagged as filing artifacts, which usually means a one-off gain sits inside reported operating income. They are marked rather than hidden, and can be excluded with one toggle.",
      "Quarterly figures now count: a company that has filed only a 10-Q, such as a recent listing, shows its interim results instead of an empty page.",
    ],
  },
  {
    version: "1.8.0",
    date: "16 July 2026",
    title: "Research workspace",
    changes: [
      "Rebuilt the site around a research-workspace design: an author-led homepage, a live worked example on Apple, and a clearer path from search to memo.",
      "Newly listed companies now appear in search as soon as they file with the SEC, and a company with no annual report yet shows a plain explanation instead of a blank page.",
      "The SEC ticker index now refreshes on its own, so a fresh listing is no longer missed until the next deploy.",
      "A methodology page and this changelog, so the sources and formulas behind each figure sit in one place.",
    ],
  },
  {
    version: "1.7.0",
    date: "3 July 2026",
    title: "Risk assessment",
    changes: [
      "A new Risks page: a rating-agency-style read combining a financial risk profile, sector context, and the company's own disclosed risk factors.",
      "Quantitative: Altman Z''-distress score, Piotroski F-score, and red-amber-green credit metrics (leverage, coverage, liquidity, cash runway, earnings-quality accruals) with the formula shown on each.",
      "Qualitative: the company's actual risk factors pulled verbatim from its 10-K (Item 1A), keyword-categorised and linked to the SEC filing, never summarised.",
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
      "Powered by TradingView, kept clearly separate from, and complementary to, the app's primary-source fundamentals.",
    ],
  },
  {
    version: "1.4.0",
    date: "2 July 2026",
    title: "Deal-memo depth",
    changes: [
      "Sources & Uses table on the LBO, with transaction fees funded as a use and pro-forma opening leverage.",
      "Underwriting scenarios: the base case bracketed by a strategic-buyer upside and a downturn downside, so returns read as a range, not a point estimate.",
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
