"""US screening routes: filter every listed US filer on filed annual figures.

Backed by the ScreenIndexRow table (built from the SEC frames API), so a screen
is one indexed query rather than thousands of per-company fetches.

Every row states its own reporting period and links to the filing its revenue
came from, and rows whose EBITDA is undisclosed say so instead of showing a
figure derived from an assumption.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ScreenIndexRow
from app.screening.index_service import coverage_summary, query_screen

router = APIRouter(prefix="/screen", tags=["screen"])

_COVERAGE_NOTE = {
    "full": "Revenue and EBITDA from the filing. EBITDA calculated as operating income plus D&A.",
    "ebit_only": "EBITDA not disclosed: this filer does not tag depreciation and amortisation separately.",
    "revenue_only": "Only revenue disclosed in machine-readable form for this period.",
}

_FLAG_NOTE = {
    "ebitda_exceeds_revenue": (
        "EBITDA exceeds revenue, which normally means a one-off gain sits inside "
        "reported operating income. Read this as a filing artifact, not an "
        "operating margin, and check the filing before using the figure."
    ),
}


class ScreenRowOut(BaseModel):
    cik: int
    ticker: str | None
    name: str
    sector: str | None
    sic: str | None
    exchange: str | None
    period: str
    period_end: str | None
    revenue: float
    operating_income: float | None
    depreciation_amortization: float | None
    # None whenever the filer did not disclose D&A. Never inferred from EBIT.
    ebitda: float | None
    ebitda_margin: float | None
    coverage: str
    coverage_note: str
    # Set when the figure is right as filed but would mislead if read plainly.
    quality_flag: str | None
    quality_note: str | None
    revenue_tag: str | None
    filing_url: str | None


class CoverageOut(BaseModel):
    total: int
    with_ebitda: int
    ebit_only: int
    revenue_only: int
    flagged: int
    refreshed_at: str | None


class ScreenResponse(BaseModel):
    rows: list[ScreenRowOut]
    total: int
    limit: int
    offset: int
    coverage: CoverageOut
    source: str
    note: str


class SectorOut(BaseModel):
    sic: str | None
    name: str
    count: int


def _filing_url(cik: int, accession: str | None) -> str | None:
    """Link to the filing index page the figure was taken from."""
    if not accession:
        return None
    plain = accession.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{plain}/{accession}-index.htm"
    )


def _to_out(record: ScreenIndexRow) -> ScreenRowOut:
    return ScreenRowOut(
        cik=record.cik,
        ticker=record.ticker,
        name=record.entity_name,
        sector=record.sic_description,
        sic=record.sic,
        exchange=record.exchange,
        period=record.period,
        period_end=record.period_end,
        revenue=record.revenue,
        operating_income=record.operating_income,
        depreciation_amortization=record.depreciation_amortization,
        ebitda=record.ebitda,
        ebitda_margin=record.ebitda_margin,
        coverage=record.coverage,
        coverage_note=_COVERAGE_NOTE.get(record.coverage, ""),
        quality_flag=record.quality_flag,
        quality_note=_FLAG_NOTE.get(record.quality_flag or ""),
        revenue_tag=record.revenue_tag,
        filing_url=_filing_url(record.cik, record.accession),
    )


@router.get("", response_model=ScreenResponse)
def screen(
    revenue_min: float | None = Query(None, description="Minimum revenue, in currency units"),
    revenue_max: float | None = Query(None, description="Maximum revenue, in currency units"),
    ebitda_min: float | None = Query(None),
    ebitda_positive: bool = Query(False, description="Keep only positive EBITDA"),
    margin_min: float | None = Query(None, description="Minimum EBITDA margin, as a fraction"),
    sector: str | None = Query(None, description="SIC description substring"),
    q: str | None = Query(None, description="Company name or ticker"),
    exclude_flagged: bool = Query(
        False, description="Drop rows whose EBITDA exceeds revenue (one-off gains)"
    ),
    sort: str = Query("revenue"),
    direction: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ScreenResponse:
    rows, total = query_screen(
        db,
        revenue_min=revenue_min,
        revenue_max=revenue_max,
        ebitda_min=ebitda_min,
        ebitda_positive=ebitda_positive,
        margin_min=margin_min,
        sector=sector,
        q=q,
        exclude_flagged=exclude_flagged,
        sort=sort,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    summary = coverage_summary(db)
    filtered_on_ebitda = ebitda_positive or ebitda_min is not None or margin_min is not None
    note = (
        "Filtering on EBITDA excludes companies that do not disclose depreciation "
        "and amortisation separately, because their EBITDA cannot be calculated "
        "from the filing."
        if filtered_on_ebitda
        else "Figures are as filed with the SEC for each company's most recent "
        "annual period. EBITDA is calculated as operating income plus D&A."
    )
    return ScreenResponse(
        rows=[_to_out(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
        coverage=CoverageOut(**summary),
        source="SEC EDGAR (XBRL company facts)",
        note=note,
    )


@router.get("/sectors", response_model=list[SectorOut])
def sectors(db: Session = Depends(get_db)) -> list[SectorOut]:
    """Sectors present in the index, most populated first, for the filter rail."""
    rows = db.execute(
        select(
            ScreenIndexRow.sic,
            ScreenIndexRow.sic_description,
            func.count().label("n"),
        )
        .where(ScreenIndexRow.sic_description.is_not(None))
        .group_by(ScreenIndexRow.sic, ScreenIndexRow.sic_description)
        .order_by(func.count().desc())
    ).all()
    return [
        SectorOut(sic=sic, name=description, count=int(count))
        for sic, description, count in rows
    ]
