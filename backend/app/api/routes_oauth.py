"""Social sign-in routes (spec §12 extension): Google + GitHub OAuth2.

Flow: the frontend sends the browser to ``/{provider}/login`` (a top-level
navigation, not XHR). That sets a signed, cookie-pinned ``state`` and redirects
to the provider. The provider returns to ``/{provider}/callback``, where the
code is exchanged for the user's verified email, a user is linked or created,
and the browser is redirected back to the frontend ``/auth/callback`` with the
app JWT in the URL fragment.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import oauth as oauth_lib
from app.auth.security import create_access_token, hash_password
from app.core.config import settings
from app.crud import users as users_crud
from app.db.base import get_db
from app.email import send_email, welcome_email

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


def _safe_next(next_path: str | None) -> str:
    """Accept only same-origin absolute paths (blocks open-redirect via next)."""
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/"


def _allowed_origin(origin: str | None) -> str | None:
    """Return origin if it is a configured frontend origin, else None."""
    if origin and origin in settings.cors_origins_list:
        return origin.rstrip("/")
    return None


def _frontend_base(origin: str | None) -> str:
    """Where to send the user back: their starting origin if allowlisted,
    otherwise the default frontend URL."""
    return _allowed_origin(origin) or settings.frontend_url.rstrip("/")


def _redirect_to_frontend(base: str, fragment: dict[str, str]) -> RedirectResponse:
    resp = RedirectResponse(
        url=f"{base}/auth/callback#{urlencode(fragment)}", status_code=302
    )
    resp.delete_cookie(oauth_lib.STATE_COOKIE, path=oauth_lib.STATE_COOKIE_PATH)
    return resp


def _send_welcome(email: str) -> None:
    subject, html, text = welcome_email(email)
    send_email(email, subject, html, text)


@router.get("/providers")
def providers() -> dict[str, bool]:
    """Which social providers are configured (drives the frontend buttons)."""
    return oauth_lib.enabled_providers()


@router.get("/{provider}/login")
def oauth_login(
    provider: str, request: Request, next: str = "/"
) -> RedirectResponse:
    cfg = oauth_lib.get_provider(provider)
    if cfg is None:
        raise HTTPException(
            status_code=404, detail="This sign-in method is not available."
        )
    origin = _allowed_origin(request.query_params.get("origin")) or ""
    state = oauth_lib.make_state(provider, _safe_next(next), origin)
    resp = RedirectResponse(url=oauth_lib.authorize_url(cfg, state), status_code=302)
    # Cookie pins the state to this browser; SameSite=Lax still rides the
    # top-level GET redirect back from the provider.
    resp.set_cookie(
        key=oauth_lib.STATE_COOKIE,
        value=state,
        max_age=int(oauth_lib.STATE_TTL.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
        path=oauth_lib.STATE_COOKIE_PATH,
    )
    return resp


@router.get("/{provider}/callback")
def oauth_callback(
    provider: str,
    request: Request,
    background: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    cfg = oauth_lib.get_provider(provider)
    if cfg is None:
        raise HTTPException(
            status_code=404, detail="This sign-in method is not available."
        )

    # Best-effort recovery of the starting origin even on the failure path, so
    # the error lands on the same domain the user came from.
    cookie_state = request.cookies.get(oauth_lib.STATE_COOKIE)
    payload = oauth_lib.verify_state(cookie_state, provider) if cookie_state else None
    base = _frontend_base(payload.get("org") if payload else None)

    def fail() -> RedirectResponse:
        return _redirect_to_frontend(base, {"error": "oauth_failed", "provider": provider})

    if error or not code or not state:
        return fail()
    # CSRF: the state in the URL must equal the state pinned in the cookie.
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        return fail()
    if payload is None:
        return fail()

    access_token = oauth_lib.exchange_code(cfg, code)
    if not access_token:
        return fail()
    email = oauth_lib.fetch_verified_email(cfg, access_token)
    if not email:
        return fail()

    user, created = users_crud.get_or_create_oauth_user(
        db, email, provider, hash_password(secrets.token_urlsafe(32))
    )
    if created:
        background.add_task(_send_welcome, user.email)

    resp = _redirect_to_frontend(
        base,
        {"token": create_access_token(user.id), "next": _safe_next(payload.get("nxt"))},
    )
    # Ensure the welcome task runs even though we return a custom Response.
    resp.background = background
    return resp
