"""Auth routes (spec §12): register, login, me — JSON bodies, JWT bearer."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.crud import users as users_crud
from app.crud.users import DuplicateEmailError
from app.db.base import get_db
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}

# Hash of an unguessable throwaway value, verified when the email is unknown so
# login latency does not reveal whether an address is registered.
_DUMMY_HASH = hash_password("dummy-timing-equalizer-not-a-real-password")


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = users_crud.create_user(db, body.email, hash_password(body.password))
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TokenResponse(access_token=create_access_token(user.id))


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
