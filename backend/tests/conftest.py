"""Shared pytest fixtures (spec §15). Test modules are added by later phases."""

import json
from pathlib import Path
from typing import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app
from app.schemas.company import CompanyDataBundle

BACKEND_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BACKEND_DIR / "data" / "sample"


@pytest.fixture(autouse=True)
def _reset_fmp_quota_cooldown() -> Iterator[None]:
    """The §19.8 FMP quota cooldown is module-level state; never let one
    test's quota hit bleed into another."""
    from app.providers import fmp

    fmp.reset_quota_cooldown()
    yield
    fmp.reset_quota_cooldown()


@pytest.fixture(autouse=True)
def _stub_yfinance_profile_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The §19.8 live-composite profile fallback calls yfinance Ticker.info;
    no pytest test may hit the live network, so it is stubbed to "no data"
    suite-wide. Tests of the fallback monkeypatch their own fake on top."""
    monkeypatch.setattr(
        "app.providers.live._yfinance_profile_info", lambda ticker: None
    )


@pytest.fixture(autouse=True)
def _stub_market_stats_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The /market-stats endpoint fetches yfinance .info directly; stub it to
    "no data" suite-wide and clear its cache so no test hits the live network.
    Tests of the endpoint monkeypatch their own fake .info on top."""
    import app.market_stats as market_stats

    market_stats.reset_cache()
    monkeypatch.setattr(market_stats, "_fetch_info", lambda ticker: None)
    yield
    market_stats.reset_cache()


@pytest.fixture()
def testco_bundle() -> CompanyDataBundle:
    """The hand-checkable TESTCO fixture parsed into the canonical bundle."""
    raw = json.loads((SAMPLE_DIR / "TESTCO.json").read_text())
    return CompanyDataBundle.model_validate(raw)


@pytest.fixture()
def client_factory() -> Iterator[Callable[[], TestClient]]:
    """Factory building TestClients whose get_db uses a fresh in-memory SQLite.

    Each call creates an isolated database (StaticPool keeps the single
    in-memory connection alive across sessions).
    """
    clients: list[TestClient] = []

    def _make() -> TestClient:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        try:
            # Aliased so the package name "app" is not bound locally (it would
            # shadow the FastAPI app imported above).
            import app.db.models as _models  # noqa: F401
        except ImportError:
            pass
        Base.metadata.create_all(bind=engine)

        def override_get_db() -> Iterator[object]:
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        # Expose the per-client sessionmaker so tests can inspect rows (e.g.
        # asserting lbo_outputs snapshots were appended).
        client.session_factory = TestingSessionLocal  # type: ignore[attr-defined]
        clients.append(client)
        return client

    yield _make

    for c in clients:
        c.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(client_factory: Callable[[], TestClient]) -> TestClient:
    """A ready-to-use TestClient backed by a fresh in-memory SQLite database."""
    return client_factory()
