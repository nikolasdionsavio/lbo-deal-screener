"""Owner-only admin routes (product-update broadcast).

Gated by a shared secret in the ``X-Admin-Token`` header matched against
``settings.admin_token``. When ``admin_token`` is empty (the default) every
endpoint here returns 403, so the capability is inert until the secret is set on
the server. Sending uses the existing Resend transactional sender.

Two modes, both explicit:
- ``test_email``: send only to that one address (preview / deliverability check).
- ``confirm_send_all: true``: send to every registered user (real broadcast).
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import users as users_crud
from app.db.base import get_db
from app.email.sender import send_email
from app.email.templates import update_announcement_email

router = APIRouter(prefix="/admin", tags=["admin"])


class AnnounceRequest(BaseModel):
    test_email: str | None = None
    confirm_send_all: bool = False
    dry_run: bool = False


class AnnounceResult(BaseModel):
    mode: str  # "dry_run" | "test" | "all"
    subject: str
    recipients: int
    sent: int
    failed: int


def _require_admin(x_admin_token: str | None) -> None:
    expected = settings.admin_token.strip()
    if not expected:
        raise HTTPException(status_code=403, detail="Admin endpoints are disabled.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Invalid admin token.")


@router.post("/announce")
def announce(
    body: AnnounceRequest,
    x_admin_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AnnounceResult:
    _require_admin(x_admin_token)

    # Count who a broadcast would reach, without sending anything. Checked first
    # so it always wins (a safe default even if another mode is also set).
    if body.dry_run:
        emails = users_crud.list_emails(db)
        return AnnounceResult(
            mode="dry_run",
            subject=update_announcement_email("")[0],
            recipients=len(emails),
            sent=0,
            failed=0,
        )

    if body.test_email:
        subject, html, text = update_announcement_email(body.test_email)
        ok = send_email(body.test_email.strip(), subject, html, text)
        return AnnounceResult(
            mode="test",
            subject=subject,
            recipients=1,
            sent=1 if ok else 0,
            failed=0 if ok else 1,
        )

    if body.confirm_send_all:
        emails = users_crud.list_emails(db)
        subject = update_announcement_email("")[0]
        sent = 0
        failed = 0
        for email in emails:
            s, html, text = update_announcement_email(email)
            if send_email(email, s, html, text):
                sent += 1
            else:
                failed += 1
        return AnnounceResult(
            mode="all",
            subject=subject,
            recipients=len(emails),
            sent=sent,
            failed=failed,
        )

    raise HTTPException(
        status_code=400,
        detail="Specify test_email (preview) or confirm_send_all=true (broadcast).",
    )
