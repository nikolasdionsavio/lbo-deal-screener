"""Owner-only announce endpoint: auth gating + test-mode send."""

import pytest
from fastapi.testclient import TestClient

import app.api.routes_admin as routes_admin
from app.core.config import settings


def test_announce_disabled_by_default(client: TestClient) -> None:
    # admin_token is empty by default -> endpoint is inert (403).
    r = client.post("/api/admin/announce", json={"test_email": "a@b.com"})
    assert r.status_code == 403


def test_announce_rejects_wrong_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")
    r = client.post(
        "/api/admin/announce",
        json={"test_email": "a@b.com"},
        headers={"X-Admin-Token": "wrong"},
    )
    assert r.status_code == 403


def test_announce_test_mode_sends_one(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")
    sent: list[str] = []
    monkeypatch.setattr(
        routes_admin, "send_email", lambda to, s, h, t: sent.append(to) or True
    )
    r = client.post(
        "/api/admin/announce",
        json={"test_email": "me@example.com"},
        headers={"X-Admin-Token": "secret-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "test"
    assert body["recipients"] == 1 and body["sent"] == 1
    assert sent == ["me@example.com"]
    assert "Investment Intelligence" in body["subject"]


def test_announce_dry_run_counts_without_sending(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")
    monkeypatch.setattr(routes_admin.users_crud, "list_emails", lambda db: ["a@b.com", "c@d.com"])
    sent: list[str] = []
    monkeypatch.setattr(
        routes_admin, "send_email", lambda to, s, h, t: sent.append(to) or True
    )
    r = client.post(
        "/api/admin/announce",
        json={"dry_run": True},
        headers={"X-Admin-Token": "secret-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "dry_run"
    assert body["recipients"] == 2 and body["sent"] == 0
    assert sent == []  # nothing was actually sent


def test_announce_requires_a_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "admin_token", "secret-token")
    r = client.post(
        "/api/admin/announce",
        json={},
        headers={"X-Admin-Token": "secret-token"},
    )
    assert r.status_code == 400
