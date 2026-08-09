"""Build and query the US screening index (app.db.models.ScreenIndexRow).

Two halves:

* ``rebuild_index`` pulls the SEC frames, keeps listed filers, and upserts one
  row per CIK. Sector enrichment is separate and incremental because it costs
  one request per company, so it only ever runs for CIKs that lack a sector.
* ``query_screen`` applies the screen filters. Rows whose EBITDA is unknown are
  excluded from EBITDA filters by SQL NULL semantics rather than being coerced
  to zero, which is the behaviour the whole feature depends on being right.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import ScreenIndexRow, utcnow
from app.screening.frames import Coverage, ScreenRow, SecFramesClient, latest_rows_by_cik

# Newest first: a filer missing from the newest period keeps its prior year.
DEFAULT_PERIODS = ("CY2025", "CY2024")

# SEC asks for no more than 10 requests/second.
_SEC_REQUEST_INTERVAL = 0.12

SORTABLE = {
    "revenue": ScreenIndexRow.revenue,
    "ebitda": ScreenIndexRow.ebitda,
    "ebitda_margin": ScreenIndexRow.ebitda_margin,
    "entity_name": ScreenIndexRow.entity_name,
    "ticker": ScreenIndexRow.ticker,
}


@dataclass
class RebuildResult:
    fetched: int
    listed: int
    written: int
    periods: list[str]


def rebuild_index(
    db: Session,
    client: SecFramesClient,
    *,
    periods: tuple[str, ...] = DEFAULT_PERIODS,
    listed_only: bool = True,
) -> RebuildResult:
    """Fetch the frames and upsert one row per filer. Idempotent.

    Sector is deliberately NOT fetched here (see ``enrich_missing_sectors``);
    an existing row keeps the sector it already has across refreshes.
    """
    period_rows = [client.fetch_period_rows(period) for period in periods]
    rows = latest_rows_by_cik(period_rows)
    fetched = len(rows)

    ticker_map = client.fetch_ticker_map()
    if listed_only:
        rows = [row for row in rows if row.cik in ticker_map]

    existing = {
        row.cik: row for row in db.execute(select(ScreenIndexRow)).scalars().all()
    }
    written = 0
    for row in rows:
        _upsert(db, existing.get(row.cik), row, ticker_map.get(row.cik))
        written += 1
    db.commit()
    return RebuildResult(
        fetched=fetched, listed=len(rows), written=written, periods=list(periods)
    )


def _upsert(
    db: Session,
    record: ScreenIndexRow | None,
    row: ScreenRow,
    ticker: str | None,
) -> None:
    if record is None:
        record = ScreenIndexRow(cik=row.cik, entity_name=row.entity_name)
        db.add(record)
    record.entity_name = row.entity_name or record.entity_name
    record.ticker = ticker or record.ticker
    record.period = row.period
    record.period_end = row.period_end
    record.accession = row.accession
    record.revenue = row.revenue
    record.revenue_tag = str(row.revenue_tag)
    record.operating_income = row.operating_income
    record.depreciation_amortization = row.depreciation_amortization
    record.ebitda = row.ebitda
    record.ebitda_margin = row.ebitda_margin
    record.coverage = str(row.coverage)
    record.quality_flag = str(row.quality_flag) if row.quality_flag else None
    record.refreshed_at = utcnow()


def enrich_missing_sectors(
    db: Session, client: SecFramesClient, *, limit: int | None = None
) -> int:
    """Fill SIC sector/exchange for rows that lack it, one request per company.

    Incremental by design: sector does not change, so a company is fetched once
    and later refreshes skip it. Interrupting this is safe, since every company
    is committed as it is fetched and the next run picks up the remainder.
    """
    stmt = select(ScreenIndexRow).where(ScreenIndexRow.sic.is_(None))
    if limit is not None:
        stmt = stmt.limit(limit)
    pending = db.execute(stmt).scalars().all()

    enriched = 0
    for record in pending:
        submission = client.fetch_submission(record.cik)
        time.sleep(_SEC_REQUEST_INTERVAL)
        if not isinstance(submission, dict):
            continue
        sic = submission.get("sic")
        record.sic = str(sic).strip() if sic else None
        description = submission.get("sicDescription")
        record.sic_description = str(description).strip() if description else None
        exchanges = submission.get("exchanges")
        if isinstance(exchanges, list) and exchanges:
            record.exchange = str(exchanges[0])
        if not record.ticker:
            tickers = submission.get("tickers")
            if isinstance(tickers, list) and tickers:
                record.ticker = str(tickers[0]).strip().upper()
        enriched += 1
        db.commit()
    return enriched


def query_screen(
    db: Session,
    *,
    revenue_min: float | None = None,
    revenue_max: float | None = None,
    ebitda_min: float | None = None,
    ebitda_positive: bool = False,
    margin_min: float | None = None,
    sector: str | None = None,
    q: str | None = None,
    exclude_flagged: bool = False,
    sort: str = "revenue",
    direction: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ScreenIndexRow], int]:
    """Apply the screen filters. Returns (page of rows, total matching count).

    Any EBITDA or margin filter implicitly drops rows where EBITDA is unknown,
    because SQL comparisons against NULL are never true. That is intended: a
    company that does not disclose D&A must not appear in a positive-EBITDA
    screen on the strength of a guess.
    """
    stmt = select(ScreenIndexRow)
    if revenue_min is not None:
        stmt = stmt.where(ScreenIndexRow.revenue >= revenue_min)
    if revenue_max is not None:
        stmt = stmt.where(ScreenIndexRow.revenue <= revenue_max)
    if ebitda_positive:
        stmt = stmt.where(ScreenIndexRow.ebitda > 0)
    if ebitda_min is not None:
        stmt = stmt.where(ScreenIndexRow.ebitda >= ebitda_min)
    if margin_min is not None:
        stmt = stmt.where(ScreenIndexRow.ebitda_margin >= margin_min)
    if exclude_flagged:
        stmt = stmt.where(ScreenIndexRow.quality_flag.is_(None))
    if sector:
        stmt = stmt.where(ScreenIndexRow.sic_description.ilike(f"%{sector.strip()}%"))
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ScreenIndexRow.entity_name.ilike(needle),
                ScreenIndexRow.ticker.ilike(needle),
            )
        )

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    column = SORTABLE.get(sort, ScreenIndexRow.revenue)
    # NULLs sort last in either direction, so companies missing the sort figure
    # never head the table.
    order = column.desc().nullslast() if direction == "desc" else column.asc().nullslast()
    stmt = stmt.order_by(order, ScreenIndexRow.cik).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), int(total)


def coverage_summary(db: Session) -> dict[str, Any]:
    """Row counts by coverage level, for the honest note shown above the table."""
    counts = dict(
        db.execute(
            select(ScreenIndexRow.coverage, func.count()).group_by(
                ScreenIndexRow.coverage
            )
        ).all()
    )
    total = sum(counts.values())
    refreshed = db.execute(select(func.max(ScreenIndexRow.refreshed_at))).scalar_one_or_none()
    flagged = db.execute(
        select(func.count()).select_from(ScreenIndexRow).where(
            ScreenIndexRow.quality_flag.is_not(None)
        )
    ).scalar_one()
    return {
        "total": total,
        "with_ebitda": int(counts.get(str(Coverage.FULL), 0)),
        "ebit_only": int(counts.get(str(Coverage.EBIT_ONLY), 0)),
        "revenue_only": int(counts.get(str(Coverage.REVENUE_ONLY), 0)),
        "flagged": int(flagged),
        "refreshed_at": refreshed.isoformat() if refreshed else None,
    }
