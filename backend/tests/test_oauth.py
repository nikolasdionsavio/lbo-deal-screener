"""Social sign-in (Google/GitHub OAuth2): config gating, the login redirect,
the CSRF-checked callback, and link-or-create behavior.

No test touches the network: the provider HTTP calls (code exchange + email
lookup) are monkeypatched, exactly like the email tests stub SMTP.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import oauth as oauth_lib
from app.core.config import settings
from app.crud import users as users_crud
from app.db.models import User


def _enable_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "gid", raising=False)
    monkeypatch.setattr(settings, "google_client_secret", "gsecret", raising=False)
    monkeypatch.setattr(settings, "backend_url", "https://backend.test", raising=False)


def _disable_all(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "google_client_id",
        "google_client_secret",
        "github_client_id",
        "github_client_secret",
        "backend_url",
    ):
        monkeypatch.setattr(settings, key, "", raising=False)


# ---------------------------------------------------------------------------
# providers endpoint
# ---------------------------------------------------------------------------


def test_providers_endpoint_all_false_when_unconfigured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_all(monkeypatch)
    resp = client.get("/api/auth/oauth/providers")
    assert resp.status_code == 200
    assert resp.json() == {"google": False, "github": False}


def test_providers_endpoint_reports_enabled_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_all(monkeypatch)
    _enable_google(monkeypatch)
    assert client.get("/api/auth/oauth/providers").json() == {
        "google": True,
        "github": False,
    }


# ---------------------------------------------------------------------------
# login redirect
# ---------------------------------------------------------------------------


def test_login_redirects_to_provider_with_state_cookie(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_google(monkeypatch)
    resp = client.get(
        "/api/auth/oauth/google/login?next=/deals", follow_redirects=False
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "state=" in location and "client_id=gid" in location
    # State is pinned to a cookie for the callback's CSRF check.
    assert "oauth_state=" in resp.headers.get("set-cookie", "")


def test_login_unknown_provider_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_google(monkeypatch)
    assert client.get("/api/auth/oauth/bogus/login").status_code == 404


def test_login_disabled_provider_is_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_all(monkeypatch)
    assert client.get("/api/auth/oauth/google/login").status_code == 404


# ---------------------------------------------------------------------------
# callback
# ---------------------------------------------------------------------------


def test_callback_creates_user_and_redirects_with_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_google(monkeypatch)
    monkeypatch.setattr(oauth_lib, "exchange_code", lambda cfg, code: "access-tok")
    monkeypatch.setattr(
        oauth_lib, "fetch_verified_email", lambda cfg, tok: "newgoogle@example.com"
    )

    state = oauth_lib.make_state("google", "/deals", "")
    resp = client.get(
        f"/api/auth/oauth/google/callback?code=abc&state={state}",
        cookies={"oauth_state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith(f"{settings.frontend_url}/auth/callback#")
    assert "token=" in location and "next=%2Fdeals" in location
    assert "error=" not in location

    Session = client.session_factory  # type: ignore[attr-defined]
    db = Session()
    try:
        user = db.query(User).filter(User.email == "newgoogle@example.com").one()
        assert user.oauth_provider == "google"
    finally:
        db.close()


def test_callback_rejects_state_mismatch(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_google(monkeypatch)
    called = {"exchange": False}

    def _should_not_run(cfg, code):  # pragma: no cover - must not be called
        called["exchange"] = True
        return "access-tok"

    monkeypatch.setattr(oauth_lib, "exchange_code", _should_not_run)

    cookie_state = oauth_lib.make_state("google", "/", "")
    resp = client.get(
        "/api/auth/oauth/google/callback?code=abc&state=tampered-value",
        cookies={"oauth_state": cookie_state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]
    assert "token=" not in resp.headers["location"]
    assert called["exchange"] is False


def test_callback_provider_error_redirects_without_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enable_google(monkeypatch)
    state = oauth_lib.make_state("google", "/", "")
    resp = client.get(
        f"/api/auth/oauth/google/callback?error=access_denied&state={state}",
        cookies={"oauth_state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


# ---------------------------------------------------------------------------
# link-or-create
# ---------------------------------------------------------------------------


def test_get_or_create_links_existing_and_creates_new(client: TestClient) -> None:
    Session = client.session_factory  # type: ignore[attr-defined]
    db = Session()
    try:
        # New OAuth user.
        user, created = users_crud.get_or_create_oauth_user(
            db, "Person@Example.com", "github", "randomhash"
        )
        assert created is True
        assert user.email == "person@example.com"
        assert user.oauth_provider == "github"

        # Same email again links to the same row.
        again, created2 = users_crud.get_or_create_oauth_user(
            db, "person@example.com", "github", "otherhash"
        )
        assert created2 is False
        assert again.id == user.id

        # A pre-existing password account is linked, not duplicated.
        pw_user = users_crud.create_user(db, "pw@example.com", "pwhash")
        linked, created3 = users_crud.get_or_create_oauth_user(
            db, "pw@example.com", "google", "randomhash2"
        )
        assert created3 is False
        assert linked.id == pw_user.id
    finally:
        db.close()
