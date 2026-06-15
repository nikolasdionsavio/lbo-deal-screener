"""Plain, professional transactional email copy (welcome + password reset).

Each builder returns ``(subject, html, text)``. The HTML uses simple inline
styles only (no external CSS, no images) so it renders predictably across
clients; the text part is the readable fallback.
"""

from __future__ import annotations

_SITE_URL = "https://nikolasproject.com"
_SIGNATURE = "Investment Intelligence"

# Shared inline-styled wrapper for the HTML body.
_HTML_WRAPPER = (
    '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;'
    'line-height:1.6;color:#0f172a;max-width:560px;margin:0 auto;">{body}</div>'
)

_BUTTON = (
    '<a href="{url}" style="display:inline-block;padding:10px 18px;'
    "background:#1e3a5f;color:#ffffff;text-decoration:none;border-radius:4px;"
    'font-weight:bold;">{label}</a>'
)


def welcome_email(to: str) -> tuple[str, str, str]:
    """Welcome / registration confirmation email."""
    subject = "Welcome to Investment Intelligence"

    text = (
        "Thanks for registering with Investment Intelligence.\n\n"
        "The tool helps you analyze US-listed companies end to end: financial "
        "statements, KPIs, valuation, a 5-year LBO model, peer comparables, and "
        "an auto-generated investment memo.\n\n"
        f"Get started: {_SITE_URL}\n\n"
        f"{_SIGNATURE}"
    )

    body = (
        "<p>Thanks for registering with Investment Intelligence.</p>"
        "<p>The tool helps you analyze US-listed companies end to end: "
        "financial statements, KPIs, valuation, a 5-year LBO model, peer "
        "comparables, and an auto-generated investment memo.</p>"
        f"<p>{_BUTTON.format(url=_SITE_URL, label='Get started')}</p>"
        f"<p style=\"color:#475569;\">{_SIGNATURE}</p>"
    )
    html = _HTML_WRAPPER.format(body=body)
    return subject, html, text


def password_reset_email(to: str, reset_url: str) -> tuple[str, str, str]:
    """Password-reset email containing the one-time reset link."""
    subject = "Reset your Investment Intelligence password"

    text = (
        "We received a request to reset your password.\n\n"
        f"Reset it here: {reset_url}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can "
        "safely ignore this email and your password will stay the same.\n\n"
        f"{_SIGNATURE}"
    )

    body = (
        "<p>We received a request to reset your password.</p>"
        f"<p>{_BUTTON.format(url=reset_url, label='Reset password')}</p>"
        '<p style="color:#475569;">This link expires in 1 hour. If you didn\'t '
        "request this, you can safely ignore this email and your password will "
        "stay the same.</p>"
        f"<p style=\"color:#475569;\">{_SIGNATURE}</p>"
    )
    html = _HTML_WRAPPER.format(body=body)
    return subject, html, text
