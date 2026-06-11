"""Deal score schemas (spec §9)."""

from pydantic import BaseModel, Field

from app.schemas.kpi import TracedValue

SCORE_DISCLAIMER = (
    "Screening score based on mechanical rules. Not an investment recommendation."
)


class ScoreComponent(BaseModel):
    key: str
    label: str
    weight: float
    effective_weight: float
    score: float | None = None  # None when all inputs missing (weight redistributed)
    weighted_points: float | None = None
    reason: str
    inputs: list[TracedValue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ScoreResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/score (spec §9, §12)."""

    ticker: str
    as_of: str
    total: float
    rating: str  # "Attractive" | "Watchlist" | "Pass"
    components: list[ScoreComponent]
    disclaimer: str = SCORE_DISCLAIMER
