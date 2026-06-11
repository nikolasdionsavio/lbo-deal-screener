"""Password hashing (bcrypt directly) and JWT (PyJWT HS256) — spec §2.8, §12.

Tokens carry ``sub`` = user id as a string and expire after 7 days.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(days=7)

# bcrypt only uses the first 72 bytes; bcrypt>=5 raises beyond that, so we
# truncate explicitly for deterministic behavior on long passwords.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password with a fresh bcrypt salt."""
    raw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """True if the plaintext password matches the stored bcrypt hash."""
    raw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        # Malformed stored hash — treat as non-matching rather than erroring.
        return False


def create_access_token(
    user_id: int, expires_delta: timedelta | None = None
) -> str:
    """Create an HS256 JWT with sub = user id (string) and 7-day expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + (expires_delta if expires_delta is not None else ACCESS_TOKEN_TTL),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if invalid/expired.

    Callers (the auth dependency) map None to HTTP 401.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None
