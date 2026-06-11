"""Traceable KPI framework schemas (spec §6)."""

from typing import Literal

from pydantic import BaseModel, Field

Unit = Literal["percent", "ratio", "multiple", "currency", "per_share", "days"]


class TracedInput(BaseModel):
    field: str
    value: float | None = None
    period: str


class TracedValue(BaseModel):
    key: str  # e.g. "ebitda_margin"
    label: str  # e.g. "EBITDA Margin"
    value: float | None = None
    unit: Unit
    period: str  # "FY2025" or "FY2023→FY2025"
    formula: str  # human-readable, e.g. "EBITDA / Revenue"
    inputs: list[TracedInput] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SeriesPoint(BaseModel):
    fiscal_year: int
    value: float | None = None


class KpiResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/kpis (spec §6, §12)."""

    ticker: str
    as_of: str
    data_source: str
    kpis: list[TracedValue]
    diagnostics: list[TracedValue] = Field(default_factory=list)
    series: dict[str, list[SeriesPoint]] = Field(default_factory=dict)
