"""Auth unit tests (spec §15): bcrypt roundtrip, JWT roundtrip/expiry/tamper,
and the get_current_user dependency's 401 semantics."""

from datetime import timedelta
from typing import Iterator

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

import app.db.models as models
from app.auth.deps import get_current_user
from app.auth.security import (
    ALGORITHM,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.db.base import Base


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def test_hash_verify_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_wrong_password_is_false() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_hashes_are_salted() -> None:
    assert hash_password("samepassword") != hash_password("samepassword")


def test_verify_malformed_hash_is_false() -> None:
    assert verify_password("whatever", "not-a-bcrypt-hash") is False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def test_token_create_decode_roundtrip_sub_matches() -> None:
    token = create_access_token(42)
    assert decode_token(token) == 42
    # sub must be stored as a string (spec §12)
    payload = pyjwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert isinstance(payload["sub"], str)


def test_expired_token_returns_none() -> None:
    token = create_access_token(7, expires_delta=timedelta(seconds=-10))
    assert decode_token(token) is None


def test_tampered_token_rejected() -> None:
    token = create_access_token(7)
    # Re-sign with a different secret: signature check must fail.
    forged = pyjwt.encode({"sub": "7"}, "attacker-secret", algorithm=ALGORITHM)
    assert decode_token(forged) is None
    # Corrupt the signature segment of a genuine token.
    head, payload, sig = token.split(".")
    corrupted_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    assert decode_token(f"{head}.{payload}.{corrupted_sig}") is None


def test_non_integer_sub_returns_none() -> None:
    token = pyjwt.encode({"sub": "not-an-id"}, settings.jwt_secret, algorithm=ALGORITHM)
    assert decode_token(token) is None


# ---------------------------------------------------------------------------
# get_current_user dependency (401 semantics)
# ---------------------------------------------------------------------------


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


def _request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in (headers or {}).items()
    ]
    return Request({"type": "http", "headers": raw_headers, "method": "GET", "path": "/"})


def _assert_401(exc_info: pytest.ExceptionInfo[HTTPException]) -> None:
    assert exc_info.value.status_code == 401
    assert isinstance(exc_info.value.detail, str)


def test_get_current_user_missing_header_401(db: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request(), db)
    _assert_401(exc_info)


def test_get_current_user_non_bearer_scheme_401(db: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request({"Authorization": "Basic abc123"}), db)
    _assert_401(exc_info)


def test_get_current_user_invalid_token_401(db: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request({"Authorization": "Bearer not.a.jwt"}), db)
    _assert_401(exc_info)


def test_get_current_user_expired_token_401(db: Session) -> None:
    user = models.User(email="a@example.com", password_hash=hash_password("password1"))
    db.add(user)
    db.commit()
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request({"Authorization": f"Bearer {token}"}), db)
    _assert_401(exc_info)


def test_get_current_user_unknown_user_401(db: Session) -> None:
    token = create_access_token(999999)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request({"Authorization": f"Bearer {token}"}), db)
    _assert_401(exc_info)


def test_get_current_user_valid_token_returns_user(db: Session) -> None:
    user = models.User(email="b@example.com", password_hash=hash_password("password1"))
    db.add(user)
    db.commit()
    token = create_access_token(user.id)
    resolved = get_current_user(_request({"Authorization": f"Bearer {token}"}), db)
    assert resolved.id == user.id
    assert resolved.email == "b@example.com"
