"""Company-level schemas: search, info, market data, bundle, profile (spec §4, §5, §12)."""

from pydantic import BaseModel, Field

from app.schemas.financials import FiscalYearFinancials


class SearchResult(BaseModel):
    ticker: str
    name: str
    exchange: str | None = None
    source: str


class CompanyInfo(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    exchange: str | None = None
    description: str | None = None
    cik: str | None = None


class MarketData(BaseModel):
    share_price: float | None = None
    market_cap: float | None = None
    shares_outstanding: float | None = None
    as_of: str | None = None  # ISO date
    source: str


class CompanyDataBundle(BaseModel):
    info: CompanyInfo
    market: MarketData | None = None
    financials: list[FiscalYearFinancials] = Field(default_factory=list)
    data_source: str
    fetched_at: str  # ISO datetime
    warnings: list[str] = Field(default_factory=list)


class CompanyProfile(BaseModel):
    """Response for GET /api/companies/{ticker}/profile (spec §12)."""

    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    exchange: str | None = None
    description: str | None = None
    share_price: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    shares_outstanding: float | None = None
    latest_fiscal_year: int | None = None
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    free_cash_flow: float | None = None
    cash: float | None = None
    total_debt: float | None = None
    net_debt: float | None = None
    data_source: str
    data_as_of: str | None = None
    warnings: list[str] = Field(default_factory=list)
