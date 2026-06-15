"""Email sending (config-gated) and the forgot/reset-password flow.

No test touches the real network: the SMTP layer is monkeypatched with fakes,
and the route tests capture outgoing email into a list. Reset tokens are
inspected via the crud layer / direct DB rows.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.crud import password_reset as reset_crud
from app.db.models import PasswordResetToken, User, utcnow


# ---------------------------------------------------------------------------
# Email sender (config-gated)
# ---------------------------------------------------------------------------


def test_send_email_unconfigured_returns_false_and_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.email import sender

    # Force "unconfigured": empty SMTP settings.
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    assert settings.email_configured is False

    # If anything tried to open a connection this would explode.
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("SMTP must not be contacted when unconfigured")

    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", _boom)
    monkeypatch.setattr(sender.smtplib, "SMTP", _boom)

    assert sender.send_email("u@example.com", "Hi", "<b>Hi</b>", "Hi") is False


def test_send_email_configured_calls_sendmail_with_right_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.email import sender

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_user", "mailer")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_from", "Sender <from@example.com>")
    assert settings.email_configured is True

    captured: dict[str, object] = {}

    class FakeSMTPSSL:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeSMTPSSL":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            captured["login"] = (user, password)

        def sendmail(self, from_addr: str, to_addrs: list[str], msg: str) -> None:
            captured["from"] = from_addr
            captured["to"] = to_addrs
            captured["msg"] = msg

    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", FakeSMTPSSL)

    ok = sender.send_email("dest@example.com", "Subject", "<b>H</b>", "H")
    assert ok is True
    assert captured["from"] == "Sender <from@example.com>"
    assert captured["to"] == ["dest@example.com"]
    assert captured["login"] == ("mailer", "secret")
    # Both alternatives present in the MIME message.
    assert "Subject" in str(captured["msg"])
    assert "dest@example.com" in str(captured["msg"])


def test_send_email_swallows_exceptions_and_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.email import sender

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_user", "mailer")
    monkeypatch.setattr(settings, "smtp_password", "secret")

    def _raise(*args: object, **kwargs: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(sender.smtplib, "SMTP_SSL", _raise)
    assert sender.send_email("d@example.com", "S", "<b>h</b>", "t") is False


# ---------------------------------------------------------------------------
# Forgot / reset password flow (TestClient, email captured)
# ---------------------------------------------------------------------------


@pytest.fixture()
def captured_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Capture every send_email call instead of contacting SMTP."""
    sent: list[dict[str, str]] = []

    def _capture(to: str, subject: str, html: str, text: str) -> bool:
        sent.append({"to": to, "subject": subject, "html": html, "text": text})
        return True

    # The routes import send_email into their module namespace.
    monkeypatch.setattr("app.api.routes_auth.send_email", _capture)
    return sent


def _register(client: TestClient, email: str, password: str = "password1") -> None:
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


def test_register_returns_token_and_attempts_welcome_email(
    client: TestClient, captured_emails: list[dict[str, str]]
) -> None:
    _register(client, "newuser@example.com")
    assert any(
        e["to"] == "newuser@example.com" and "Welcome" in e["subject"]
        for e in captured_emails
    )


def test_register_succeeds_even_if_email_send_returns_false(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.routes_auth.send_email", lambda *a, **k: False)
    resp = client.post(
        "/api/auth/register",
        json={"email": "noemail@example.com", "password": "password1"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_forgot_password_returns_generic_message_and_sends_reset_link(
    client: TestClient, captured_emails: list[dict[str, str]]
) -> None:
    _register(client, "reset@example.com")
    captured_emails.clear()  # drop the welcome email

    resp = client.post(
        "/api/auth/forgot-password", json={"email": "reset@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == (
        "If an account exists for that email, a reset link is on its way."
    )
    # A reset email with a token link was sent.
    reset_mails = [e for e in captured_emails if "?token=" in e["text"]]
    assert len(reset_mails) == 1
    assert reset_mails[0]["to"] == "reset@example.com"


def _extract_token(reset_text: str) -> str:
    return reset_text.split("?token=")[1].split()[0].strip()


def test_full_reset_flow_token_resets_password_and_logs_in(
    client: TestClient, captured_emails: list[dict[str, str]]
) -> None:
    _register(client, "flow@example.com", password="oldpassword1")
    captured_emails.clear()

    client.post("/api/auth/forgot-password", json={"email": "flow@example.com"})
    reset_mail = next(e for e in captured_emails if "?token=" in e["text"])
    token = _extract_token(reset_mail["text"])

    # Reset to a new password.
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "newpassword2"},
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == (
        "Your password has been reset. You can now sign in."
    )

    # Old password no longer works.
    bad = client.post(
        "/api/auth/login",
        json={"email": "flow@example.com", "password": "oldpassword1"},
    )
    assert bad.status_code == 401
    # New password logs in.
    good = client.post(
        "/api/auth/login",
        json={"email": "flow@example.com", "password": "newpassword2"},
    )
    assert good.status_code == 200
    assert good.json()["access_token"]


def test_reused_token_is_rejected(
    client: TestClient, captured_emails: list[dict[str, str]]
) -> None:
    _register(client, "reuse@example.com")
    captured_emails.clear()
    client.post("/api/auth/forgot-password", json={"email": "reuse@example.com"})
    token = _extract_token(
        next(e for e in captured_emails if "?token=" in e["text"])["text"]
    )

    first = client.post(
        "/api/auth/reset-password", json={"token": token, "password": "password2"}
    )
    assert first.status_code == 200
    second = client.post(
        "/api/auth/reset-password", json={"token": token, "password": "password3"}
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "This reset link is invalid or has expired."


def test_expired_token_is_rejected(client: TestClient) -> None:
    _register(client, "expired@example.com")
    Session = client.session_factory  # type: ignore[attr-defined]
    db = Session()
    try:
        user = db.query(User).filter(User.email == "expired@example.com").one()
        raw = "raw-expired-token-value"
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=reset_crud._hash_token(raw),
                expires_at=utcnow() - timedelta(minutes=5),
                used=False,
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.post(
        "/api/auth/reset-password", json={"token": raw, "password": "password2"}
    )
    assert resp.status_code == 400


def test_wrong_token_is_rejected(client: TestClient) -> None:
    _register(client, "wrong@example.com")
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "totally-bogus-token", "password": "password2"},
    )
    assert resp.status_code == 400


def test_forgot_password_unknown_email_returns_200_and_sends_nothing(
    client: TestClient, captured_emails: list[dict[str, str]]
) -> None:
    resp = client.post(
        "/api/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == (
        "If an account exists for that email, a reset link is on its way."
    )
    assert captured_emails == []


def test_create_token_invalidates_prior_unused_tokens(client: TestClient) -> None:
    _register(client, "rotate@example.com")
    Session = client.session_factory  # type: ignore[attr-defined]
    db = Session()
    try:
        user = db.query(User).filter(User.email == "rotate@example.com").one()
        first_raw = reset_crud.create_token(db, user)
        second_raw = reset_crud.create_token(db, user)
        # Only the second token survives; the first is deleted.
        assert reset_crud.consume_token(db, first_raw) is None
        assert reset_crud.consume_token(db, second_raw) is not None
    finally:
        db.close()
