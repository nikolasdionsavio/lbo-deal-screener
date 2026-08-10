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

    # Profitability
    gross_profit: float | None = None
    gross_margin: float | None = None
    net_income: float | None = None
    net_margin: float | None = None
    operating_margin: float | None = None

    # Balance sheet
    cash: float | None = None
    total_debt: float | None = None
    assets: float | None = None
    equity: float | None = None
    net_debt: float | None = None
    leverage: float | None = None


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
        # "" is the "checked, none on record" marker; surface it as absent.
        sic=record.sic or None,
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
        gross_profit=record.gross_profit,
        gross_margin=record.gross_margin,
        net_income=record.net_income,
        net_margin=record.net_margin,
        operating_margin=record.operating_margin,
        cash=record.cash,
        total_debt=record.total_debt,
        assets=record.assets,
        equity=record.equity,
        net_debt=record.net_debt,
        leverage=record.leverage,
    )


@router.get("", response_model=ScreenResponse)
def screen(
    # Size. Currency amounts are in full units, not millions.
    revenue_min: float | None = Query(None, description="Minimum revenue"),
    revenue_max: float | None = Query(None, description="Maximum revenue"),
    ebitda_min: float | None = Query(None),
    ebitda_max: float | None = Query(None),
    assets_min: float | None = Query(None),
    assets_max: float | None = Query(None),
    # Profitability. Margins are fractions, so 0.15 is 15 percent.
    margin_min: float | None = Query(None, description="Minimum EBITDA margin"),
    margin_max: float | None = Query(None),
    operating_margin_min: float | None = Query(None),
    operating_margin_max: float | None = Query(None),
    gross_margin_min: float | None = Query(None),
    gross_margin_max: float | None = Query(None),
    net_margin_min: float | None = Query(None),
    net_margin_max: float | None = Query(None),
    ebitda_positive: bool = Query(False, description="Keep only positive EBITDA"),
    profitable: bool = Query(False, description="Keep only positive net income"),
    # Balance sheet.
    cash_min: float | None = Query(None),
    cash_max: float | None = Query(None),
    net_debt_min: float | None = Query(None),
    net_debt_max: float | None = Query(None),
    leverage_min: float | None = Query(None, description="Min net debt / EBITDA"),
    leverage_max: float | None = Query(None, description="Max net debt / EBITDA"),
    # Classification.
    sector: str | None = Query(None, description="SIC description substring"),
    exchange: str | None = Query(None),
    period: str | None = Query(None, description="e.g. CY2025"),
    coverage: str | None = Query(None, description="full | ebit_only | revenue_only"),
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
    ranges: dict[str, tuple[float | None, float | None]] = {
        "revenue": (revenue_min, revenue_max),
        "ebitda": (ebitda_min, ebitda_max),
        "assets": (assets_min, assets_max),
        "ebitda_margin": (margin_min, margin_max),
        "operating_margin": (operating_margin_min, operating_margin_max),
        "gross_margin": (gross_margin_min, gross_margin_max),
        "net_margin": (net_margin_min, net_margin_max),
        "cash": (cash_min, cash_max),
        "net_debt": (net_debt_min, net_debt_max),
        "leverage": (leverage_min, leverage_max),
    }
    rows, total = query_screen(
        db,
        ranges=ranges,
        ebitda_positive=ebitda_positive,
        profitable=profitable,
        sector=sector,
        exchange=exchange,
        period=period,
        coverage=coverage,
        q=q,
        exclude_flagged=exclude_flagged,
        sort=sort,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    summary = coverage_summary(db)
    derived_filters = (
        ebitda_positive
        or profitable
        or any(
            bound is not None
            for field in ("ebitda", "ebitda_margin", "operating_margin",
                          "gross_margin", "net_margin", "cash", "net_debt", "leverage")
            for bound in ranges[field]
        )
    )
    filtered_on_ebitda = derived_filters
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


class FacetsOut(BaseModel):
    """Values that actually exist in the index, so the filter UI never offers
    an option that would return nothing."""

    exchanges: list[str]
    periods: list[str]
    sectors: list[SectorOut]
    coverage_levels: list[str]


@router.get("/facets", response_model=FacetsOut)
def facets(db: Session = Depends(get_db)) -> FacetsOut:
    exchanges = [
        row[0]
        for row in db.execute(
            select(ScreenIndexRow.exchange)
            .where(ScreenIndexRow.exchange.is_not(None))
            .group_by(ScreenIndexRow.exchange)
            .order_by(func.count().desc())
        ).all()
    ]
    periods = [
        row[0]
        for row in db.execute(
            select(ScreenIndexRow.period)
            .group_by(ScreenIndexRow.period)
            .order_by(ScreenIndexRow.period.desc())
        ).all()
    ]
    return FacetsOut(
        exchanges=exchanges,
        periods=periods,
        sectors=sectors(db),
        coverage_levels=["full", "ebit_only", "revenue_only"],
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
