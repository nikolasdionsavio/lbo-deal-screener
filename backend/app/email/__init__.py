"""Transactional email: config-gated SMTP sender + plain-copy templates.

With no SMTP configuration ``send_email`` skips sending and returns False, so
the app behaves exactly as before email was added (see ``sender``).
"""

from app.email.sender import send_email
from app.email.templates import password_reset_email, welcome_email

__all__ = ["send_email", "welcome_email", "password_reset_email"]
