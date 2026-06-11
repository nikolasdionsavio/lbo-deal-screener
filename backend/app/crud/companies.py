"""Company + financial_statements write-through cache primitives (spec §11).

The skip-cache-for-mock policy lives in the services layer; these are just the
storage primitives. Note: the §11 ``companies`` table has no market-data
columns, so a cache-reconstructed bundle has ``market=None`` plus a warning —
services should refresh market data when serving a cached bundle live.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, FinancialStatement
from app.schemas.company import CompanyDataBundle, CompanyInfo
from app.schemas.financials import FiscalYearFinancials

MARKET_NOT_CACHED_WARNING = (
    "Market data is not cached; fundamentals served from cache without a "
    "current quote."
)


def _parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO datetime (accepts trailing 'Z') into an aware UTC datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes (SQLite round-trip) as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_company_by_ticker(db: Session, ticker: str) -> Company | None:
    return db.scalar(select(Company).where(Company.ticker == ticker.upper()))


def upsert_company(db: Session, bundle: CompanyDataBundle) -> Company:
    """Write-through cache: upsert the company row and its per-FY statements."""
    ticker = bundle.info.ticker.upper()
    fetched_at = _parse_iso_datetime(bundle.fetched_at)

    company = get_company_by_ticker(db, ticker)
    if company is None:
        company = Company(ticker=ticker)
        db.add(company)

    company.name = bundle.info.name
    company.sector = bundle.info.sector
    company.industry = bundle.info.industry
    company.exchange = bundle.info.exchange
    company.cik = bundle.info.cik
    company.data_source = bundle.data_source
    company.fetched_at = fetched_at
    db.flush()

    existing = {row.fiscal_year: row for row in company.financial_statements}
    for fy in bundle.financials:
        payload = fy.model_dump()
        row = existing.get(fy.fiscal_year)
        if row is None:
            company.financial_statements.append(
                FinancialStatement(
                    fiscal_year=fy.fiscal_year,
                    payload=payload,
                    source=bundle.data_source,
                    fetched_at=fetched_at,
                )
            )
        else:
            row.payload = payload
            row.source = bundle.data_source
            row.fetched_at = fetched_at

    db.commit()
    db.refresh(company)
    return company


def get_cached(
    db: Session, ticker: str, max_age_hours: int = 24
) -> CompanyDataBundle | None:
    """Return the cached bundle if fetched within max_age_hours, else None."""
    company = get_company_by_ticker(db, ticker)
    if company is None or company.fetched_at is None:
        return None

    fetched_at = _as_utc(company.fetched_at)
    age = datetime.now(timezone.utc) - fetched_at
    if age > timedelta(hours=max_age_hours):
        return None

    financials = sorted(
        (
            FiscalYearFinancials.model_validate(row.payload)
            for row in company.financial_statements
        ),
        key=lambda fy: fy.fiscal_year,
    )
    return CompanyDataBundle(
        info=CompanyInfo(
            ticker=company.ticker,
            name=company.name or company.ticker,
            sector=company.sector,
            industry=company.industry,
            exchange=company.exchange,
            cik=company.cik,
        ),
        market=None,  # §11 companies table carries no market-data columns
        financials=financials,
        data_source=company.data_source or "cache",
        fetched_at=fetched_at.isoformat(),
        warnings=[MARKET_NOT_CACHED_WARNING],
    )
