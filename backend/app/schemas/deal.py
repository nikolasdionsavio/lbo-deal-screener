"""Saved-deals schemas (spec §12)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.lbo import LboAssumptions
from app.schemas.memo import MemoResponse


class SavedDeal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    company_name: str
    score: float | None = None
    rating: str | None = None
    created_at: datetime
    updated_at: datetime
    lbo_assumptions: LboAssumptions | None = None
    memo: MemoResponse | None = None  # embedded from snapshot


class DealCreateRequest(BaseModel):
    """POST /api/deals body — server recomputes score+memo+lbo and snapshots."""

    ticker: str
    lbo_assumptions: LboAssumptions | None = None


class DealAssumptionsUpdateRequest(BaseModel):
    """PUT /api/deals/{id}/assumptions body."""

    lbo_assumptions: LboAssumptions
