"""SQLAlchemy 2.x engine, session factory, declarative base and init (spec §11)."""

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict[str, object]:
    # SQLite needs check_same_thread disabled for use across FastAPI threads.
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Imports models so they register on Base.metadata.

    Guarded with try/ImportError because app.db.models is added by a later
    build phase (spec §11).
    """
    try:
        import app.db.models  # noqa: F401
    except ImportError:
        pass
    Base.metadata.create_all(bind=engine)
