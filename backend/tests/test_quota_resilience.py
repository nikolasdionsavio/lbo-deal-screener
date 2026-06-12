"""FMP quota resilience (spec §19.8): detection, cooldown, peers cache,
companies.description migration, yfinance profile fallback.

No live network: FMP goes through httpx.MockTransport; the yfinance profile
fallback is exercised via the module-level hook (stubbed suite-wide in
conftest, overridden per-test here).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

import app.providers.fmp as fmp_mod
import app.providers.live as live_mod
from app.crud import peers as peers_crud
from app.crud.companies import get_cached, upsert_company
from app.db.base import Base, run_additive_migrations
from app.db.models import PeersCache
from app.providers.base import DataProvider
from app.providers.fmp import (
    QUOTA_WARNING,
    FmpProvider,
    FmpQuotaExceededError,
    quota_cooldown_active,
    reset_quota_cooldown,
)
from app.providers.live import PROFILE_FALLBACK_WARNING, CompositeLiveProvider
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, SearchResult
from app.services import news_service, peers_service

LIMIT_REACH_BODY = {
    "Error Message": "Limit Reach . Please upgrade your plan or visit our "
    "documentation for more details. By upgrading your plan you will access "
    "to more API calls"
}

_mock_provider = MockProvider()


def _fmp_with(handler: Callable[[httpx.Request], httpx.Response]) -> FmpProvider:
    return FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def _counting_handler(
    response_factory: Callable[[], httpx.Response],
) -> tuple[Callable[[httpx.Request], httpx.Response], dict[str, int]]:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return response_factory()

    return handler, calls


# ---------------------------------------------------------------------------
# Quota detection + module-level cooldown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [200, 429])
def test_limit_reach_body_raises_typed_quota_error(status: int) -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(status, json=LIMIT_REACH_BODY)
    )
    provider = _fmp_with(handler)
    with pytest.raises(FmpQuotaExceededError) as excinfo:
        provider.get_quote("AAPL")
    assert str(excinfo.value) == QUOTA_WARNING  # the literal §19.8 warning
    assert calls["n"] == 1  # quota is terminal today: never retried
    assert quota_cooldown_active()


def test_cooldown_skips_all_fmp_methods_without_http() -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=LIMIT_REACH_BODY)
    )
    provider = _fmp_with(handler)
    with pytest.raises(FmpQuotaExceededError):
        provider.get_profile("AAPL")
    assert calls["n"] == 1

    # The cooldown is module-level: a DIFFERENT provider instance skips FMP
    # entirely (no HTTP) for every method, including get_news.
    other = _fmp_with(handler)
    for call in (
        lambda: other.get_profile("MSFT"),
        lambda: other.get_quote("MSFT"),
        lambda: other.get_peers("MSFT"),
        lambda: other.get_news("MSFT"),
        lambda: other.search("microsoft"),
    ):
        with pytest.raises(FmpQuotaExceededError):
            call()
    assert calls["n"] == 1  # no further requests went out


def test_cooldown_expires_and_allows_a_recheck() -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=LIMIT_REACH_BODY)
    )
    provider = _fmp_with(handler)
    with pytest.raises(FmpQuotaExceededError):
        provider.get_quote("AAPL")
    assert quota_cooldown_active()
    # Rewind the deadline past expiry: the next call rechecks over HTTP.
    with fmp_mod._quota_lock:
        fmp_mod._quota_blocked_until = 0.0
    assert not quota_cooldown_active()
    with pytest.raises(FmpQuotaExceededError):
        provider.get_quote("AAPL")
    assert calls["n"] == 2  # the recheck went out and re-armed the cooldown
    assert quota_cooldown_active()


def test_get_news_quota_body_raises_but_restricted_still_returns_none() -> None:
    provider = _fmp_with(lambda r: httpx.Response(200, json=LIMIT_REACH_BODY))
    with pytest.raises(FmpQuotaExceededError):
        provider.get_news("AAPL")
    assert quota_cooldown_active()

    reset_quota_cooldown()
    restricted = _fmp_with(
        lambda r: httpx.Response(
            200, json={"Error Message": "Restricted Endpoint: not on your plan."}
        )
    )
    assert restricted.get_news("AAPL") is None  # plan-gating is NOT a quota hit
    assert not quota_cooldown_active()


def test_news_service_quota_falls_through_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        news_service,
        "_build_fmp",
        lambda app_settings: _fmp_with(
            lambda r: httpx.Response(200, json=LIMIT_REACH_BODY)
        ),
    )
    from tests.test_news import StubLiveProvider, _install_fake_yfinance, _settings, _yf_item

    _install_fake_yfinance(monkeypatch, [_yf_item(1, "2026-06-10T09:00:00Z")])
    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("test-key")
    )
    assert response.provider == "Yahoo Finance (unofficial endpoints, via yfinance)"
    assert any(QUOTA_WARNING in w for w in response.warnings)


# ---------------------------------------------------------------------------
# Peers cache: fresh / stale / quota+empty paths
# ---------------------------------------------------------------------------

PEERS_PAYLOAD = [
    {"symbol": "DE", "companyName": "Deere & Company", "price": 450.0,
     "mktCap": 122_400_000_000},
    {"symbol": "HD", "companyName": "The Home Depot, Inc.", "price": 360.0,
     "mktCap": 356_400_000_000},
]


class CacheableProvider(DataProvider):
    """Non-mock provider (so the §19.8 peers cache applies) whose bundles
    come from the sample data; no get_peers, so FMP resolves as the source."""

    name = "stub"

    def search(self, query: str) -> list[SearchResult]:  # pragma: no cover
        return []

    def get_company(self, ticker: str) -> CompanyDataBundle:
        return _mock_provider.get_company(ticker)


@pytest.fixture()
def db(client: TestClient) -> Iterator[Session]:
    session = client.session_factory()  # type: ignore[attr-defined]
    yield session
    session.close()


def _peers_via_service(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
):
    from app.core.config import Settings

    settings = Settings(fmp_api_key="test-key", _env_file=None)
    monkeypatch.setattr(
        peers_service, "_build_fmp", lambda app_settings: _fmp_with(handler)
    )
    return peers_service.get_peers(
        "AAPL", db, CacheableProvider(), app_settings=settings
    )


def test_peers_cache_fresh_serves_without_source_call(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=PEERS_PAYLOAD)
    )
    first = _peers_via_service(db, monkeypatch, handler)
    assert [p.ticker for p in first.peers] == ["DE", "HD"]
    assert calls["n"] == 1
    row = peers_crud.get_peers_cache(db, "AAPL")
    assert row is not None and peers_crud.is_fresh(row)

    second = _peers_via_service(db, monkeypatch, handler)
    assert [p.ticker for p in second.peers] == ["DE", "HD"]
    assert calls["n"] == 1  # served from the fresh cache, no second call
    assert second.warnings == []


def test_peers_cache_stale_served_with_warning_on_refresh_failure(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=PEERS_PAYLOAD)
    )
    _peers_via_service(db, monkeypatch, handler)
    # Age the cache beyond the 7-day TTL.
    row = db.query(PeersCache).filter(PeersCache.ticker == "AAPL").one()
    row.fetched_at = datetime.now(timezone.utc) - timedelta(days=8)
    db.commit()

    # The refresh hits the quota: the STALE payload is served with a warning.
    quota_handler, quota_calls = _counting_handler(
        lambda: httpx.Response(200, json=LIMIT_REACH_BODY)
    )
    response = _peers_via_service(db, monkeypatch, quota_handler)
    assert quota_calls["n"] == 1
    assert [p.ticker for p in response.peers] == ["DE", "HD"]
    assert any(
        "served from cache" in w and QUOTA_WARNING in w for w in response.warnings
    )


def test_peers_cache_expired_refresh_succeeds_and_restamps(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=PEERS_PAYLOAD)
    )
    _peers_via_service(db, monkeypatch, handler)
    row = db.query(PeersCache).filter(PeersCache.ticker == "AAPL").one()
    row.fetched_at = datetime.now(timezone.utc) - timedelta(days=8)
    db.commit()

    response = _peers_via_service(db, monkeypatch, handler)
    assert calls["n"] == 2  # expiry forced a refresh
    assert [p.ticker for p in response.peers] == ["DE", "HD"]
    assert response.warnings == []
    db.expire_all()
    row = db.query(PeersCache).filter(PeersCache.ticker == "AAPL").one()
    assert peers_crud.is_fresh(row)  # fetched_at restamped


def test_peers_quota_without_cache_warns_and_returns_empty(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, calls = _counting_handler(
        lambda: httpx.Response(200, json=LIMIT_REACH_BODY)
    )
    response = _peers_via_service(db, monkeypatch, handler)
    assert response.peers == []
    assert response.stats == {}
    assert QUOTA_WARNING in response.warnings  # the literal §19.8 warning
    # The target row is still built from its own (sample-backed) bundle.
    assert response.target.ticker == "AAPL"


def test_peers_non_quota_error_without_cache_keeps_generic_warning(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler, _calls = _counting_handler(lambda: httpx.Response(500))
    response = _peers_via_service(db, monkeypatch, handler)
    assert response.peers == []
    assert any(w.startswith("Peer discovery failed:") for w in response.warnings)


def test_mock_provider_peers_bypass_the_cache(client: TestClient) -> None:
    """Mock peers stay uncached (§11 policy): no peers_cache row is written."""
    from app.api.deps import get_provider_dep
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_provider_dep] = lambda: _mock_provider
    try:
        resp = client.get("/api/companies/TESTCO/peers")
    finally:
        fastapi_app.dependency_overrides.pop(get_provider_dep, None)
    assert resp.status_code == 200
    assert len(resp.json()["peers"]) == 5
    session = client.session_factory()  # type: ignore[attr-defined]
    try:
        assert session.query(PeersCache).count() == 0
    finally:
        session.close()


# ---------------------------------------------------------------------------
# companies.description: additive migration + crud round-trip
# ---------------------------------------------------------------------------


def test_migration_adds_description_to_preexisting_companies_table(
    tmp_path: Path,
) -> None:
    """A database created before §19.8 (companies table without description)
    gains the column via the lightweight additive migration; idempotent."""
    db_path = tmp_path / "old_schema.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY,
                    ticker VARCHAR(16) NOT NULL UNIQUE,
                    name VARCHAR(256),
                    sector VARCHAR(128),
                    industry VARCHAR(128),
                    exchange VARCHAR(64),
                    cik VARCHAR(16),
                    currency VARCHAR(8),
                    data_source VARCHAR(128),
                    fetched_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text("INSERT INTO companies (ticker, name) VALUES ('OLD', 'Old Corp')")
        )

    columns = {c["name"] for c in inspect(engine).get_columns("companies")}
    assert "description" not in columns

    run_additive_migrations(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("companies")}
    assert "description" in columns
    # Existing rows survive with NULL description; the migration is idempotent.
    run_additive_migrations(engine)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT name, description FROM companies WHERE ticker = 'OLD'")
        ).one()
    assert row.name == "Old Corp"
    assert row.description is None

    # create_all on the migrated database completes (description now matches
    # the ORM column) and the ORM can read/write through it.
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def test_company_cache_round_trips_description(db: Session) -> None:
    bundle = _mock_provider.get_company("TESTCO")
    bundle.info.description = "Diversified industrial test fixture."
    bundle.fetched_at = datetime.now(timezone.utc).isoformat()  # within the TTL
    upsert_company(db, bundle)
    cached = get_cached(db, "TESTCO")
    assert cached is not None
    assert cached.info.description == "Diversified industrial test fixture."


# ---------------------------------------------------------------------------
# §19.8 yfinance profile fallback in the live composite
# ---------------------------------------------------------------------------


def _composite_with_quota_fmp(tmp_path: Path) -> CompositeLiveProvider:
    from tests.test_providers import _edgar_handler, _make_edgar

    edgar = _make_edgar(tmp_path / "cache", _edgar_handler())
    fmp = _fmp_with(lambda r: httpx.Response(200, json=LIMIT_REACH_BODY))
    return CompositeLiveProvider(edgar, fmp)


def test_profile_fallback_fills_from_yfinance_when_fmp_quota_hit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        live_mod,
        "_yfinance_profile_info",
        lambda ticker: {
            "sector": "Industrials",
            "industry": "Specialty Industrial Machinery",
            "longBusinessSummary": "Fixture Manufacturing makes fixtures.",
            "fullExchangeName": "New York Stock Exchange",
        },
    )
    bundle = _composite_with_quota_fmp(tmp_path).get_company("FIXT")
    assert bundle.info.sector == "Industrials"
    assert bundle.info.industry == "Specialty Industrial Machinery"
    assert bundle.info.description == "Fixture Manufacturing makes fixtures."
    assert bundle.info.exchange == "New York Stock Exchange"
    assert PROFILE_FALLBACK_WARNING in bundle.warnings
    # The quota warning surfaced through the FMP profile/market paths too.
    assert any(QUOTA_WARNING in w for w in bundle.warnings)


def test_profile_fallback_applies_when_no_fmp_key_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_providers import _edgar_handler, _make_edgar

    monkeypatch.setattr(
        live_mod,
        "_yfinance_profile_info",
        lambda ticker: {"sector": "Industrials", "industry": "Machinery"},
    )
    composite = CompositeLiveProvider(
        _make_edgar(tmp_path / "cache", _edgar_handler()), fmp=None
    )
    bundle = composite.get_company("FIXT")
    assert bundle.info.sector == "Industrials"
    assert bundle.info.industry == "Machinery"
    assert PROFILE_FALLBACK_WARNING in bundle.warnings


def test_profile_fallback_failure_is_silent_best_effort(tmp_path: Path) -> None:
    """conftest stubs the yfinance hook to None: the bundle simply keeps its
    EDGAR-only profile with no fallback warning and no error."""
    bundle = _composite_with_quota_fmp(tmp_path).get_company("FIXT")
    assert bundle.info.sector is None
    assert PROFILE_FALLBACK_WARNING not in bundle.warnings


# Captured at import time (collection), before the conftest autouse fixture
# replaces the module attribute — this is the REAL fallback implementation.
_REAL_YF_HOOK = live_mod._yfinance_profile_info


def test_real_yfinance_hook_reads_ticker_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real hook lazily imports yfinance and tolerates failures."""
    import sys
    import types

    class FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        @property
        def info(self) -> dict[str, Any]:
            return {"sector": "Technology"}

    monkeypatch.setitem(
        sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker)
    )
    # Call the original function captured at import time (conftest patches the
    # module attribute, not the function object itself).
    assert _REAL_YF_HOOK("CRWD") == {"sector": "Technology"}

    class BrokenTicker:
        def __init__(self, ticker: str) -> None:
            raise RuntimeError("boom")

    monkeypatch.setitem(
        sys.modules, "yfinance", types.SimpleNamespace(Ticker=BrokenTicker)
    )
    assert _REAL_YF_HOOK("CRWD") is None
