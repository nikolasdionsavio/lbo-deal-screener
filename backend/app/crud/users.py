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


def list_emails(db: Session) -> list[str]:
    """Every registered user's email (for owner-only broadcasts)."""
    rows = db.scalars(select(User.email)).all()
    return [e for e in rows if e]


def get_or_create_oauth_user(
    db: Session, email: str, provider: str, password_hash: str
) -> tuple[User, bool]:
    """Find a user by (verified) email, or create one for an OAuth sign-in.

    Returns ``(user, created)``. An existing account is linked by email so a
    person who first registered with a password and later uses Google/GitHub
    with the same verified address lands on the same account. New OAuth users
    are given the caller-supplied random ``password_hash`` (unusable for
    password login) and a recorded ``oauth_provider``.
    """
    email = email.strip().lower()
    user = get_by_email(db, email)
    if user is not None:
        return user, False

    user = User(email=email, password_hash=password_hash, oauth_provider=provider)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        # Concurrent create for the same email: fall back to the existing row.
        db.rollback()
        existing = get_by_email(db, email)
        if existing is not None:
            return existing, False
        raise DuplicateEmailError(f"email already registered: {email}") from exc
    db.refresh(user)
    return user, True
