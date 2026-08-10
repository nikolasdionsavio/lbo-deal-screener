// TypeScript interfaces for the Investment Intelligence API.
// Mirrors docs/BUILD_SPEC.md sections 4-12. Field names match the API exactly.

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

export type Rating = "Attractive" | "Watchlist" | "Pass";

export type TracedUnit =
  | "percent"
  | "ratio"
  | "multiple"
  | "currency"
  | "per_share"
  | "days";

export interface TracedInput {
  field: string;
  value: number | null;
  period: string;
}

export interface TracedValue {
  key: string;
  label: string;
  value: number | null;
  unit: TracedUnit;
  period: string;
  formula: string;
  inputs: TracedInput[];
  warnings: string[];
}

export interface SeriesPoint {
  fiscal_year: number;
  value: number | null;
}

// ---------------------------------------------------------------------------
// Health and search (section 12)
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  provider: string;
}

export interface SearchResult {
  ticker: string;
  name: string;
  exchange: string | null;
  source: string;
}

// ---------------------------------------------------------------------------
// Canonical financial data model (section 4)
// ---------------------------------------------------------------------------

export interface FiscalYearFinancials {
  fiscal_year: number;
  period_end: string | null;
  /** Set for an interim (10-Q) period when no annual report exists yet. */
  period_label?: string | null;
  revenue: number | null;
  cost_of_revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  depreciation_amortization: number | null;
  ebitda: number | null;
  interest_expense: number | null;
  tax_expense: number | null;
  net_income: number | null;
  operating_cash_flow: number | null;
  capex: number | null;
  free_cash_flow: number | null;
  cash_and_equivalents: number | null;
  total_debt: number | null;
  current_assets: number | null;
  current_liabilities: number | null;
  total_equity: number | null;
  shares_outstanding: number | null;
  // Section 19.1 additions — optional so older cached payloads remain valid.
  dividends_paid?: number | null;
  share_buybacks?: number | null;
  receivables?: number | null;
  inventory?: number | null;
  accounts_payable?: number | null;
  // Section 19.8 additions (additive, None default on the backend).
  research_development?: number | null;
  selling_general_admin?: number | null;
  pretax_income?: number | null;
  /** Per-share figure in the reporting currency (not currency-scaled). */
  eps_basic?: number | null;
  /** Per-share figure in the reporting currency (not currency-scaled). */
  eps_diluted?: number | null;
  /** Weighted-average diluted share count (a count, not a monetary value). */
  shares_diluted?: number | null;
  stock_based_compensation?: number | null;
  total_assets?: number | null;
  total_liabilities?: number | null;
  goodwill?: number | null;
  intangible_assets?: number | null;
  ppe_net?: number | null;
  long_term_debt?: number | null;
  retained_earnings?: number | null;
  investing_cash_flow?: number | null;
  financing_cash_flow?: number | null;
  derived_fields: string[];
}

export interface CompanyInfo {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: string | null;
  description: string | null;
  cik: string | null;
}

export interface MarketData {
  share_price: number | null;
  market_cap: number | null;
  shares_outstanding: number | null;
  as_of: string;
  source: string;
  /** Quote currency after normalization (ISO code); absent/null means USD. */
  currency?: string | null;
}

export interface CompanyDataBundle {
  info: CompanyInfo;
  market: MarketData | null;
  financials: FiscalYearFinancials[];
  /** Financial reporting currency (ISO code); absent/null means USD. */
  currency?: string | null;
  data_source: string;
  fetched_at: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Company endpoints (section 12)
// ---------------------------------------------------------------------------

export interface CompanyProfile {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: string | null;
  description: string | null;
  share_price: number | null;
  market_cap: number | null;
  enterprise_value: number | null;
  shares_outstanding: number | null;
  latest_fiscal_year: number | null;
  revenue: number | null;
  ebitda: number | null;
  net_income: number | null;
  free_cash_flow: number | null;
  cash: number | null;
  total_debt: number | null;
  net_debt: number | null;
  /** Financial reporting currency (ISO code); absent/null means USD. */
  currency?: string | null;
  data_source: string;
  data_as_of: string | null;
  warnings: string[];
}

export interface FinancialsResponse {
  ticker: string;
  years: FiscalYearFinancials[];
  data_source: string;
  fetched_at: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Financial statements (section 19.7)
// ---------------------------------------------------------------------------

// Section 19.8 fields are optional so payloads from older backends (which
// omit them) remain valid; the table hides rows that are null everywhere.
export interface IncomeStatementLines {
  revenue: number | null;
  cost_of_revenue: number | null;
  gross_profit: number | null;
  research_development?: number | null;
  selling_general_admin?: number | null;
  operating_income: number | null;
  depreciation_amortization: number | null;
  ebitda: number | null;
  interest_expense: number | null;
  pretax_income?: number | null;
  tax_expense: number | null;
  net_income: number | null;
  /** Per-share figure in the reporting currency (not currency-scaled). */
  eps_basic?: number | null;
  /** Per-share figure in the reporting currency (not currency-scaled). */
  eps_diluted?: number | null;
  /** Weighted-average diluted share count (a count, not a monetary value). */
  shares_diluted?: number | null;
}

export interface BalanceSheetLines {
  cash_and_equivalents: number | null;
  receivables: number | null;
  inventory: number | null;
  current_assets: number | null;
  ppe_net?: number | null;
  goodwill?: number | null;
  intangible_assets?: number | null;
  total_assets?: number | null;
  accounts_payable: number | null;
  current_liabilities: number | null;
  long_term_debt?: number | null;
  total_debt: number | null;
  total_liabilities?: number | null;
  retained_earnings?: number | null;
  total_equity: number | null;
}

export interface CashFlowLines {
  stock_based_compensation?: number | null;
  operating_cash_flow: number | null;
  capex: number | null;
  investing_cash_flow?: number | null;
  dividends_paid: number | null;
  share_buybacks: number | null;
  financing_cash_flow?: number | null;
  free_cash_flow: number | null;
}

export interface StatementYear {
  fiscal_year: number;
  period_end: string | null;
  /** Set for an interim (10-Q) period when no annual report exists yet. */
  period_label?: string | null;
  /** Canonical field names whose values were derived rather than filed. */
  derived_fields: string[];
  income_statement: IncomeStatementLines;
  balance_sheet: BalanceSheetLines;
  cash_flow: CashFlowLines;
}

export interface StatementsResponse {
  ticker: string;
  /** Financial reporting currency (ISO code); null means USD. */
  currency: string | null;
  data_source: string;
  fetched_at: string;
  /** All available fiscal years, descending (newest first). */
  years: StatementYear[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// KPIs (section 6)
// ---------------------------------------------------------------------------

export interface KpiResponse {
  ticker: string;
  as_of: string;
  data_source: string;
  kpis: TracedValue[];
  series: Record<string, SeriesPoint[]>;
  /** PE diagnostics (section 19.1) — optional so older payloads remain valid. */
  diagnostics?: TracedValue[];
}

// ---------------------------------------------------------------------------
// Peer comparables (section 19.2)
// ---------------------------------------------------------------------------

export interface PeerRow {
  ticker: string;
  name: string;
  market_cap: number | null;
  enterprise_value: number | null;
  ev_ebitda: number | null;
  ev_revenue: number | null;
  pe: number | null;
  ebitda_margin: number | null;
  revenue_growth_yoy: number | null;
  currency: string | null;
  warnings: string[];
}

export interface PeerStats {
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
}

export interface PeersResponse {
  ticker: string;
  as_of: string;
  peer_source: string;
  target: PeerRow;
  peers: PeerRow[];
  /** Quartile stats keyed by metric: ev_ebitda, ev_revenue, pe, ebitda_margin. */
  stats: Record<string, PeerStats>;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Filings intelligence (section 19.3)
// ---------------------------------------------------------------------------

export interface Filing {
  form: string;
  filed: string;
  report_date: string | null;
  accession: string;
  primary_document: string;
  url: string;
}

export interface FilingsResponse {
  ticker: string;
  cik: string | null;
  filings: Filing[];
  source: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// News (section 19.6)
// ---------------------------------------------------------------------------

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  /** ISO timestamp. */
  published_at: string;
  summary: string | null;
}

export interface NewsResponse {
  ticker: string;
  /** Newest first; the backend caps at the requested limit (≤60, default 30). */
  items: NewsItem[];
  provider: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Valuation (section 7)
// ---------------------------------------------------------------------------

export interface ValuationRequest {
  low?: number;
  base?: number;
  high?: number;
}

export interface ValuationAssumptions {
  low: number;
  base: number;
  high: number;
}

export interface ValuationCase {
  case: string;
  multiple: number;
  implied_ev: number | null;
  implied_equity: number | null;
  implied_share_price: number | null;
  premium_vs_current: number | null;
}

export interface ValuationResponse {
  ticker: string;
  as_of: string;
  multiples: TracedValue[];
  assumptions: ValuationAssumptions;
  range: ValuationCase[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// LBO model (section 8)
// ---------------------------------------------------------------------------

export interface LboAssumptions {
  // "ebitda" prices entry/exit on EV/EBITDA; "revenue" prices entry on
  // EV/Revenue for a company whose latest EBITDA is non-positive (exit still
  // prices on EV/EBITDA once the projected margin turns positive).
  valuation_basis: "ebitda" | "revenue";
  entry_multiple: number;
  debt_multiple: number;
  // Opening debt as a fraction of entry EV (loan-to-value); used on the
  // revenue basis instead of the debt multiple.
  entry_leverage_pct: number;
  revenue_growth: number[];
  ebitda_margin: number[];
  capex_pct_revenue: number;
  nwc_pct_revenue: number;
  tax_rate: number;
  interest_rate: number;
  mandatory_repayment_pct: number;
  exit_multiple: number;
  transaction_fee_pct: number;
  holding_period: number;
}

export interface LboDefaultsResponse {
  assumptions: LboAssumptions;
  basis: Record<string, string>;
}

export interface LboEntry {
  entry_ebitda: number | null;
  entry_revenue: number | null;
  entry_ev: number | null;
  opening_debt: number | null;
  transaction_fees: number | null;
  total_uses: number | null;
  sponsor_equity: number | null;
  equity_pct: number | null;
  opening_net_leverage: number | null;
}

export interface LboYear {
  year: number;
  revenue: number;
  ebitda: number;
  capex: number;
  delta_nwc: number;
  interest: number;
  taxes: number;
  fcf: number;
  debt_repaid: number;
  ending_debt: number;
  ending_cash: number;
}

export interface LboExit {
  exit_ebitda: number | null;
  exit_ev: number | null;
  ending_debt: number | null;
  ending_cash: number | null;
  exit_equity: number | null;
  mom: number | null;
  irr: number | null;
}

export interface SensitivityGrid {
  row_label: string;
  col_label: string;
  rows: number[];
  cols: number[];
  values: (number | null)[][];
}

export interface LboSensitivities {
  irr_exit_vs_growth: SensitivityGrid;
  irr_entry_vs_exit: SensitivityGrid;
  mom_exit_vs_margin: SensitivityGrid;
}

export interface LboScenario {
  key: "downside" | "base" | "strategic";
  label: string;
  note: string;
  exit_multiple: number;
  irr: number | null;
  mom: number | null;
  exit_equity: number | null;
}

export interface CovenantLimits {
  max_net_debt_to_ebitda: number;
  min_interest_coverage: number;
  min_fcf_dscr: number;
}

export interface CovenantYear {
  year: number;
  net_debt_to_ebitda: number | null;
  interest_coverage: number | null;
  fcf_dscr: number | null;
  breached: boolean;
}

export interface LboCovenants {
  limits: CovenantLimits;
  years: CovenantYear[];
  any_breach: boolean;
  min_ebitda_cushion_pct: number | null;
}

export interface LboResponse {
  ticker: string;
  entry: LboEntry;
  years: LboYear[];
  exit: LboExit;
  scenarios: LboScenario[];
  covenants: LboCovenants | null;
  sensitivities: LboSensitivities;
  assumptions: LboAssumptions;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Deal score (section 9)
// ---------------------------------------------------------------------------

export interface ScoreComponent {
  key: string;
  label: string;
  weight: number;
  effective_weight: number;
  score: number | null;
  weighted_points: number | null;
  reason: string;
  inputs: TracedValue[];
  warnings: string[];
}

export interface ScoreResponse {
  ticker: string;
  as_of: string;
  total: number;
  rating: Rating;
  components: ScoreComponent[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Investment memo (section 10)
// ---------------------------------------------------------------------------

export interface MemoRequest {
  lbo_assumptions: LboAssumptions | null;
}

export interface MemoSection {
  key: string;
  title: string;
  content: string;
}

export interface MemoResponse {
  ticker: string;
  generated_at: string;
  rating: Rating;
  sections: MemoSection[];
  data_gaps: string[];
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Auth (section 12)
// ---------------------------------------------------------------------------

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
}

// ---------------------------------------------------------------------------
// Saved deals (section 12)
// ---------------------------------------------------------------------------

export interface SavedDeal {
  id: number;
  ticker: string;
  company_name: string;
  score: number | null;
  rating: Rating | null;
  created_at: string;
  updated_at: string;
  lbo_assumptions: LboAssumptions | null;
  memo: MemoResponse | null;
}

export interface SaveDealRequest {
  ticker: string;
  lbo_assumptions: LboAssumptions | null;
}

export interface UpdateDealAssumptionsRequest {
  lbo_assumptions: LboAssumptions;
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export interface ApiErrorBody {
  detail: string;
}

// ---------------------------------------------------------------------------
// Risk assessment (company + sector, qualitative + quantitative)
// ---------------------------------------------------------------------------

export type RiskFlag = "low" | "medium" | "high" | "na";
export type RiskBand = "low" | "moderate" | "elevated" | "high" | "na";

export interface RiskMetric {
  key: string;
  label: string;
  value: number | null;
  formatted: string;
  flag: RiskFlag;
  interpretation: string;
  formula: string;
}

export interface DistressScore {
  name: string;
  score: number | null;
  formatted: string;
  zone: string;
  flag: RiskFlag;
  interpretation: string;
  formula: string;
}

export interface SectorComparison {
  metric: string;
  company_value: number | null;
  company_formatted: string;
  peer_median: number | null;
  peer_median_formatted: string;
  peer_count: number;
  flag: RiskFlag;
  note: string;
}

export interface RiskFactor {
  heading: string;
  category: string;
}

export interface RiskResponse {
  ticker: string;
  as_of: string;
  financial_band: RiskBand;
  financial_summary: string;
  distress: DistressScore[];
  financial_metrics: RiskMetric[];
  market_metrics: RiskMetric[];
  sector_comparisons: SectorComparison[];
  sector_note: string;
  risk_factors: RiskFactor[];
  risk_factor_categories: Record<string, number>;
  going_concern_flagged: boolean;
  risk_factors_source: string | null;
  risk_factors_period: string | null;
  warnings: string[];
  sources: string[];
}

// ---------------------------------------------------------------------------
// Market stats (Bloomberg-style analyst / ownership / dividend / key stats)
// ---------------------------------------------------------------------------

export interface AnalystView {
  rating: string | null;
  rating_score: number | null;
  analyst_count: number | null;
  target_mean: number | null;
  target_high: number | null;
  target_low: number | null;
  current_price: number | null;
  implied_upside: number | null;
  forward_pe: number | null;
  forward_eps: number | null;
  trailing_eps: number | null;
  earnings_growth: number | null;
  revenue_growth: number | null;
  next_earnings_date: string | null;
}

export interface OwnershipView {
  held_pct_institutions: number | null;
  held_pct_insiders: number | null;
  float_shares: number | null;
  shares_outstanding: number | null;
  shares_short: number | null;
  short_pct_of_float: number | null;
  short_pct_shares_out: number | null;
  short_ratio: number | null;
}

export interface DividendView {
  dividend_rate: number | null;
  dividend_yield: number | null;
  payout_ratio: number | null;
  five_year_avg_yield: number | null;
  ex_dividend_date: string | null;
  last_dividend_value: number | null;
}

export interface KeyStats {
  beta: number | null;
  trailing_pe: number | null;
  price_to_book: number | null;
  ev_to_ebitda: number | null;
  ev_to_revenue: number | null;
  profit_margin: number | null;
  return_on_equity: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  fifty_two_week_change: number | null;
  sp_fifty_two_week_change: number | null;
  fifty_day_average: number | null;
  two_hundred_day_average: number | null;
}

export interface MarketStats {
  ticker: string;
  currency: string | null;
  as_of: string;
  source: string;
  analysts: AnalystView;
  ownership: OwnershipView;
  dividends: DividendView;
  stats: KeyStats;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// US screening index (SEC frames). Cross-company financials, one row per filer.
// ---------------------------------------------------------------------------

/** How much of the income statement a filer tagged, and so what is screenable. */
export type ScreenCoverage = "full" | "ebit_only" | "revenue_only";

/** A filed figure that is right as filed but would mislead if read plainly. */
export type ScreenQualityFlag = "ebitda_exceeds_revenue";

export interface ScreenRow {
  cik: number;
  ticker: string | null;
  name: string;
  sector: string | null;
  sic: string | null;
  exchange: string | null;
  period: string;
  period_end: string | null;
  revenue: number;
  operating_income: number | null;
  depreciation_amortization: number | null;
  /** null whenever the filer did not disclose D&A. Never inferred from EBIT. */
  ebitda: number | null;
  ebitda_margin: number | null;
  coverage: ScreenCoverage;
  coverage_note: string;
  quality_flag: ScreenQualityFlag | null;
  quality_note: string | null;
  revenue_tag: string | null;
  filing_url: string | null;

  gross_profit?: number | null;
  gross_margin?: number | null;
  net_income?: number | null;
  net_margin?: number | null;
  operating_margin?: number | null;
  cash?: number | null;
  total_debt?: number | null;
  assets?: number | null;
  equity?: number | null;
  net_debt?: number | null;
  /** Net debt / EBITDA. Null unless EBITDA is known and positive. */
  leverage?: number | null;
}

export interface ScreenCoverageSummary {
  total: number;
  with_ebitda: number;
  ebit_only: number;
  revenue_only: number;
  flagged: number;
  refreshed_at: string | null;
}

export interface ScreenResponse {
  rows: ScreenRow[];
  total: number;
  limit: number;
  offset: number;
  coverage: ScreenCoverageSummary;
  source: string;
  note: string;
}

export interface ScreenFacets {
  exchanges: string[];
  periods: string[];
  sectors: ScreenSector[];
  coverage_levels: string[];
}

export interface ScreenSector {
  sic: string | null;
  name: string;
  count: number;
}

export interface ScreenQuery {
  // Range filters are generated from the filter spec as `${field}_min` /
  // `${field}_max`, so the shape is open rather than enumerated here.
  [key: string]: string | number | boolean | null | undefined;
}
