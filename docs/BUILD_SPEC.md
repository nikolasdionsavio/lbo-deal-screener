# LBO Deal Screener — Build Specification (canonical)

This document is the single source of truth for the build. Every module, schema field,
formula, API route, and frontend route defined here is a binding contract. If code and
this spec disagree, the spec wins; if the spec is genuinely wrong, fix the spec and the
code together.

Project root: `/Users/nikolasdionsavio/Documents/Personal Projects/PE_Deal_Analyser`
(referred to as `ROOT` below — note the space in the path; always quote it in shell).

## 1. Product summary

"LBO Deal Screener" — a private equity style deal screening tool for public companies
(US, UK, and European listings as of 2026-06; US-only at MVP launch). A user enters a
ticker or company name and gets: company dashboard, KPI dashboard with traceable
calculations, valuation page, simplified 5-year LBO model with sensitivities,
transparent 0–100 deal screening score, auto-generated investment memo, and a
saved-deals watchlist (auth required for saving only).

Product constraints (binding):
- Public companies only. Live coverage: US + UK + EU via Yahoo Finance (unofficial,
  flagged per §5) with official SEC EDGAR fundamentals for US tickers when configured.
  Figures display in the company's reporting currency; mixed-currency multiples are
  suppressed, never silently converted (§4 currency contract).
- Never claim financial advice; never claim a valuation is definitive.
- Every page shows data source and data date. Every computed number is traceable
  (formula + inputs + period + warnings). No black-box outputs.
- The memo and score never invent facts. Missing data is stated as missing.
- Every page footer: "Screening tool for educational and research purposes. Not
  investment advice."

## 2. Locked design decisions

1. **No Celery/Redis in MVP.** Data fetches are synchronous (seconds) with a DB cache
   (24h TTL). Background jobs are a roadmap item. Reason: do-not-overbuild.
2. **PostgreSQL in Docker; SQLite fallback locally.** SQLAlchemy 2.x code identical for
   both; `DATABASE_URL` switches. Default local run uses SQLite so the app works with
   zero infra. Docker is NOT installed on this machine — Docker files are deliverables
   validated by inspection, not by building images.
3. **Memo generation is deterministic templates** (no LLM). Guarantees the
   never-invent-facts constraint.
4. **Analysis is public; auth (email+password, JWT) is required only for saving deals.**
5. **Data providers:** `MockProvider` (bundled sample JSON), `SecEdgarProvider`
   (fundamentals, no key, UA header required), `FmpProvider` (market data, key required),
   `YahooProvider`/`YahooCompositeProvider` (global live US+UK+EU via yfinance, no key,
   unofficial — added 2026-06), composed by a factory honoring
   `DATA_PROVIDER=auto|mock|live|yahoo` (auto prefers yahoo; see §5).
6. **Charts: Recharts. Frontend: Next.js 14 App Router + TypeScript + Tailwind CSS.**
   No react-query, no component library; small hand-rolled UI kit.
7. **Python:** venv at `ROOT/backend/.venv` created from `/opt/anaconda3/bin/python3`
   (3.13). System `python3` is 3.9 — do not use it. Always invoke tools as
   `"$ROOT/backend/.venv/bin/python" -m pytest` etc.
8. **Auth libs:** `bcrypt` directly (not passlib), `PyJWT` (not python-jose).
9. **ΔNWC convention:** change in net working capital is a % of the *change* in revenue:
   `delta_nwc_t = nwc_pct_revenue × (revenue_t − revenue_{t−1})`. UI label: "Change in
   NWC (% of revenue growth)".

## 3. Repository layout

```
ROOT/
  .env.example  .gitignore  docker-compose.yml  README.md
  docs/BUILD_SPEC.md
  backend/
    Dockerfile  requirements.txt  .venv/ (local only, gitignored)
    app/
      __init__.py
      main.py                  # FastAPI app factory, CORS, startup init_db, include api_router
      core/config.py           # pydantic-settings Settings (env vars per §13)
      schemas/                 # ALL Pydantic models (company.py, financials.py, kpi.py,
                               #   valuation.py, lbo.py, score.py, memo.py, deal.py, auth.py)
      providers/               # base.py (interface), mock.py, edgar.py, fmp.py, factory.py
      normalization/           # raw provider payloads -> canonical FiscalYearFinancials
      kpis/                    # KPI calculations (traceable)
      valuation/               # multiples + valuation range
      lbo/                     # LBO engine, IRR/MoM, sensitivities
      scoring/                 # deal score
      memo/                    # memo generation
      auth/                    # password hashing, JWT, current_user dependency
      db/                      # base.py (engine/session/Base/init_db), models.py (9 tables)
      crud/                    # persistence helpers (cache, saved deals, snapshots)
      services/                # composition layer used by routes (company_service, deal_service)
      api/                     # __init__.py exposes api_router; routes_*.py modules
    data/sample/               # AAPL.json MSFT.json HD.json KO.json DE.json TESTCO.json
    tests/                     # pytest; fixtures from data/sample/TESTCO.json
  frontend/
    Dockerfile  package.json  tsconfig.json  tailwind.config.ts  postcss.config.js  next.config.js
    app/                       # layout.tsx, page.tsx (landing), login/, register/, deals/,
                               #   company/[ticker]/{layout.tsx, dashboard|kpis|valuation|lbo|score|memo}/page.tsx
    components/                # Sidebar.tsx, ui/ kit, then per-page subdirs (dashboard/, lbo/, ...)
    lib/                       # api.ts (typed client), types.ts, format.ts, hooks.ts, auth.tsx
```

Module ownership is one-agent-per-area; shared files (`schemas/`, `lib/types.ts`,
`lib/api.ts`) are created by foundation agents and treated as read-only by later agents
unless the integration phase fixes a mismatch.

## 4. Canonical financial data model

`FiscalYearFinancials` (Pydantic, `schemas/financials.py`) — all monetary values in USD,
floats, absolute units (not millions). `None` when unavailable.

```
fiscal_year: int            # e.g. 2025
period_end: str | None      # ISO date "2025-09-27"
revenue, cost_of_revenue, gross_profit,
operating_income, depreciation_amortization, ebitda,
interest_expense, tax_expense, net_income,
operating_cash_flow, capex, free_cash_flow,
cash_and_equivalents, total_debt,
current_assets, current_liabilities,
total_equity: float | None
shares_outstanding: float | None
derived_fields: list[str]   # names of fields that were derived rather than reported
```

Derivations (in `normalization/`, applied uniformly to all providers):
- `gross_profit = revenue − cost_of_revenue` when missing and both inputs present.
- `ebitda = operating_income + depreciation_amortization` when missing. EBITDA is
  ALWAYS recorded as derived this way for EDGAR data; mock files may state it directly.
- `free_cash_flow = operating_cash_flow − capex` when missing (capex stored positive).
- Record each derived field name in `derived_fields`.

`MarketData` (schemas/company.py): `share_price, market_cap, shares_outstanding,
as_of (ISO date), source`. `CompanyInfo`: `ticker, name, sector, industry, exchange,
description, cik (optional)`.

`CompanyDataBundle` = `{info: CompanyInfo, market: MarketData | None,
financials: list[FiscalYearFinancials] (ascending fiscal_year, up to 5 years),
currency: str | None (financial reporting currency, ISO code, default None ≡ USD for
legacy/sample payloads), data_source: str, fetched_at: ISO datetime,
warnings: list[str]}`.

Headline aggregates (computed in services, shown on dashboard):
- `enterprise_value = market_cap + net_debt` where `net_debt = total_debt − cash` (latest FY).
- `market_cap`: from market provider; if absent but `share_price` and shares exist,
  derive; else `None` + warning "Market data unavailable".

### Currency contract (added for global coverage)

- `MarketData.currency: str | None` — quote currency AFTER normalization. Yahoo quotes
  LSE stocks in pence (`"GBp"`): normalize `share_price /= 100`, currency → `"GBP"`;
  `market_cap` is cross-checked against `share_price × shares_outstanding` and the
  computed value wins when they disagree by > 5% (warning recorded).
- `CompanyDataBundle.currency` / `CompanyProfile.currency` — the financial reporting
  currency (Yahoo `financialCurrency`); this is the display currency for all
  fundamentals-derived figures. Sample/mock data: `"USD"`.
- When (normalized) quote currency ≠ reporting currency: do NOT mix them. EV,
  EV-based multiples, P/E, FCF yield, and valuation premium-vs-current are `None`
  with the warning "Quote currency (X) differs from reporting currency (Y); mixed
  currency multiples suppressed (no FX conversion in MVP)". Fundamentals-only KPIs and
  the LBO (entirely in reporting currency, entry EV from multiple × EBITDA) still work.
- Frontend `fmtCurrency(value, currency?)`: `USD → $`, `GBP → £`, `EUR → €`; any other
  code prefixes the ISO code (`"SEK 1.2bn"`). Company pages read the code from
  `useCompany().profile.currency`. Backend memo/score formatters accept the same code.

## 5. Data providers

`providers/base.py`:

```python
class DataProvider(ABC):
    name: str
    def search(self, query: str) -> list[SearchResult]: ...        # ticker or name match
    def get_company(self, ticker: str) -> CompanyDataBundle: ...   # raises CompanyNotFoundError
```

`SearchResult = {ticker, name, exchange, source}`.

- **MockProvider**: loads `backend/data/sample/*.json` (schema mirrors
  `CompanyDataBundle`). Search = case-insensitive substring on ticker or name.
  TESTCO is excluded from search results (test fixture only) but loadable by ticker.
  All mock bundles have `data_source: "Sample data (illustrative figures)"`.
- **SecEdgarProvider**: ticker→CIK via `https://www.sec.gov/files/company_tickers.json`
  (cached in memory + on disk), fundamentals via
  `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json`. Requires
  `SEC_EDGAR_USER_AGENT` header. Use 10-K annual facts (`form == "10-K"`, pick the value
  whose `frame`/`fy`/`fp == "FY"` per fiscal year; dedupe by `end` date, prefer latest
  filed). us-gaap tag preference lists (first present wins):
  - revenue: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`,
    `SalesRevenueNet`
  - cost_of_revenue: `CostOfRevenue`, `CostOfGoodsAndServicesSold`, `CostOfGoodsSold`
  - operating_income: `OperatingIncomeLoss`
  - depreciation_amortization: `DepreciationDepletionAndAmortization`,
    `DepreciationAmortizationAndAccretionNet`, `DepreciationAndAmortization`;
    when no combined tag is filed (e.g. Microsoft), fall back to the per-year sum
    of `Depreciation` (required anchor) + `AmortizationOfIntangibleAssets` +
    `FinanceLeaseRightOfUseAssetAmortization`
  - net_income: `NetIncomeLoss`
  - interest_expense: `InterestExpense`, `InterestExpenseDebt`, `InterestIncomeExpenseNet`(abs)
  - tax_expense: `IncomeTaxExpenseBenefit`
  - operating_cash_flow: `NetCashProvidedByUsedInOperatingActivities`,
    `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations`
  - capex: `PaymentsToAcquirePropertyPlantAndEquipment`,
    `PaymentsToAcquireProductiveAssets` (store positive)
  - cash: `CashAndCashEquivalentsAtCarryingValue`,
    `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`
  - total_debt: `LongTermDebtNoncurrent` + current component, where the current
    component is `DebtCurrent` when present, else `LongTermDebtCurrent` +
    `ShortTermBorrowings` (avoids double-counting filers that report both);
    fallback `LongTermDebt` alone; if none present, `None` + warning
  - current_assets: `AssetsCurrent`; current_liabilities: `LiabilitiesCurrent`
  - total_equity: `StockholdersEquity`,
    `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
  - shares: dei `EntityCommonStockSharesOutstanding` (latest)
  Missing tags → field `None` + warning string `"<field> unavailable from SEC EDGAR"`.
  Sector/industry are NOT in companyfacts → take from FMP when available, else `None`.
- **FmpProvider** (market data + profile): `GET /api/v3/profile/{ticker}` and
  `/api/v3/quote/{ticker}` on `https://financialmodelingprep.com`, `apikey` param.
- **YahooProvider** (global live coverage: US + UK + EU, via the `yfinance` library —
  UNOFFICIAL Yahoo endpoints; chosen 2026-06 because no official API offers free
  US+UK+EU fundamentals; FMP/Finnhub/Alpha Vantage free tiers are US-only, Twelve
  Data/EODHD gate fundamentals behind paid plans):
  - search: `yfinance` Search/Lookup, equities only, top 8, exchange display name
    passed through; works for "tesco", "TSCO.L", "ASML", etc.
  - fundamentals: `Ticker.income_stmt`, `.balance_sheet`, `.cashflow` (annual, up to
    4-5 FYs) mapped to FiscalYearFinancials. Row-label preference lists (first present
    wins): revenue "Total Revenue"; cost_of_revenue "Cost Of Revenue";
    gross_profit "Gross Profit"; operating_income "Operating Income";
    d_and_a (cashflow) "Depreciation Amortization Depletion", "Depreciation And
    Amortization", "Depreciation"; interest_expense "Interest Expense";
    tax_expense "Tax Provision"; net_income "Net Income";
    operating_cash_flow "Operating Cash Flow", "Cash Flow From Continuing Operating
    Activities"; capex "Capital Expenditure" (abs); cash "Cash And Cash Equivalents",
    "Cash Cash Equivalents And Short Term Investments"; total_debt "Total Debt", else
    "Long Term Debt" + "Current Debt"; current_assets "Current Assets";
    current_liabilities "Current Liabilities"; total_equity "Stockholders Equity",
    "Common Stock Equity". Missing rows → None + warning. Fiscal year = column
    end-date year. Normalization (§4) applies after mapping.
  - market/profile: `Ticker.info` (sector, industry, longBusinessSummary, exchange,
    currency, financialCurrency, currentPrice/regularMarketPrice, marketCap,
    sharesOutstanding) with the GBp normalization and market-cap cross-check above.
  - data_source: `"Yahoo Finance (unofficial endpoints, via yfinance)"`. Every bundle
    carries the warning `"Data from unofficial Yahoo Finance endpoints; verify figures
    against filings before relying on them."`
  - EDGAR enrichment: when `SEC_EDGAR_USER_AGENT` is set and the ticker has no
    exchange suffix (US-style), fetch fundamentals from SecEdgarProvider instead and
    keep Yahoo for market/profile; `data_source: "SEC EDGAR + Yahoo Finance"`. On
    EDGAR failure, fall back to Yahoo fundamentals with a warning. Implemented as
    `YahooCompositeProvider` mirroring CompositeLiveProvider.
  - Errors: yfinance raising/empty frames → CompanyNotFoundError (unknown symbol) or
    ProviderError (rate limit / network) with readable messages; never tracebacks
    with URLs. No pytest test may hit the live network (monkeypatched fixtures only).
  - Cache-hit market refresh: providers may expose `refresh_market(ticker) ->
    MarketData | None`; company_service uses it on §11 cache hits (replaces the
    FMP-specific re-fetch).
- **factory.py** `get_provider(settings) -> DataProvider`:
  - `mock` → MockProvider.
  - `live` → CompositeLiveProvider (EDGAR fundamentals + FMP market/profile; FMP search
    endpoint `/api/v3/search?query=&exchange=NASDAQ,NYSE` if key present, else EDGAR
    ticker-file search). Raise `ProviderConfigError` if `SEC_EDGAR_USER_AGENT` missing.
  - `yahoo` → YahooCompositeProvider (global; no key required). Raise
    `ProviderConfigError` only if yfinance is not importable.
  - `auto` → yahoo when yfinance imports, else live if `SEC_EDGAR_USER_AGENT`
    present, else mock with the warning "Using bundled sample data; set
    SEC_EDGAR_USER_AGENT and FMP_API_KEY for live data." (auto is live-by-default
    as of 2026-06; DATA_PROVIDER=mock remains the offline/dev mode and the pytest
    default via dependency override.)
  All `httpx` calls: 15s timeout, raise-for-status mapped to `ProviderError` with a
  human-readable message. No scraping anywhere; official JSON endpoints only.

## 6. Traceable KPI framework

`TracedValue` (schemas/kpi.py) — used for KPIs and reused by valuation/score:

```
key: str            # "ebitda_margin"
label: str          # "EBITDA Margin"
value: float | None
unit: "percent" | "ratio" | "multiple" | "currency" | "per_share"
period: str         # "FY2025" or "FY2023→FY2025"
formula: str        # human-readable, e.g. "EBITDA / Revenue"
inputs: list[{field: str, value: float | None, period: str}]
warnings: list[str] # e.g. "EBITDA derived as Operating income + D&A"
```

KPI set (`kpis/calculations.py`, latest FY unless stated; `None` value + warning when
inputs missing — never raise):

| key | formula | unit |
|---|---|---|
| revenue_growth_yoy | rev_t / rev_{t−1} − 1 | percent |
| revenue_cagr_3y | (rev_t / rev_{t−3})^(1/3) − 1 (use available span if <3y, say so in period) | percent |
| gross_margin | gross_profit / revenue | percent |
| ebitda_margin | ebitda / revenue | percent |
| net_income_margin | net_income / revenue | percent |
| fcf_margin | fcf / revenue | percent |
| fcf_conversion | fcf / ebitda | percent |
| capex_pct_revenue | capex / revenue | percent |
| net_debt_to_ebitda | (total_debt − cash) / ebitda | multiple |
| debt_to_ebitda | total_debt / ebitda | multiple |
| interest_coverage | ebitda / interest_expense (None + warning if interest ≤ 0/missing) | multiple |
| roic | operating_income × (1 − effective_tax) / (total_debt + total_equity − cash); effective_tax = tax_expense / (net_income + tax_expense) clamped [0, 0.5], fallback 0.25 with warning | percent |
| current_ratio | current_assets / current_liabilities | ratio |
| nwc_pct_revenue | (current_assets − current_liabilities) / revenue | percent |

`KpiResponse = {ticker, as_of, data_source, kpis: list[TracedValue], series: {<metric>:
list[{fiscal_year, value}]}}`. Series provided (when data exists): revenue, ebitda,
free_cash_flow, total_debt, gross_margin, ebitda_margin, net_income_margin, fcf_margin,
net_debt_to_ebitda. Valuation-multiple time series are out of MVP scope (single price
point only) — frontend hides that chart when series absent.

## 7. Valuation

`valuation/model.py`:
- Current multiples (TracedValue list): ev_revenue, ev_ebitda, pe (market_cap /
  net_income), price_sales (market_cap / revenue), fcf_yield (fcf / market_cap),
  plus market_cap and enterprise_value as currency values.
- Valuation range from user-editable EV/EBITDA multiples `{low, base, high}`:
  for each case: `implied_ev = multiple × latest_ebitda`,
  `implied_equity = implied_ev − net_debt`,
  `implied_share_price = implied_equity / shares_outstanding` (None if shares missing),
  `premium_vs_current = implied_share_price / share_price − 1` (None if price missing).
- Defaults: `base = round(current EV/EBITDA × 2) / 2` (nearest 0.5x), `low = max(1.0,
  base − 2)`, `high = base + 2`. If EV/EBITDA unavailable, default base 8.0x + warning.
- Response: `{ticker, as_of, multiples: list[TracedValue], assumptions: {low, base, high},
  range: list[{case, multiple, implied_ev, implied_equity, implied_share_price,
  premium_vs_current}], warnings}`.

## 8. LBO model

`lbo/engine.py`. All rates as decimals (0.05 = 5%).

`LboAssumptions` (schemas/lbo.py):
```
entry_multiple: float          # EV / entry EBITDA
debt_multiple: float           # opening debt / entry EBITDA (validated < entry_multiple)
revenue_growth: list[float]    # length == holding_period
ebitda_margin: list[float]     # length == holding_period
capex_pct_revenue: float
nwc_pct_revenue: float         # ΔNWC = this × Δrevenue   (§2.9)
tax_rate: float
interest_rate: float           # cash interest on beginning-of-year debt
mandatory_repayment_pct: float # % of ORIGINAL opening debt repaid per year (before sweep)
exit_multiple: float
holding_period: int            # 1–7, default 5
```

Mechanics (entry base = latest FY: `entry_ebitda`, `entry_revenue`):
```
entry_ev       = entry_multiple × entry_ebitda
opening_debt   = debt_multiple × entry_ebitda
sponsor_equity = entry_ev − opening_debt          # equity_pct = sponsor_equity / entry_ev
For each year t = 1..N:
  revenue_t  = revenue_{t−1} × (1 + growth_t)
  ebitda_t   = margin_t × revenue_t
  d_and_a_t  = capex_t = capex_pct_revenue × revenue_t      # simplification: D&A = capex
  delta_nwc_t= nwc_pct_revenue × (revenue_t − revenue_{t−1})
  interest_t = interest_rate × debt_{t−1}                   # beginning-of-year balance
  ebt_t      = ebitda_t − d_and_a_t − interest_t
  taxes_t    = max(0, ebt_t) × tax_rate
  fcf_t      = ebitda_t − capex_t − delta_nwc_t − interest_t − taxes_t
  repay_t    = min(debt_{t−1}, mandatory_repayment_pct × opening_debt + max(0, fcf_t − mandatory_repayment_pct × opening_debt))
               # i.e. 100% cash sweep of positive FCF, floored at 0 debt;
               # if fcf_t < mandatory amount, repay max(0, fcf_t) (no new borrowing in MVP)
  cash_t     = cash_{t−1} + max(0, fcf_t − repay_t)         # excess builds cash after debt = 0
  debt_t     = debt_{t−1} − repay_t
Exit:
  exit_ebitda = ebitda_N ; exit_ev = exit_multiple × exit_ebitda
  exit_equity = exit_ev − debt_N + cash_N
  mom = exit_equity / sponsor_equity
  irr = irr([−sponsor_equity, 0, …, 0, exit_equity])        # equals mom^(1/N) − 1 here
```
Negative-FCF years simply repay nothing (debt stays; MVP does not model revolver draws —
add a per-year warning "Negative FCF in year t; no revolver modeled").

`lbo/irr.py`: general `irr(cashflows: list[float]) -> float | None` — Newton from 0.1
with bisection fallback on [−0.99, 10.0]; `None` if no sign change. `mom(cashflows)` for
the simple case. Unit-tested against the closed form.

Defaults (`lbo/defaults.py`, derived from company data, each with a `basis` note):
entry_multiple = current EV/EBITDA rounded to 0.5x (fallback 8.0); debt_multiple =
`min(6.0, round(entry_multiple/2 × 2)/2)` i.e. ~50% of entry, capped 6.0x; revenue_growth
= 3y CAGR clamped [0, 0.15], flat across years; ebitda_margin = latest margin, flat;
capex_pct_revenue = 3y average (fallback 0.04); nwc_pct_revenue = 0.02 unless history
supports otherwise (any cleverer derivation is out of scope); tax_rate = 0.25;
interest_rate = 0.08; mandatory_repayment_pct = 0.05; exit_multiple = entry_multiple;
holding_period = 5.

Sensitivities (5×5 grids, recompute full model per cell):
1. `irr_exit_vs_growth`: rows = exit_multiple {base−2 … base+2, step 1}; cols = uniform
   shift of every year's growth by {−4, −2, 0, +2, +4} pp.
2. `irr_entry_vs_exit`: rows = entry_multiple base±2 step 1 (re-derives EV/debt/equity;
   keep debt_multiple fixed, but clamp to entry_multiple − 0.5 minimum equity);
   cols = exit_multiple base±2 step 1.
3. `mom_exit_vs_margin`: rows = exit_multiple base±2; cols = uniform shift of every
   year's margin by {−4, −2, 0, +2, +4} pp (clamp margins to ≥ 1%).
Grid shape: `{row_label, col_label, rows: list[float], cols: list[float],
values: list[list[float | None]]}` (values[i][j] for rows[i] × cols[j]).

`LboResponse = {ticker, entry: {entry_ebitda, entry_revenue, entry_ev, opening_debt,
sponsor_equity, equity_pct}, years: list[{year, revenue, ebitda, capex, delta_nwc,
interest, taxes, fcf, debt_repaid, ending_debt, ending_cash}], exit: {exit_ebitda,
exit_ev, ending_debt, ending_cash, exit_equity, mom, irr}, sensitivities: {…three grids…},
assumptions: LboAssumptions (echo), warnings: list[str]}`.

## 9. Deal score

`scoring/model.py`. Helper `linear_score(value, worst, best)` → 0–100 clamped, works for
inverted ranges (worst > best means lower-is-better). Each component averages the scores
of its available inputs; if ALL inputs missing → component score `None`, its weight is
redistributed proportionally across available components, and a warning is added.

| component | weight | inputs (worst → best) |
|---|---|---|
| growth | 20% | revenue_cagr_3y: 0% → 15% |
| margins | 20% | ebitda_margin: 5% → 30%; gross_margin: 20% → 60% |
| cash_conversion | 20% | fcf_conversion: 20% → 80%; fcf_margin: 0% → 15% |
| leverage_capacity | 15% | net_debt_to_ebitda: 4.0x → 0.0x; interest_coverage: 1x → 8x |
| valuation | 15% | ev_ebitda: 16x → 6x; fcf_yield: 2% → 8% |
| balance_sheet_risk | 10% | current_ratio: 0.8 → 2.0; debt_to_ebitda: 5x → 1x |

`total = Σ weight_i × score_i` (with redistributed weights), rounded to 1 decimal.
Rating: ≥70 "Attractive", ≥50 "Watchlist", else "Pass".
Each component carries a `reason` string citing actual values, e.g.
"3-year revenue CAGR of 5.6% scores 37/100 on a 0–15% scale."
Response: `{ticker, as_of, total, rating, components: list[{key, label, weight,
effective_weight, score, weighted_points, reason, inputs: list[TracedValue-like],
warnings}], disclaimer: "Screening score based on mechanical rules. Not an investment
recommendation."}`.

## 10. Investment memo

`memo/generator.py` — deterministic templates filled ONLY from computed data
(profile, KPIs, valuation at default multiples, LBO at default assumptions or
caller-supplied assumptions, score). Sections (keys fixed):
`company_overview, investment_thesis, financial_highlights, kpi_summary,
lbo_case_summary, valuation_view, key_risks, data_gaps, screening_view`.

Rules:
- `investment_thesis`: bullets selected by rule (e.g. fcf_conversion > 0.6 → "Strong
  cash conversion supports deleveraging"; revenue_cagr_3y > 0.07 → growth bullet;
  ebitda_margin > 0.2 → margin bullet). If fewer than 2 bullets qualify, state
  "Limited affirmative thesis support from available data."
- `key_risks`: rule-selected (net_debt_to_ebitda > 3 → leverage risk; revenue_growth_yoy
  < 0 → declining revenue; fcf_margin < 0.05 → weak FCF; interest_coverage < 3 →
  coverage risk; data warnings → data quality risk). Always at least: "Public-market
  valuation may already reflect the qualities identified above."
- `data_gaps`: aggregates every warning from the bundle, KPIs, valuation, LBO. If none:
  "No material data gaps identified in the fields used."
- `screening_view`: mirrors the deal score rating with one-line justification citing the
  score. Numbers formatted consistently ($X.Xbn / X.X% / X.Xx).
- Every section content is markdown text. Response: `{ticker, generated_at, rating,
  sections: list[{key, title, content}], data_gaps: list[str], disclaimer}`.

## 11. Database (SQLAlchemy 2.x, models in `db/models.py`)

JSON payload columns use `sqlalchemy.JSON` (works on SQLite and Postgres).
`init_db()` runs `Base.metadata.create_all` at startup (Alembic is roadmap).

- `users(id PK, email unique not null, password_hash, created_at)`
- `companies(id PK, ticker unique, name, sector, industry, exchange, cik, currency, data_source, fetched_at)`
  — `currency` is the bundle's financial reporting currency (§4), persisted so
  cache-hit bundles keep the currency contract (nullable; None ≡ USD)
- `financial_statements(id PK, company_id FK, fiscal_year, payload JSON, source, fetched_at; unique(company_id, fiscal_year))`
- `kpi_snapshots(id PK, company_id FK, as_of, payload JSON, created_at)`
- `lbo_assumptions(id PK, saved_deal_id FK, payload JSON, updated_at)`
- `lbo_outputs(id PK, lbo_assumptions_id FK, payload JSON, created_at)`
- `deal_scores(id PK, company_id FK, total, rating, payload JSON, created_at)`
- `investment_memos(id PK, company_id FK, rating, payload JSON, created_at)`
- `saved_deals(id PK, user_id FK, company_id FK, ticker, company_name, score, rating, memo_id FK nullable, created_at, updated_at; unique(user_id, ticker))`

Caching: `companies` + `financial_statements` are a write-through cache of provider
fetches; reuse when `fetched_at` < 24h old (skip cache when provider is mock — mock is
instant). Snapshot rows (`kpi_snapshots`, `deal_scores`, `investment_memos`,
`lbo_assumptions`, `lbo_outputs`) are written when a deal is saved/updated, not on every
view.

## 12. API contract (FastAPI, all under `/api`)

Errors: JSON `{detail: str}` with 404 (unknown ticker), 422 (validation), 502 (provider
failure, human-readable message), 401 (auth), 409 (duplicate save/register).

| method, path | request | response |
|---|---|---|
| GET `/api/health` | — | `{status: "ok", provider: str}` |
| GET `/api/search?q=` | — | `list[SearchResult]` |
| GET `/api/companies/{ticker}/profile` | — | CompanyProfile: `{ticker, name, sector, industry, exchange, description, share_price, market_cap, enterprise_value, shares_outstanding, latest_fiscal_year, revenue, ebitda, net_income, free_cash_flow, cash, total_debt, net_debt, data_source, data_as_of, warnings}` |
| GET `/api/companies/{ticker}/financials` | — | `{ticker, years: list[FiscalYearFinancials], data_source, fetched_at, warnings}` |
| GET `/api/companies/{ticker}/kpis` | — | KpiResponse (§6) |
| POST `/api/companies/{ticker}/valuation` | `{low, base, high} (all optional → defaults)` | Valuation response (§7) |
| GET `/api/companies/{ticker}/lbo/defaults` | — | `{assumptions: LboAssumptions, basis: dict[str, str]}` |
| POST `/api/companies/{ticker}/lbo` | `LboAssumptions` | LboResponse (§8) |
| GET `/api/companies/{ticker}/score` | — | Deal score response (§9) |
| POST `/api/companies/{ticker}/memo` | `{lbo_assumptions: LboAssumptions \| null}` | Memo response (§10) |
| POST `/api/auth/register` | `{email, password}` (JSON; password ≥ 8 chars) | `{access_token, token_type: "bearer"}` |
| POST `/api/auth/login` | `{email, password}` (JSON) | `{access_token, token_type}` |
| GET `/api/auth/me` | Bearer | `{id, email}` |
| GET `/api/deals` | Bearer | `list[SavedDeal]` |
| POST `/api/deals` | Bearer, `{ticker, lbo_assumptions \| null}` — server recomputes score+memo+lbo and snapshots them | SavedDeal |
| PUT `/api/deals/{id}/assumptions` | Bearer, `{lbo_assumptions}` — recomputes + stores lbo_outputs | SavedDeal |
| DELETE `/api/deals/{id}` | Bearer | 204 |

`SavedDeal = {id, ticker, company_name, score, rating, created_at, updated_at,
lbo_assumptions: LboAssumptions | null, memo: Memo response | null}` (memo embedded from
snapshot). JWT: HS256, `sub` = user id, 7-day expiry, secret `JWT_SECRET`.

PDF export: NOT in MVP (roadmap).

## 13. Configuration (env vars — see `.env.example`)

`DATABASE_URL` (default `sqlite:///./lbo_screener.db`), `JWT_SECRET`,
`DATA_PROVIDER` (auto|mock|live, default auto), `SEC_EDGAR_USER_AGENT`, `FMP_API_KEY`,
`CORS_ORIGINS` (comma-separated, default `http://localhost:3000`),
frontend: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## 14. Frontend

Routes (App Router):
- `/` landing: product explanation ("A private equity style deal screening tool for
  public companies."), search bar with debounced `/api/search` dropdown, sample-company
  quick links, disclaimer footer.
- `/login`, `/register`: minimal forms; on success store JWT in localStorage and
  redirect; auth state via `lib/auth.tsx` React context (AuthProvider in root layout).
- `/company/[ticker]` → redirects to `/company/[ticker]/dashboard`.
- `/company/[ticker]/{dashboard,kpis,valuation,lbo,score,memo}`.
- `/deals` saved deals (prompts login if no token).

Layout: fixed left sidebar (component `Sidebar.tsx`) with sections — Search (link to
`/`), then company-scoped items Dashboard / KPIs / Valuation / LBO Model / Deal Score /
Memo (built from current ticker; rendered disabled with a hint when no ticker in route
and no `lastTicker` in localStorage), then Saved Deals, then login/logout. Top of content
area: company header (name, ticker, data source + data date badge) on company pages.

UI kit (`components/ui/`): `Card`, `StatCard` (label, value, sub), `DataTable`,
`SectionHeader`, `LoadingState` (skeleton), `ErrorState` (message + retry),
`WarningBadge`/`WarningList`, `AssumptionField` (numeric input with unit suffix, %
handling), `RatingBadge`, `Disclaimer`. Charts via Recharts wrappers in
`components/charts/`: `TimeSeriesChart` (line/bar), `MarginChart`, `SensitivityTable`
(HTML table with green→red cell shading; NOT a chart lib heatmap).

Design language: institutional and quiet. Tailwind config tokens — background
`#f6f7f9`, surface white, ink `#0f172a`, brand navy `#1e3a5f`, accent emerald
`#0d9488` only for positive deltas / primary buttons, red `#b91c1c` for negatives,
amber for warnings. Font: Inter (next/font). Dense numeric tables, right-aligned
figures, tabular-nums. No gradients, no glassmorphism, no emoji. Every page renders
`<Disclaimer/>` at the bottom and shows data source + date where data appears.

Number formatting (`lib/format.ts`): currency auto-scaled ($1.23tn / $456.7bn / $89.1m),
percent `12.3%`, multiples `8.5x`, signed deltas. `null` renders as `—` with a tooltip
"Not available" where practical.

Data fetching: plain `fetch` via `lib/api.ts` typed client (one function per endpoint,
`ApiError` carrying status + detail). `lib/hooks.ts`: `useApi<T>(fn, deps)` returning
`{data, error, loading, retry}`. All pages are client components (`"use client"`).
LBO page: assumption form (per-year growth/margin editable as 5 fields each), debounced
recompute on change via POST, outputs table + sensitivity tables. Valuation page:
editable low/base/high multiples, recompute on change.

## 15. Testing (pytest, `backend/tests/`)

Fixture: `data/sample/TESTCO.json` — synthetic "Testco Industrials Inc" (ticker TESTCO),
hand-checkable round numbers. FY2025 (binding, USD millions expressed as absolute
numbers — i.e. revenue 1_000_000_000.0 etc. Multiply all values below by 1e6):
revenue 1000, cost_of_revenue 600, gross_profit 400, operating_income 200, D&A 50,
ebitda 250, interest_expense 20, tax_expense 45, net_income 135, operating_cash_flow 230,
capex 50, fcf 180, cash 100, total_debt 400, current_assets 300, current_liabilities 150,
total_equity 500, shares_outstanding 100e6, share_price 13.50 → market_cap 1350,
EV 1650. Revenue series FY2021–2025: 800, 850, 900, 950, 1000. EBITDA series:
180, 200, 215, 235, 250. (Earlier-year remaining fields: any internally consistent
values.)

Required test coverage (exact expected values, tolerance 1e-6 relative unless noted):
- EV = 1650m; net debt = 300m; FCF = 180m (and derivation path OCF − capex).
- KPIs: ebitda_margin 0.25, fcf_conversion 0.72, net_debt_to_ebitda 1.2,
  interest_coverage 12.5, revenue_growth_yoy 1000/950−1, revenue_cagr_3y
  (1000/850)^(1/3)−1, current_ratio 2.0, capex_pct_revenue 0.05.
- Missing-data behavior: KPI returns value None + warning, never raises.
- IRR: irr([−1000, 0, 0, 0, 0, 2000]) == 2^(1/5)−1; mom == 2.0; irr returns None for
  all-negative flows.
- LBO year-1 hand-check with assumptions: entry_multiple 8.0, debt_multiple 4.0,
  growth 5% flat, margin 25% flat, capex 5%, nwc 2%, tax 25%, interest 8%, mandatory 5%,
  exit 8.0, N=5 → entry_ev 2000m, opening_debt 1000m, sponsor_equity 1000m;
  year 1: revenue 1050m, ebitda 262.5m, capex 52.5m, delta_nwc 1.0m, interest 80m,
  taxes 32.5m, fcf 96.5m, ending_debt 903.5m. Full 5-year run cross-checked in-test by
  an independent loop implementation; assert mom and irr consistency
  (irr == mom^(1/5) − 1 within 1e-9 when only entry/exit equity flows).
- Deal score: weights sum to 1.0; TESTCO total in [0, 100]; component reasons contain
  formatted input values; all-inputs-missing component triggers reweighting and total
  still in [0, 100]; rating boundaries (70/50) tested directly via synthetic components.
- Valuation range: base 6.5x on TESTCO (EV/EBITDA 6.6 → rounds to 6.5), implied equity
  = multiple × 250m − 300m, implied share price = equity / 100m.
- Memo: sections all present; data_gaps lists injected warnings; no section contains
  the literal string "None" or "nan".
- Normalization: EDGAR-shaped raw fixture (small synthetic companyfacts JSON) maps tags
  correctly, derives EBITDA/FCF/gross profit, records derived_fields.
- Auth: register/login roundtrip, wrong password 401, duplicate email 409 (TestClient +
  in-memory SQLite). Saved deals CRUD with auth (TestClient).

Run command: `cd "$ROOT/backend" && .venv/bin/python -m pytest -q` — must be fully green.

## 16. Dockerfiles

`backend/Dockerfile`: `python:3.13-slim`, copy requirements, pip install, copy app+data,
`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
`frontend/Dockerfile`: multi-stage `node:20-alpine` (deps → build → `next start -p 3000`,
`NEXT_PUBLIC_API_URL` as build arg + runtime env).

## 17. README requirements (written in final phase)

Quick start without Docker (venv + SQLite + two terminals), Docker compose path
(flagged as not yet built on this machine), env var table, architecture overview,
provider setup (EDGAR UA, FMP key), test instructions, screenshots optional, short
roadmap: PDF memo export, Celery/Redis background refresh, Alembic migrations, more
providers (Polygon/Alpha Vantage), peer comps, historical multiples, deployment guides
(Render/Railway), revolver + tranche structure in LBO, quarterly data.

## 18. Conventions

- Python: type hints everywhere, Pydantic v2 (`model_dump()`, `ConfigDict`), no pandas
  in request path except normalization/sensitivities where it genuinely helps (NumPy fine
  in lbo/irr). Comments only where financial logic is non-obvious.
- Money floats are absolute USD. Percentages are decimals in APIs (0.25), formatted only
  in the frontend.
- TS: strict mode, no `any` in `lib/` (pages may use narrow casts if unavoidable).
- Frontend copy: serious, no hype, no exclamation marks, correct PE terminology.
- Never claim advice; disclaimers per §1.

## 19. Expansion (2026-06): PE depth, peer comps, filings, provider plugins

All changes additive; old payloads/caches must stay valid (new fields default None/[]).

### 19.1 Deeper fundamentals (owner: agent A)

`FiscalYearFinancials` new optional fields: `dividends_paid, share_buybacks,
receivables, inventory, accounts_payable` (USD absolute, None when unavailable).
EDGAR tags (per-period merge machinery applies): dividends_paid:
`PaymentsOfDividends`, `PaymentsOfDividendsCommonStock`; share_buybacks:
`PaymentsForRepurchaseOfCommonStock`; receivables: `AccountsReceivableNetCurrent`,
`ReceivablesNetCurrent`; inventory: `InventoryNet`; accounts_payable:
`AccountsPayableCurrent`, `AccountsPayableAndAccruedLiabilitiesCurrent`.
Yahoo row map additions: "Cash Dividends Paid"/"Common Stock Dividend Paid",
"Repurchase Of Capital Stock" (abs), "Accounts Receivable", "Inventory",
"Accounts Payable".

`KpiResponse` gains `diagnostics: list[TracedValue] = []` ("PE diagnostics", latest FY,
None+warning on missing inputs; TracedValue.unit literal gains `"days"`):
dso = receivables/revenue×365; dsi = inventory/cost_of_revenue×365;
dpo = accounts_payable/cost_of_revenue×365; cash_conversion_cycle = dso+dsi−dpo;
capital_return_pct_fcf = (dividends_paid+share_buybacks)/fcf;
buyback_pct_fcf = share_buybacks/fcf; incremental_ebitda_margin = ΔEBITDA/Δrevenue (yoy).
Series additions: dividends_paid, share_buybacks.
TESTCO FY2025 bindings (×1e6): dividends_paid 30, share_buybacks 50, receivables 120,
inventory 80, accounts_payable 90 → dso 43.8, dsi 48.6667, dpo 54.75, ccc 37.7167,
capital_return_pct_fcf 0.4444, buyback_pct_fcf 0.2778, incremental_ebitda_margin 0.30.
All six sample files gain internally consistent values for the new fields.

### 19.2 Peer comparables (owner: agent B)

Peer discovery is a duck-typed provider method `get_peers(ticker) ->
list[{symbol, name, price, mktCap}]`: FmpProvider via GET `/stable/stock-peers?symbol=`
(VERIFIED working on the free plan; company-screener is NOT); MockProvider returns the
other sample companies; providers without the method → peers unavailable warning.

GET `/api/companies/{ticker}/peers` → `{ticker, as_of, peer_source, target: PeerRow,
peers: list[PeerRow] (≤6), stats: {metric: {min, q1, median, q3, max}} for ev_ebitda,
ev_revenue, pe, ebitda_margin, warnings}`. PeerRow = `{ticker, name, market_cap,
enterprise_value, ev_ebitda, ev_revenue, pe, ebitda_margin, revenue_growth_yoy,
currency, warnings}`. Implementation (`services/peers_service.py`): market cap/price
from the peers payload itself (no extra quote calls); fundamentals per peer through the
existing cached `company_service.get_bundle` with per-peer try/except → skip + warning;
quartile stats computed over valued peers only (exclude target), None metric values
skipped. First uncached load is slow — acceptable, surfaced in the frontend copy.

### 19.3 Filings intelligence (owner: agent B)

`providers/edgar_filings.py`: submissions via
`https://data.sec.gov/submissions/CIK{cik:010d}.json` (UA header, 429-retry pattern),
filter forms {10-K, 10-Q, 8-K, DEF 14A}, latest 10, document URL
`https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession without dashes}/{primaryDocument}`.
GET `/api/companies/{ticker}/filings` → `{ticker, cik, filings: [{form, filed,
report_date, accession, primary_document, url}], source: "SEC EDGAR", warnings}`.
Ticker→CIK via the bundled EDGAR ticker map; unresolvable (mock tickers) → 200 with
empty list + warning "Filings are available in live mode for US filers only."
Memo: `generate_memo` gains optional `filings` param — company_overview appends
"Latest 10-K filed YYYY-MM-DD" with a markdown link; key_risks appends a pointer to
Item 1A of that 10-K with the link. Services pass filings best-effort (failures never
break the memo). Full-text section extraction stays on the roadmap.

### 19.4 Market-data provider plugins (owner: agent C)

New key-gated quote adapters, each exposing `get_quote(ticker) -> MarketData | None`
(15s timeout, ProviderError mapping, keys never in error messages):
`providers/polygon.py` (prev-close `/v2/aggs/ticker/{t}/prev` + shares from
`/v3/reference/tickers/{t}`), `providers/alphavantage.py` (GLOBAL_QUOTE + OVERVIEW for
shares/market cap), `providers/tiingo.py` (`/tiingo/daily/{t}` meta + `/prices`).
Settings: `polygon_api_key`, `alphavantage_api_key`, `tiingo_api_key` (+ .env.example,
README provider table). `CompositeLiveProvider` market data becomes an ordered chain of
configured adapters [FMP, Polygon, Alpha Vantage, Tiingo]; first non-None quote wins and
sets MarketData.source; `refresh_market` uses the same chain.

### 19.5 Frontend (owner: agent D)

KPIs page: "PE diagnostics" section (same traced table treatment) + capital-returns
stacked bar chart (dividends + buybacks; `components/charts/CapitalReturnsChart.tsx`)
when series exist. New page `/company/[ticker]/peers` ("Peer Comps" sidebar item between
Valuation and LBO Model): peers DataTable with the target row highlighted, median stat
cards, EV/EBITDA bar chart with target in accent color (`components/peers/`), loading
copy noting the first load can take ~30s. Dashboard: "Recent SEC filings" card (form
badge, date, external link). MemoRenderer gains `[text](url)` link support
(target=_blank, rel=noopener). lib/types.ts + lib/api.ts additions (getPeers, getFilings).

### 19.6 News, description, charts pack (added at user request)

- **News** (backend owner: agent B; page: agent E): GET `/api/companies/{ticker}/news` →
  `{ticker, items: list[{title, url, source, published_at (ISO), summary: str | None}]
  (≤12, newest first), provider: str, warnings}`. `services/news_service.py` chain:
  (1) FMP GET `/stable/news/stock?symbols=&limit=` when fmp_api_key set — the free plan
  returns a "Restricted Endpoint" body: detect it (and 402/403) → warning + fall
  through, never error; (2) yfinance `Ticker(t).news` (keyless; items arrive under a
  `content` dict: title, `canonicalUrl.url` or `clickThroughUrl.url`, `provider.
  displayName`, `pubDate`, `summary`), provider label "Yahoo Finance (unofficial
  endpoints, via yfinance)"; (3) mock/unavailable → 200, empty items, warning
  "News is available in live mode only." New page `/company/[ticker]/news` + sidebar
  item "News" after Memo: headline list (title links target=_blank rel=noopener,
  source, relative+absolute date, summary line clamped), provider + warnings shown,
  Disclaimer.
- **Dashboard description** (agent D): `profile.description` rendered under the Company
  section as prose in a Card; collapsed to ~4 lines with a "Show more"/"Show less"
  toggle when long; hidden when null.
- **Charts pack** (agent E, all client-computed from existing endpoints, Recharts,
  currency-aware, hidden when inputs missing):
  - Valuation `components/charts/FootballFieldChart.tsx`: horizontal bars for low/base/
    high implied enterprise value with a reference line at current EV.
  - LBO `components/lbo/DebtPaydownChart.tsx`: years 0..N, ending debt bars + ending
    cash line (year 0 = opening debt / zero cash).
  - LBO `components/lbo/ValueCreationBridge.tsx`: waterfall entry equity → EBITDA
    growth effect `M_in×(E_out−E_in)` → multiple effect `(M_out−M_in)×E_out` →
    deleveraging `(D_in−D_out)+C_out` → exit equity (exact decomposition; floating
    bars via a transparent stacked base; formula stated in the sub line).
  - Dashboard `components/charts/FinancialTrendChart.tsx`: revenue bars + EBITDA-margin
    line (ComposedChart) from GET /financials, placed between Financials and Price
    chart sections.
