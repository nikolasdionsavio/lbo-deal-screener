"""Canonical financial data model (spec §4) and financials API response (spec §12).

All monetary values are USD floats in absolute units (not millions). None when
unavailable.
"""

from pydantic import BaseModel, Field


class FiscalYearFinancials(BaseModel):
    fiscal_year: int
    period_end: str | None = None  # ISO date, e.g. "2025-09-27"
    # Set only for an interim (10-Q) period on a company with no annual report
    # yet, e.g. "Interim · 6mo to 30 Jun 2026". None means a full fiscal year.
    period_label: str | None = None

    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    depreciation_amortization: float | None = None
    ebitda: float | None = None
    interest_expense: float | None = None
    tax_expense: float | None = None
    net_income: float | None = None
    operating_cash_flow: float | None = None
    capex: float | None = None  # stored positive
    free_cash_flow: float | None = None
    dividends_paid: float | None = None  # cash outflow, stored positive
    share_buybacks: float | None = None  # cash outflow, stored positive
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    receivables: float | None = None
    inventory: float | None = None
    accounts_payable: float | None = None
    total_equity: float | None = None
    shares_outstanding: float | None = None

    # Extended statement fields (spec §19.8) — additive, optional, None
    # default. KPIs/score/LBO/memo never read them; they surface on the
    # /statements endpoint (and pass through /financials untouched).
    research_development: float | None = None
    selling_general_admin: float | None = None
    pretax_income: float | None = None
    eps_basic: float | None = None  # per-share (reporting currency / share)
    eps_diluted: float | None = None  # per-share (reporting currency / share)
    shares_diluted: float | None = None  # weighted-average diluted share count
    stock_based_compensation: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    goodwill: float | None = None
    intangible_assets: float | None = None
    ppe_net: float | None = None
    long_term_debt: float | None = None
    retained_earnings: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None

    derived_fields: list[str] = Field(default_factory=list)


class FinancialsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/financials (spec §12)."""

    ticker: str
    years: list[FiscalYearFinancials]
    data_source: str
    fetched_at: str
    warnings: list[str] = Field(default_factory=list)
