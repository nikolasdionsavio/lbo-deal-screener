"""SMTP email sending (stdlib smtplib) — config-gated and best-effort.

Sending email must NEVER break a request: with no SMTP configuration the
``send_email`` helper logs and returns ``False`` without touching the network,
and every failure mode (connection, auth, timeout) is caught and turned into a
``False`` return rather than a raised exception.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection/operation timeout for all SMTP calls.
_SMTP_TIMEOUT = 15


def send_email(to: str, subject: str, html: str, text: str) -> bool:
    """Send a multipart text+HTML email; return True on success.

    Returns ``False`` (never raises) when email is unconfigured or anything
    goes wrong, so callers can fire-and-forget without guarding the request.
    """
    if not settings.email_configured:
        logger.info("email not configured; skipping (to=%s subject=%r)", to, subject)
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to
    # Plain-text part first, HTML second: RFC 2046 says the last alternative is
    # the richest, so clients prefer the HTML when they can render it.
    message.attach(MIMEText(text, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from, [to], message.as_string())
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT
            ) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from, [to], message.as_string())
    except Exception:  # noqa: BLE001 — sending must never break the request
        logger.exception("failed to send email (to=%s subject=%r)", to, subject)
        return False

    logger.info("sent email (to=%s subject=%r)", to, subject)
    return True
