"""Auth: password hashing, JWT issue/verify, current-user dependency (spec §12)."""

from app.auth.deps import get_current_user
from app.auth.security import (
    ACCESS_TOKEN_TTL,
    ALGORITHM,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

__all__ = [
    "ACCESS_TOKEN_TTL",
    "ALGORITHM",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "hash_password",
    "verify_password",
]
