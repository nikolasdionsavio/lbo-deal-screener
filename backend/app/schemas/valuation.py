"""Valuation schemas (spec §7, §12)."""

from pydantic import BaseModel, Field

from app.schemas.kpi import TracedValue


class ValuationRequest(BaseModel):
    """POST /api/companies/{ticker}/valuation body — all optional → defaults."""

    low: float | None = None
    base: float | None = None
    high: float | None = None


class ValuationAssumptions(BaseModel):
    """Resolved EV/EBITDA multiples actually used."""

    low: float
    base: float
    high: float


class ValuationCase(BaseModel):
    case: str  # "low" | "base" | "high"
    multiple: float
    implied_ev: float | None = None
    implied_equity: float | None = None
    implied_share_price: float | None = None
    premium_vs_current: float | None = None


class ValuationResponse(BaseModel):
    ticker: str
    as_of: str
    multiples: list[TracedValue]
    assumptions: ValuationAssumptions
    range: list[ValuationCase]
    warnings: list[str] = Field(default_factory=list)
