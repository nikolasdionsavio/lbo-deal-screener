"""peers_cache storage primitives (spec §19.8): 7-day-TTL peer discovery cache.

Stores the raw §19.2 peers payload per ticker so peers_service can serve the
cache while fresh, refresh on expiry, and fall back to the STALE payload when
the refresh hits the FMP quota (or any provider error).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PeersCache

PEERS_CACHE_TTL_DAYS = 7


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes (SQLite round-trip) as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_peers_cache(db: Session, ticker: str) -> PeersCache | None:
    """The cached row for the ticker regardless of age, or None."""
    return db.scalar(select(PeersCache).where(PeersCache.ticker == ticker.upper()))


def is_fresh(row: PeersCache, ttl_days: int = PEERS_CACHE_TTL_DAYS) -> bool:
    """True while the row is within the §19.8 TTL."""
    age = datetime.now(timezone.utc) - _as_utc(row.fetched_at)
    return age <= timedelta(days=ttl_days)


def upsert_peers_cache(
    db: Session, ticker: str, payload: list[dict[str, Any]]
) -> PeersCache:
    """Insert or replace the cached payload, stamping fetched_at = now."""
    ticker = ticker.upper()
    row = get_peers_cache(db, ticker)
    if row is None:
        row = PeersCache(ticker=ticker)
        db.add(row)
    row.payload = list(payload)
    row.fetched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
