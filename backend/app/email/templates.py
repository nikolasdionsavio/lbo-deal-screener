"""Branded transactional email copy (welcome + password reset).

Each builder returns ``(subject, html, text)``. The HTML is table-based with
inline styles only (no <style> block, no SVG, no background images) so it
renders predictably across Gmail, Apple Mail, and Outlook. The logo is a
hosted PNG; the text part is the readable fallback.
"""

from __future__ import annotations

_SITE_URL = "https://nikolasproject.com"
_ABOUT_URL = "https://nikolasproject.com/about"
_CONTACT_URL = "https://nikolasproject.com/contact"
_LOGO_URL = "https://nikolasproject.com/email-logo.png"
_BRAND = "Investment Intelligence"
_CONTACT_EMAIL = "contact@nikolasdionsavio.com"

# Palette (matches the site).
_NAVY = "#1e3a5f"
_INK = "#0f172a"
_SECONDARY = "#475569"
_MUTED = "#94a3b8"
_BORDER = "#e6e8ec"
_BG = "#f5f6f8"


def _layout(
    *,
    preheader: str,
    heading: str,
    paragraphs: list[str],
    button_label: str,
    button_url: str,
    note: str | None = None,
    signoff: bool = False,
) -> str:
    """Assemble the full branded HTML email."""
    body = "".join(
        f'<p style="margin:0 0 16px;font-size:15px;line-height:1.65;'
        f'color:{_SECONDARY};">{p}</p>'
        for p in paragraphs
    )
    note_html = (
        f'<p style="margin:20px 0 0;font-size:13px;line-height:1.6;'
        f'color:{_MUTED};">{note}</p>'
        if note
        else ""
    )
    signoff_html = (
        f'<p style="margin:24px 0 0;font-size:15px;color:{_SECONDARY};">Thanks again,</p>'
        f'<p style="margin:2px 0 0;font-family:Georgia,\'Times New Roman\',serif;'
        f'font-size:18px;color:{_INK};">Nikolas</p>'
        f'<p style="margin:2px 0 0;font-size:13px;color:{_MUTED};">'
        f'Nikolas Dion Savio, Investment Intelligence</p>'
        if signoff
        else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_BRAND}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};">
<span style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_BG};">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background:#ffffff;border:1px solid {_BORDER};border-radius:14px;overflow:hidden;">
        <tr><td style="height:4px;background:{_NAVY};line-height:4px;font-size:0;">&nbsp;</td></tr>
        <tr>
          <td style="padding:28px 32px 0;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="padding-right:12px;vertical-align:middle;">
                  <img src="{_LOGO_URL}" width="44" height="44" alt="{_BRAND}" style="display:block;border-radius:10px;">
                </td>
                <td style="vertical-align:middle;">
                  <div style="font-family:Georgia,'Times New Roman',serif;font-size:18px;font-weight:600;color:{_INK};line-height:1.2;">{_BRAND}</div>
                  <div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:{_MUTED};line-height:1.3;">Public company analysis</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr><td style="padding:24px 32px 0;"><div style="border-top:1px solid {_BORDER};font-size:0;line-height:0;">&nbsp;</div></td></tr>
        <tr>
          <td style="padding:24px 32px 8px;font-family:Arial,Helvetica,sans-serif;">
            <h1 style="margin:0 0 16px;font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:600;color:{_INK};line-height:1.3;">{heading}</h1>
            {body}
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 4px;">
              <tr><td style="border-radius:8px;background:{_NAVY};">
                <a href="{button_url}" style="display:inline-block;padding:12px 22px;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;border-radius:8px;">{button_label}&nbsp;&rarr;</a>
              </td></tr>
            </table>
            {note_html}
            {signoff_html}
          </td>
        </tr>
        <tr><td style="padding:24px 32px 0;"><div style="border-top:1px solid {_BORDER};font-size:0;line-height:0;">&nbsp;</div></td></tr>
        <tr>
          <td style="padding:18px 32px 28px;font-family:Arial,Helvetica,sans-serif;">
            <p style="margin:0 0 10px;font-size:13px;color:{_SECONDARY};">
              <a href="{_SITE_URL}" style="color:{_NAVY};text-decoration:none;font-weight:bold;">Open the app</a>
              &nbsp;&middot;&nbsp;
              <a href="{_ABOUT_URL}" style="color:{_NAVY};text-decoration:none;font-weight:bold;">About</a>
              &nbsp;&middot;&nbsp;
              <a href="{_CONTACT_URL}" style="color:{_NAVY};text-decoration:none;font-weight:bold;">Contact</a>
            </p>
            <p style="margin:0 0 4px;font-size:12px;line-height:1.6;color:{_MUTED};">
              {_BRAND} is a screening tool for educational and research purposes. It is not investment advice.
            </p>
            <p style="margin:0;font-size:12px;color:{_MUTED};">
              Questions? Reply to this email or write to
              <a href="mailto:{_CONTACT_EMAIL}" style="color:{_MUTED};">{_CONTACT_EMAIL}</a>.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def welcome_email(to: str) -> tuple[str, str, str]:
    """Welcome / registration confirmation email."""
    subject = "Thanks for joining Investment Intelligence"
    paragraphs = [
        "I'm Nikolas, the person behind Investment Intelligence. Thank you for "
        "signing up and giving it a try. It genuinely means a lot to me.",
        "You can save companies to a watchlist now and keep your screens in one "
        "place. Search any US-listed company and you'll get its dashboard, the "
        "KPIs with their formulas, the filed statements, valuation multiples, a "
        "five-year LBO model with sensitivities, peer comparables, a deal score, "
        "and a memo built from the figures on the page.",
        "If something looks off or you have an idea, just reply to this email. It "
        "comes straight to me and I read everything.",
    ]
    html = _layout(
        preheader="A quick thank you from Nikolas. Your account is ready to use.",
        heading="Thanks for joining",
        paragraphs=paragraphs,
        button_label="Start screening",
        button_url=_SITE_URL,
        signoff=True,
    )
    text = (
        "Thanks for joining Investment Intelligence\n\n"
        "I'm Nikolas, the person behind Investment Intelligence. Thank you for "
        "signing up and giving it a try. It genuinely means a lot to me.\n\n"
        "You can save companies to a watchlist now and keep your screens in one "
        "place. Search any US-listed company and you'll get its dashboard, the "
        "KPIs with their formulas, the filed statements, valuation multiples, a "
        "five-year LBO model with sensitivities, peer comparables, a deal score, "
        "and a memo built from the figures on the page.\n\n"
        "If something looks off or you have an idea, just reply to this email. It "
        "comes straight to me and I read everything.\n\n"
        f"Start screening: {_SITE_URL}\n\n"
        "Thanks again,\nNikolas\nNikolas Dion Savio, Investment Intelligence\n\n"
        f"About: {_ABOUT_URL} · Contact: {_CONTACT_EMAIL}\n"
        f"{_BRAND} is a screening tool for educational and research purposes. "
        "It is not investment advice."
    )
    return subject, html, text


def password_reset_email(to: str, reset_url: str) -> tuple[str, str, str]:
    """Password-reset email containing the one-time reset link."""
    subject = "Reset your Investment Intelligence password"
    paragraphs = [
        "We received a request to reset the password for your Investment "
        "Intelligence account. Click the button below to choose a new one.",
    ]
    html = _layout(
        preheader="Reset your password. This link expires in one hour.",
        heading="Reset your password",
        paragraphs=paragraphs,
        button_label="Reset password",
        button_url=reset_url,
        note=(
            "This link expires in one hour. If you did not request a reset, you "
            "can safely ignore this email and your password will stay the same."
        ),
    )
    text = (
        "Reset your Investment Intelligence password\n\n"
        "We received a request to reset your password. Open the link below to "
        "choose a new one:\n\n"
        f"{reset_url}\n\n"
        "This link expires in one hour. If you did not request this, you can "
        "safely ignore this email and your password will stay the same.\n\n"
        f"{_BRAND}\n{_CONTACT_EMAIL}"
    )
    return subject, html, text
