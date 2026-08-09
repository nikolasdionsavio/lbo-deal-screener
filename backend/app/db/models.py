"""SQLAlchemy 2.x ORM models — the spec §11 tables plus peers_cache (§19.8).

JSON payload columns use ``sqlalchemy.JSON`` (works on SQLite and Postgres).
All datetime columns are UTC; on SQLite the timezone offset is dropped on
write, so readers must treat naive values as UTC (the crud layer does).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Timezone-aware UTC now, used for all datetime column defaults."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # Set when the account was created via an OAuth provider ("google" /
    # "github"). Such accounts get a random, unusable password_hash so password
    # login can never succeed for them; this column just records the origin.
    oauth_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    saved_deals: Mapped[list[SavedDeal]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    """One-time password-reset token (only the SHA-256 hash is stored).

    A raw ``secrets.token_urlsafe`` value is emailed to the user; the column
    holds its sha256 hex digest so a database leak does not expose live links.
    A token is valid while ``used`` is False and ``expires_at`` is in the
    future (1 hour after creation).
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(256))
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(128))
    exchange: Mapped[str | None] = mapped_column(String(64))
    cik: Mapped[str | None] = mapped_column(String(16))
    # Company business description (§19.8): kept in the cache so cache hits
    # retain the dashboard description. Added by an additive migration in
    # init_db for databases created before this column existed.
    description: Mapped[str | None] = mapped_column(Text)
    # Financial reporting currency of the cached bundle (spec §4); None ≡ USD.
    currency: Mapped[str | None] = mapped_column(String(8))
    data_source: Mapped[str | None] = mapped_column(String(128))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    financial_statements: Mapped[list[FinancialStatement]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="FinancialStatement.fiscal_year",
    )


class FinancialStatement(Base):
    """Write-through cache of one fiscal year's canonical financials (§11)."""

    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_financials_company_fy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str | None] = mapped_column(String(128))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="financial_statements")


class PeersCache(Base):
    """Cached FMP peer-discovery payload per ticker (spec §19.8, 7-day TTL).

    ``payload`` is the raw §19.2 peers list ``[{symbol, name, price, mktCap}]``
    so a quota-hit refresh can serve the stale list with a warning.
    """

    __tablename__ = "peers_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, index=True
    )
    payload: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    as_of: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class LboAssumptionsRecord(Base):
    __tablename__ = "lbo_assumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    saved_deal_id: Mapped[int] = mapped_column(
        ForeignKey("saved_deals.id"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    saved_deal: Mapped[SavedDeal] = relationship(back_populates="lbo_assumptions")
    outputs: Mapped[list[LboOutputRecord]] = relationship(
        back_populates="assumptions", cascade="all, delete-orphan"
    )


class LboOutputRecord(Base):
    __tablename__ = "lbo_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lbo_assumptions_id: Mapped[int] = mapped_column(
        ForeignKey("lbo_assumptions.id"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    assumptions: Mapped[LboAssumptionsRecord] = relationship(back_populates="outputs")


class DealScore(Base):
    __tablename__ = "deal_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    total: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class InvestmentMemo(Base):
    __tablename__ = "investment_memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    rating: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ScreenIndexRow(Base):
    """One US filer's latest annual figures, for cross-company screening.

    Built from the SEC frames API (app.screening.frames), one row per CIK. This
    is a rebuildable index, not a system of record: ``rebuild_index`` upserts by
    CIK so a refresh replaces figures in place.

    ``ebitda`` is CALCULATED (operating income + D&A) and is NULL whenever the
    filer did not tag D&A separately. ``coverage`` says which case a row is, so
    the UI can show "not disclosed" instead of implying a missing figure is zero.
    """

    __tablename__ = "screen_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cik: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True)
    entity_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # SIC industry classification from the EDGAR submissions endpoint.
    sic: Mapped[str | None] = mapped_column(String(8), index=True)
    sic_description: Mapped[str | None] = mapped_column(String(160), index=True)
    exchange: Mapped[str | None] = mapped_column(String(32))

    period: Mapped[str] = mapped_column(String(8), nullable=False)  # "CY2025"
    period_end: Mapped[str | None] = mapped_column(String(16))
    accession: Mapped[str | None] = mapped_column(String(32))

    revenue: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    revenue_tag: Mapped[str | None] = mapped_column(String(80))
    operating_income: Mapped[float | None] = mapped_column(Float)
    depreciation_amortization: Mapped[float | None] = mapped_column(Float)
    ebitda: Mapped[float | None] = mapped_column(Float, index=True)
    ebitda_margin: Mapped[float | None] = mapped_column(Float)
    coverage: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # Set when a filed figure is arithmetically right but misleading as filed
    # (currently: EBITDA above revenue, i.e. a one-off gain inside operating
    # income). Flagged rather than removed, and never silently ranked first.
    quality_flag: Mapped[str | None] = mapped_column(String(32), index=True)

    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class SavedDeal(Base):
    __tablename__ = "saved_deals"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_saved_deals_user_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    company_name: Mapped[str] = mapped_column(String(256), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[str | None] = mapped_column(String(32))
    memo_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_memos.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="saved_deals")
    lbo_assumptions: Mapped[list[LboAssumptionsRecord]] = relationship(
        back_populates="saved_deal",
        cascade="all, delete-orphan",
        order_by="LboAssumptionsRecord.id",
    )
