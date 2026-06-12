"""Financial statements response (spec §19.7, extended §19.8).

GET /api/companies/{ticker}/statements regroups the canonical
FiscalYearFinancials fields into the three filing statements per year, years
in DESCENDING fiscal_year order (all available history — up to 15 years from
EDGAR, the mock provider's 5 otherwise). All monetary values stay floats in
absolute units of the bundle reporting currency; None when unavailable.
Field order within each statement follows filing order (§19.8).
"""

from pydantic import BaseModel, Field


class StatementIncome(BaseModel):
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    research_development: float | None = None
    selling_general_admin: float | None = None
    operating_income: float | None = None
    depreciation_amortization: float | None = None
    ebitda: float | None = None
    interest_expense: float | None = None
    pretax_income: float | None = None
    tax_expense: float | None = None
    net_income: float | None = None
    eps_basic: float | None = None  # per share, reporting currency
    eps_diluted: float | None = None  # per share, reporting currency
    shares_diluted: float | None = None  # weighted-average diluted count


class StatementBalance(BaseModel):
    cash_and_equivalents: float | None = None
    receivables: float | None = None
    inventory: float | None = None
    current_assets: float | None = None
    ppe_net: float | None = None
    goodwill: float | None = None
    intangible_assets: float | None = None
    total_assets: float | None = None
    accounts_payable: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    total_debt: float | None = None
    total_liabilities: float | None = None
    retained_earnings: float | None = None
    total_equity: float | None = None


class StatementCashFlow(BaseModel):
    stock_based_compensation: float | None = None  # operating add-back
    operating_cash_flow: float | None = None
    capex: float | None = None  # stored positive
    free_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    dividends_paid: float | None = None  # cash outflow, stored positive
    share_buybacks: float | None = None  # cash outflow, stored positive
    financing_cash_flow: float | None = None


class StatementYear(BaseModel):
    fiscal_year: int
    period_end: str | None = None
    derived_fields: list[str] = Field(default_factory=list)
    income_statement: StatementIncome
    balance_sheet: StatementBalance
    cash_flow: StatementCashFlow


class StatementsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/statements (spec §19.7)."""

    ticker: str
    currency: str | None = None
    data_source: str
    fetched_at: str
    years: list[StatementYear]  # DESCENDING fiscal_year
    warnings: list[str] = Field(default_factory=list)
