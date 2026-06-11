"""Pydantic schemas — the binding shapes from docs/BUILD_SPEC.md."""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.company import (
    CompanyDataBundle,
    CompanyInfo,
    CompanyProfile,
    MarketData,
    SearchResult,
)
from app.schemas.deal import DealAssumptionsUpdateRequest, DealCreateRequest, SavedDeal
from app.schemas.financials import FinancialsResponse, FiscalYearFinancials
from app.schemas.kpi import KpiResponse, SeriesPoint, TracedInput, TracedValue
from app.schemas.lbo import (
    LboAssumptions,
    LboDefaultsResponse,
    LboEntry,
    LboExit,
    LboResponse,
    LboSensitivities,
    LboYear,
    SensitivityGrid,
)
from app.schemas.memo import MemoRequest, MemoResponse, MemoSection
from app.schemas.score import ScoreComponent, ScoreResponse
from app.schemas.valuation import (
    ValuationAssumptions,
    ValuationCase,
    ValuationRequest,
    ValuationResponse,
)

__all__ = [
    "CompanyDataBundle",
    "CompanyInfo",
    "CompanyProfile",
    "DealAssumptionsUpdateRequest",
    "DealCreateRequest",
    "FinancialsResponse",
    "FiscalYearFinancials",
    "KpiResponse",
    "LboAssumptions",
    "LboDefaultsResponse",
    "LboEntry",
    "LboExit",
    "LboResponse",
    "LboSensitivities",
    "LboYear",
    "LoginRequest",
    "MarketData",
    "MemoRequest",
    "MemoResponse",
    "MemoSection",
    "RegisterRequest",
    "SavedDeal",
    "ScoreComponent",
    "ScoreResponse",
    "SearchResult",
    "SensitivityGrid",
    "SeriesPoint",
    "TokenResponse",
    "TracedInput",
    "TracedValue",
    "UserResponse",
    "ValuationAssumptions",
    "ValuationCase",
    "ValuationRequest",
    "ValuationResponse",
]
