"""Auth routes (spec §12): register, login, me, forgot/reset password.

JSON bodies, JWT bearer. Transactional email (welcome, reset link) is
best-effort via BackgroundTasks and config-gated — with no SMTP config it is
skipped and the responses are unchanged.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.crud import password_reset as reset_crud
from app.crud import users as users_crud
from app.crud.users import DuplicateEmailError
from app.db.base import get_db
from app.db.models import User
from app.email import password_reset_email, send_email, welcome_email
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}

# Hash of an unguessable throwaway value, verified when the email is unknown so
# login latency does not reveal whether an address is registered.
_DUMMY_HASH = hash_password("dummy-timing-equalizer-not-a-real-password")


def _send_welcome_email(email: str) -> None:
    """Best-effort welcome email (background task; never affects the request)."""
    subject, html, text = welcome_email(email)
    send_email(email, subject, html, text)


def _send_reset_email(email: str, reset_url: str) -> None:
    """Best-effort password-reset email (background task)."""
    subject, html, text = password_reset_email(email, reset_url)
    send_email(email, subject, html, text)


@router.post("/register")
def register(
    body: RegisterRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = users_crud.create_user(db, body.email, hash_password(body.password))
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # Welcome email is best-effort and config-gated; registration succeeds
    # regardless of whether (or how) the email is sent.
    background.add_task(_send_welcome_email, user.email)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = users_crud.get_by_email(db, body.email)
    if user is not None:
        raw = reset_crud.create_token(db, user)
        reset_url = f"{settings.frontend_url}/reset-password?token={raw}"
        background.add_task(_send_reset_email, user.email, reset_url)
    # Always the same response so the endpoint never reveals whether an account
    # exists for the address (no enumeration).
    return {"detail": "If an account exists for that email, a reset link is on its way."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = reset_crud.consume_token(db, body.token)
    if user is None:
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or has expired."
        )
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"detail": "Your password has been reset. You can now sign in."}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = users_crud.get_by_email(db, body.email)
    password_ok = verify_password(
        body.password, user.password_hash if user else _DUMMY_HASH
    )
    if user is None or not password_ok:
        # Same message for unknown email and wrong password (no enumeration).
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers=_WWW_AUTHENTICATE,
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)
