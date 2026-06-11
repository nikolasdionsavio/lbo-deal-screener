"""SEC filings intelligence schemas (spec §19.3)."""

from pydantic import BaseModel, Field

FILINGS_SOURCE = "SEC EDGAR"


class Filing(BaseModel):
    """One SEC filing from the EDGAR submissions feed."""

    form: str
    filed: str | None = None  # ISO date the filing was submitted
    report_date: str | None = None  # ISO period-of-report date
    accession: str | None = None
    primary_document: str | None = None
    url: str | None = None


class FilingsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/filings (spec §19.3)."""

    ticker: str
    cik: str | None = None
    filings: list[Filing] = Field(default_factory=list)
    source: str = FILINGS_SOURCE
    warnings: list[str] = Field(default_factory=list)
