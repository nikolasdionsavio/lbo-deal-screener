"""FastAPI auth dependency (spec §12): Bearer JWT → current User or 401."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.db.base import get_db
from app.db.models import User

_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers=_WWW_AUTHENTICATE)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the authenticated user from the Authorization: Bearer header.

    Raises 401 ({"detail": ...}) on missing, malformed, invalid or expired
    tokens, and when the token's user no longer exists.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise _unauthorized("Not authenticated")

    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Invalid authorization header")

    user_id = decode_token(token)
    if user_id is None:
        raise _unauthorized("Invalid or expired token")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("User not found")
    return user
