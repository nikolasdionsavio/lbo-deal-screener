"""User persistence helpers (spec §11, §12)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import User


class DuplicateEmailError(Exception):
    """Email already registered — routes map this to HTTP 409."""


def create_user(db: Session, email: str, password_hash: str) -> User:
    """Insert a user; raises DuplicateEmailError on a unique-email violation."""
    email = email.strip().lower()
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmailError(f"email already registered: {email}") from exc
    db.refresh(user)
    return user


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))
