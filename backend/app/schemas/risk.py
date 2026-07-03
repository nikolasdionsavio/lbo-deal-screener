"""Risk-assessment schemas (company + sector, qualitative + quantitative).

Structured like a credit-rating write-up: a FINANCIAL risk profile (computed
from the filed statements — distress score, leverage, coverage, liquidity,
earnings quality), a MARKET risk read (beta / 52-week), SECTOR context
(peer-relative), and the company's own DISCLOSED risk factors (verbatim 10-K
Item 1A headings, keyword-categorised — never LLM-summarised). Every figure is
traceable; anything that cannot be computed is surfaced honestly, not hidden.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Red / amber / green (plus n/a) for a metric measured against its threshold.
RiskFlag = Literal["low", "medium", "high", "na"]
# Overall banding for a risk profile.
RiskBand = Literal["low", "moderate", "elevated", "high", "na"]


class RiskMetric(BaseModel):
    key: str
    label: str
    value: float | None = None
    formatted: str  # display string, e.g. "3.2x", "0.8", "14 months"
    flag: RiskFlag
    interpretation: str  # one line, plain English
    formula: str  # how it is computed (traceability)


class DistressScore(BaseModel):
    name: str  # "Altman Z''-score" / "Piotroski F-score"
    score: float | None = None
    formatted: str
    zone: str  # "Safe" / "Grey" / "Distress" / "Strong" / "Weak" / "n/a"
    flag: RiskFlag
    interpretation: str
    formula: str


class SectorComparison(BaseModel):
    metric: str
    company_value: float | None = None
    company_formatted: str
    peer_median: float | None = None
    peer_median_formatted: str
    peer_count: int
    flag: RiskFlag
    note: str  # "More levered than the peer median", etc.


class RiskFactor(BaseModel):
    heading: str  # the company's own risk-factor caption (verbatim)
    category: str  # keyword-derived bucket


class RiskResponse(BaseModel):
    ticker: str
    as_of: str

    # Financial risk profile (computed from the statements).
    financial_band: RiskBand
    financial_summary: str
    distress: list[DistressScore] = Field(default_factory=list)  # Z'', F-score
    financial_metrics: list[RiskMetric] = Field(default_factory=list)
    market_metrics: list[RiskMetric] = Field(default_factory=list)

    # Sector context (peer-relative).
    sector_comparisons: list[SectorComparison] = Field(default_factory=list)
    sector_note: str = ""

    # Qualitative: the company's disclosed risk factors (10-K Item 1A).
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    risk_factor_categories: dict[str, int] = Field(default_factory=dict)
    going_concern_flagged: bool = False
    risk_factors_source: str | None = None  # EDGAR filing URL
    risk_factors_period: str | None = None  # e.g. "FY2024 10-K"

    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
