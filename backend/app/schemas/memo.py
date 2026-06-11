"""Investment memo schemas (spec §10, §12)."""

from pydantic import BaseModel, Field

from app.schemas.lbo import LboAssumptions

MEMO_DISCLAIMER = (
    "Screening tool for educational and research purposes. Not investment advice."
)

MEMO_SECTION_KEYS = [
    "company_overview",
    "investment_thesis",
    "financial_highlights",
    "kpi_summary",
    "lbo_case_summary",
    "valuation_view",
    "key_risks",
    "data_gaps",
    "screening_view",
]


class MemoRequest(BaseModel):
    """POST /api/companies/{ticker}/memo body."""

    lbo_assumptions: LboAssumptions | None = None


class MemoSection(BaseModel):
    key: str
    title: str
    content: str  # markdown


class MemoResponse(BaseModel):
    ticker: str
    generated_at: str
    rating: str
    sections: list[MemoSection]
    data_gaps: list[str] = Field(default_factory=list)
    disclaimer: str = MEMO_DISCLAIMER
