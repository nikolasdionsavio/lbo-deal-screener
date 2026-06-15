"""Password-reset token persistence (spec §11, §12 extension).

Only the SHA-256 hash of the raw token is stored. ``create_token`` returns the
raw token (to be emailed); ``consume_token`` hashes the presented raw token,
validates it (exists, unused, unexpired), marks it used, and returns the owner.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import PasswordResetToken, User, utcnow

# Reset links are valid for one hour from creation.
TOKEN_TTL = timedelta(hours=1)


def _hash_token(raw_token: str) -> str:
    """SHA-256 hex digest of the raw token (what gets stored/looked up)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_token(db: Session, user: User) -> str:
    """Create a fresh reset token for ``user`` and return the raw value.

    Any prior unused tokens for the user are deleted first so only the most
    recent link is live.
    """
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used.is_(False),
        )
    )
    raw_token = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=utcnow() + TOKEN_TTL,
        used=False,
    )
    db.add(record)
    db.commit()
    return raw_token


def consume_token(db: Session, raw_token: str) -> User | None:
    """Validate and consume a raw reset token; return its user or None.

    Valid means the token exists, is unused, and is not expired. On success the
    token is marked used (single-use) and committed.
    """
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_token(raw_token)
        )
    )
    if record is None or record.used:
        return None

    # expires_at may be naive (SQLite drops tz on write); treat naive as UTC.
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utcnow():
        return None

    record.used = True
    user = db.get(User, record.user_id)
    db.commit()
    return user
