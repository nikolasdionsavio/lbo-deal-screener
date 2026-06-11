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
