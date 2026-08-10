"""SQLAlchemy 2.x engine, session factory, declarative base and init (spec §11)."""

from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
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
    # Neon (and other serverless Postgres) auto-suspends when idle and drops
    # pooled connections. pool_pre_ping checks liveness and transparently
    # reconnects a stale connection instead of erroring the first request after
    # an idle period; pool_recycle keeps connections from outliving that window.
    # Both are harmless for SQLite (local/tests).
    pool_pre_ping=True,
    pool_recycle=300,
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


# Columns added to existing tables after their first release (spec §19.8).
# create_all only creates MISSING tables, so pre-existing databases need a
# lightweight additive migration: (table, column, SQL type) triples applied
# via ALTER TABLE ADD COLUMN, which both SQLite and Postgres support.
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("companies", "description", "TEXT"),
    ("users", "oauth_provider", "VARCHAR(20)"),
    # Screening index: profitability and balance-sheet dimensions added after
    # the table's first release, so existing deployments need them added.
    ("screen_index", "gross_profit", "FLOAT"),
    ("screen_index", "gross_margin", "FLOAT"),
    ("screen_index", "net_income", "FLOAT"),
    ("screen_index", "net_margin", "FLOAT"),
    ("screen_index", "operating_margin", "FLOAT"),
    ("screen_index", "cash", "FLOAT"),
    ("screen_index", "total_debt", "FLOAT"),
    ("screen_index", "assets", "FLOAT"),
    ("screen_index", "equity", "FLOAT"),
    ("screen_index", "net_debt", "FLOAT"),
    ("screen_index", "leverage", "FLOAT"),
]


def run_additive_migrations(target_engine: Engine | None = None) -> None:
    """Add any §19.8 columns missing from pre-existing tables.

    Inspects the live schema via the SQLAlchemy inspector and issues plain
    ``ALTER TABLE <t> ADD COLUMN <c> <type>`` for absent columns — additive
    and idempotent, works on SQLite and Postgres alike.
    """
    target_engine = target_engine or engine
    inspector = inspect(target_engine)
    table_names = set(inspector.get_table_names())
    for table, column, sql_type in _ADDITIVE_COLUMNS:
        if table not in table_names:
            continue  # create_all will create it with the full schema
        existing = {col["name"] for col in inspector.get_columns(table)}
        if column in existing:
            continue
        with target_engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def init_db() -> None:
    """Create all tables and apply additive migrations (spec §11, §19.8).

    Imports models so they register on Base.metadata. Guarded with
    try/ImportError because app.db.models is added by a later build phase
    (spec §11).
    """
    try:
        import app.db.models  # noqa: F401
    except ImportError:
        pass
    run_additive_migrations()  # before create_all: alters pre-existing tables
    Base.metadata.create_all(bind=engine)
