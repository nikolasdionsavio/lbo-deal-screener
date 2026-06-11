"""Canonical financial data model (spec §4) and financials API response (spec §12).

All monetary values are USD floats in absolute units (not millions). None when
unavailable.
"""

from pydantic import BaseModel, Field


class FiscalYearFinancials(BaseModel):
    fiscal_year: int
    period_end: str | None = None  # ISO date, e.g. "2025-09-27"

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
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    total_equity: float | None = None
    shares_outstanding: float | None = None

    derived_fields: list[str] = Field(default_factory=list)


class FinancialsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/financials (spec §12)."""

    ticker: str
    years: list[FiscalYearFinancials]
    data_source: str
    fetched_at: str
    warnings: list[str] = Field(default_factory=list)
