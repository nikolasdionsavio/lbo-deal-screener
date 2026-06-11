"""CRUD tests (spec §15): users, company cache freshness, saved-deal lifecycle.

Uses an in-memory SQLite engine with StaticPool directly (no conftest client).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models as models
from app.crud.companies import get_cached, upsert_company
from app.crud.deals import (
    DuplicateDealError,
    create_saved_deal,
    delete_deal,
    list_for_user,
    update_assumptions,
)
from app.crud.users import DuplicateEmailError, create_user, get_by_email
from app.db.base import Base
from app.schemas.company import CompanyDataBundle

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"

ASSUMPTIONS_PAYLOAD: dict[str, Any] = {
    "entry_multiple": 8.0,
    "debt_multiple": 4.0,
    "revenue_growth": [0.05, 0.05, 0.05, 0.05, 0.05],
    "ebitda_margin": [0.25, 0.25, 0.25, 0.25, 0.25],
    "capex_pct_revenue": 0.05,
    "nwc_pct_revenue": 0.02,
    "tax_rate": 0.25,
    "interest_rate": 0.08,
    "mandatory_repayment_pct": 0.05,
    "exit_multiple": 8.0,
    "holding_period": 5,
}

MEMO_PAYLOAD: dict[str, Any] = {
    "ticker": "TESTCO",
    "generated_at": "2026-06-11T00:00:00+00:00",
    "rating": "Watchlist",
    "sections": [
        {
            "key": "company_overview",
            "title": "Company Overview",
            "content": "Testco Industrials Inc is a synthetic test company.",
        },
        {
            "key": "screening_view",
            "title": "Screening View",
            "content": "Watchlist with a screening score of 61.5/100.",
        },
    ],
    "data_gaps": [],
    "disclaimer": (
        "Screening tool for educational and research purposes. "
        "Not investment advice."
    ),
}

SCORE_PAYLOAD: dict[str, Any] = {
    "ticker": "TESTCO",
    "as_of": "2026-06-11",
    "total": 61.5,
    "rating": "Watchlist",
    "components": [],
    "disclaimer": (
        "Screening score based on mechanical rules. "
        "Not an investment recommendation."
    ),
}

KPI_PAYLOAD: dict[str, Any] = {
    "ticker": "TESTCO",
    "as_of": "2026-06-11",
    "data_source": "Sample data (illustrative figures)",
    "kpis": [],
    "series": {},
}

LBO_OUTPUT_PAYLOAD: dict[str, Any] = {"exit": {"mom": 2.0, "irr": 0.1487}}


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def testco() -> CompanyDataBundle:
    raw = json.loads((SAMPLE_DIR / "TESTCO.json").read_text())
    raw["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return CompanyDataBundle.model_validate(raw)


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def test_create_user_and_get_by_email(db: Session) -> None:
    user = create_user(db, "Investor@Example.com", "hashed-pw")
    assert user.id is not None
    assert user.email == "investor@example.com"  # normalized lowercase
    assert user.created_at is not None

    found = get_by_email(db, "investor@example.com")
    assert found is not None and found.id == user.id
    assert get_by_email(db, "nobody@example.com") is None


def test_duplicate_email_raises_typed_error(db: Session) -> None:
    create_user(db, "dup@example.com", "hash1")
    with pytest.raises(DuplicateEmailError):
        create_user(db, "dup@example.com", "hash2")
    # Session must remain usable after the rollback.
    assert _count(db, models.User) == 1


# ---------------------------------------------------------------------------
# Company cache
# ---------------------------------------------------------------------------


def test_company_cache_upsert_and_fresh_retrieval(db: Session, testco: CompanyDataBundle) -> None:
    company = upsert_company(db, testco)
    assert company.ticker == "TESTCO"
    assert _count(db, models.FinancialStatement) == 5

    cached = get_cached(db, "testco")  # case-insensitive lookup
    assert cached is not None
    assert cached.info.ticker == "TESTCO"
    assert cached.info.name == "Testco Industrials Inc"
    assert cached.info.sector == "Industrials"
    assert cached.data_source == "Sample data (illustrative figures)"
    assert len(cached.financials) == 5
    # Ascending fiscal_year order and payload integrity (spec §15 round numbers).
    years = [fy.fiscal_year for fy in cached.financials]
    assert years == [2021, 2022, 2023, 2024, 2025]
    latest = cached.financials[-1]
    assert latest.revenue == 1_000_000_000.0
    assert latest.ebitda == 250_000_000.0
    assert latest.free_cash_flow == 180_000_000.0
    assert latest.total_debt == 400_000_000.0
    assert latest.cash_and_equivalents == 100_000_000.0
    # §11 companies table has no market columns — cache returns market=None.
    assert cached.market is None
    assert any("not cached" in w.lower() for w in cached.warnings)


def test_company_cache_upsert_is_idempotent(db: Session, testco: CompanyDataBundle) -> None:
    upsert_company(db, testco)
    testco.info.name = "Testco Industrials Incorporated"
    testco.financials[-1].revenue = 1_100_000_000.0
    upsert_company(db, testco)

    assert _count(db, models.Company) == 1
    assert _count(db, models.FinancialStatement) == 5  # unique(company_id, fiscal_year)
    cached = get_cached(db, "TESTCO")
    assert cached is not None
    assert cached.info.name == "Testco Industrials Incorporated"
    assert cached.financials[-1].revenue == 1_100_000_000.0


def test_company_cache_honors_max_age(db: Session, testco: CompanyDataBundle) -> None:
    company = upsert_company(db, testco)
    assert get_cached(db, "TESTCO", max_age_hours=24) is not None

    # Age the row to 48h: stale at the 24h default, fresh at 100h.
    company.fetched_at = datetime.now(timezone.utc) - timedelta(hours=48)
    db.commit()
    assert get_cached(db, "TESTCO", max_age_hours=24) is None
    assert get_cached(db, "TESTCO", max_age_hours=100) is not None


def test_company_cache_unknown_ticker_is_none(db: Session) -> None:
    assert get_cached(db, "NOSUCH") is None


# ---------------------------------------------------------------------------
# Saved deals
# ---------------------------------------------------------------------------


def _setup_user_company(db: Session, testco: CompanyDataBundle) -> tuple[int, int]:
    user = create_user(db, "pe@example.com", "hash")
    company = upsert_company(db, testco)
    return user.id, company.id


def _create_deal(db: Session, user_id: int, company_id: int):
    return create_saved_deal(
        db,
        user_id=user_id,
        company_id=company_id,
        ticker="TESTCO",
        company_name="Testco Industrials Inc",
        kpi_payload=KPI_PAYLOAD,
        score_payload=SCORE_PAYLOAD,
        memo_payload=MEMO_PAYLOAD,
        lbo_assumptions_payload=ASSUMPTIONS_PAYLOAD,
        lbo_output_payload=LBO_OUTPUT_PAYLOAD,
    )


def test_saved_deal_create_roundtrip(db: Session, testco: CompanyDataBundle) -> None:
    user_id, company_id = _setup_user_company(db, testco)
    deal = _create_deal(db, user_id, company_id)

    assert deal.id is not None
    assert deal.ticker == "TESTCO"
    assert deal.company_name == "Testco Industrials Inc"
    assert deal.score == 61.5
    assert deal.rating == "Watchlist"
    # Embedded snapshots reconstructed into schema objects with full integrity.
    assert deal.lbo_assumptions is not None
    assert deal.lbo_assumptions.model_dump() == ASSUMPTIONS_PAYLOAD
    assert deal.memo is not None
    assert deal.memo.rating == "Watchlist"
    assert [s.key for s in deal.memo.sections] == ["company_overview", "screening_view"]

    # Snapshot rows all written (spec §11).
    assert _count(db, models.KpiSnapshot) == 1
    assert _count(db, models.DealScore) == 1
    assert _count(db, models.InvestmentMemo) == 1
    assert _count(db, models.LboAssumptionsRecord) == 1
    assert _count(db, models.LboOutputRecord) == 1
    score_row = db.scalar(select(models.DealScore))
    assert score_row is not None
    assert score_row.total == 61.5 and score_row.payload == SCORE_PAYLOAD


def test_saved_deal_duplicate_raises_typed_error(db: Session, testco: CompanyDataBundle) -> None:
    user_id, company_id = _setup_user_company(db, testco)
    _create_deal(db, user_id, company_id)
    with pytest.raises(DuplicateDealError):
        _create_deal(db, user_id, company_id)
    assert len(list_for_user(db, user_id)) == 1

    # Different user may save the same ticker (unique is per (user_id, ticker)).
    other = create_user(db, "other@example.com", "hash")
    other_deal = _create_deal(db, other.id, company_id)
    assert other_deal.ticker == "TESTCO"


def test_saved_deal_list_for_user(db: Session, testco: CompanyDataBundle) -> None:
    user_id, company_id = _setup_user_company(db, testco)
    assert list_for_user(db, user_id) == []
    created = _create_deal(db, user_id, company_id)

    deals = list_for_user(db, user_id)
    assert len(deals) == 1
    deal = deals[0]
    assert deal.id == created.id
    assert deal.lbo_assumptions is not None
    assert deal.lbo_assumptions.entry_multiple == 8.0
    assert deal.memo is not None
    assert deal.memo.sections[0].content.startswith("Testco Industrials Inc")
    # Other users see nothing.
    assert list_for_user(db, user_id + 999) == []


def test_saved_deal_update_assumptions(db: Session, testco: CompanyDataBundle) -> None:
    user_id, company_id = _setup_user_company(db, testco)
    deal = _create_deal(db, user_id, company_id)

    new_assumptions = dict(ASSUMPTIONS_PAYLOAD)
    new_assumptions["entry_multiple"] = 9.0
    new_assumptions["exit_multiple"] = 9.5
    new_output = {"exit": {"mom": 2.4, "irr": 0.19}}

    updated = update_assumptions(db, deal.id, user_id, new_assumptions, new_output)
    assert updated is not None
    assert updated.lbo_assumptions is not None
    assert updated.lbo_assumptions.entry_multiple == 9.0
    assert updated.lbo_assumptions.exit_multiple == 9.5
    assert updated.updated_at >= updated.created_at
    # A new lbo_outputs row is stored alongside the updated assumptions payload.
    assert _count(db, models.LboOutputRecord) == 2
    listed = list_for_user(db, user_id)[0]
    assert listed.lbo_assumptions is not None
    assert listed.lbo_assumptions.entry_multiple == 9.0

    # Unknown deal id or wrong owner → None (404 semantics in routes).
    assert update_assumptions(db, deal.id + 999, user_id, new_assumptions) is None
    other = create_user(db, "intruder@example.com", "hash")
    assert update_assumptions(db, deal.id, other.id, new_assumptions) is None


def test_saved_deal_delete(db: Session, testco: CompanyDataBundle) -> None:
    user_id, company_id = _setup_user_company(db, testco)
    deal = _create_deal(db, user_id, company_id)

    # Wrong owner cannot delete.
    other = create_user(db, "intruder@example.com", "hash")
    assert delete_deal(db, deal.id, other.id) is False

    assert delete_deal(db, deal.id, user_id) is True
    assert list_for_user(db, user_id) == []
    # Deal-scoped children cascade away; company-level snapshots remain.
    assert _count(db, models.SavedDeal) == 0
    assert _count(db, models.LboAssumptionsRecord) == 0
    assert _count(db, models.LboOutputRecord) == 0
    assert _count(db, models.InvestmentMemo) == 1
    assert _count(db, models.DealScore) == 1
    # Deleting again reports absence.
    assert delete_deal(db, deal.id, user_id) is False
