"""Google + GitHub OAuth2 sign-in (authorization-code flow).

Hand-rolled over httpx + PyJWT, so no new dependency and nothing hidden: the
backend holds the client secret, exchanges the code, reads the provider's
*verified* email, and links/creates a user by that address. CSRF is prevented
by a short-lived signed ``state`` token that is also pinned to a cookie and
checked on the callback. The issued app JWT is handed back to the frontend in a
URL fragment so it never lands in a server log or Referer header.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import settings

STATE_TTL = timedelta(minutes=10)
STATE_COOKIE = "oauth_state"
STATE_COOKIE_PATH = "/api/auth/oauth"
_ALGO = "HS256"
_TIMEOUT = 10.0


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    authorize_url: str
    token_url: str
    scope: str
    client_id: str
    client_secret: str


def _providers() -> dict[str, ProviderConfig]:
    return {
        "google": ProviderConfig(
            name="google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scope="openid email profile",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        ),
        "github": ProviderConfig(
            name="github",
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scope="read:user user:email",
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
        ),
    }


def provider_enabled(name: str) -> bool:
    """A provider is usable only with id, secret, and a known backend URL."""
    p = _providers().get(name)
    return bool(p and p.client_id and p.client_secret and settings.backend_url)


def enabled_providers() -> dict[str, bool]:
    return {name: provider_enabled(name) for name in _providers()}


def get_provider(name: str) -> ProviderConfig | None:
    return _providers().get(name) if provider_enabled(name) else None


def redirect_uri(name: str) -> str:
    """Backend callback URL; must match the provider console exactly."""
    return f"{settings.backend_url.rstrip('/')}/api/auth/oauth/{name}/callback"


# ---------------------------------------------------------------------------
# State (signed, short-lived, cookie-pinned)
# ---------------------------------------------------------------------------


def make_state(provider: str, next_path: str, origin: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "oauth_state",
        "prv": provider,
        "nxt": next_path,
        "org": origin,
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + STATE_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def verify_state(token: str, provider: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
    except jwt.InvalidTokenError:
        return None
    if payload.get("typ") != "oauth_state" or payload.get("prv") != provider:
        return None
    return payload


# ---------------------------------------------------------------------------
# Authorization-code dance
# ---------------------------------------------------------------------------


def authorize_url(provider: ProviderConfig, state: str) -> str:
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri(provider.name),
        "scope": provider.scope,
        "state": state,
        "response_type": "code",
    }
    if provider.name == "google":
        params["access_type"] = "online"
        params["prompt"] = "select_account"
        params["include_granted_scopes"] = "true"
    elif provider.name == "github":
        params["allow_signup"] = "true"
    return f"{provider.authorize_url}?{urlencode(params)}"


def exchange_code(provider: ProviderConfig, code: str) -> str | None:
    """Swap the authorization code for an access token; None on any failure."""
    data = {
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "code": code,
        "redirect_uri": redirect_uri(provider.name),
        "grant_type": "authorization_code",
    }
    try:
        resp = httpx.post(
            provider.token_url,
            data=data,
            headers={"Accept": "application/json"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        token = resp.json().get("access_token")
    except ValueError:
        return None
    return token or None


def fetch_verified_email(provider: ProviderConfig, access_token: str) -> str | None:
    """Return the provider's *verified* primary email, or None.

    Only verified addresses are trusted: linking accounts by email is safe
    only if the provider has confirmed the user owns it.
    """
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    try:
        if provider.name == "google":
            resp = httpx.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers=headers,
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            verified = data.get("email_verified")
            if not data.get("email") or verified in (False, "false"):
                return None
            return str(data["email"]).strip().lower()

        if provider.name == "github":
            resp = httpx.get(
                "https://api.github.com/user/emails",
                headers={**headers, "X-GitHub-Api-Version": "2022-11-28"},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return None
            emails = resp.json()
            if not isinstance(emails, list):
                return None
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            chosen = primary or next((e for e in emails if e.get("verified")), None)
            if not chosen or not chosen.get("email"):
                return None
            return str(chosen["email"]).strip().lower()
    except (httpx.HTTPError, ValueError):
        return None
    return None
