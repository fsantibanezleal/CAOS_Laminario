"""The optional mail sender.

Mail is not a prerequisite: invitations and password-reset links work by copying a link. When a sender is
configured (``LAMINARIO_SMTP_HOST`` and ``LAMINARIO_SMTP_SENDER``, credentials from the vault), links are mailed
over SMTP with STARTTLS; the production host can reach port 587 and not 25 or 465 (finding F-013).
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.config import Settings

PRODUCT = "Laminario"


def compose(settings: Settings, to: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.smtp_sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    return message


def send(settings: Settings, message: EmailMessage) -> None:
    """Send one message through the configured server (blocking; call from a worker thread)."""
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls:
            cafile = str(settings.smtp_cafile) if settings.smtp_cafile else None
            smtp.starttls(context=ssl.create_default_context(cafile=cafile))
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)


def invitation_message(settings: Settings, to: str, link: str, role: str, days: int) -> EmailMessage:
    body = (f"You are invited to join {PRODUCT}, an open collection of microscope slides, as a {role}.\n\n"
            f"Create your account here (the link works once, for {days} days):\n\n{link}\n\n"
            f"If you did not expect this, ignore it; nothing happens without the link.\n")
    return compose(settings, to, f"Your invitation to {PRODUCT}", body)


def reset_message(settings: Settings, to: str, link: str, minutes: int) -> EmailMessage:
    body = (f"Someone asked to reset the password of your {PRODUCT} account.\n\n"
            f"Choose a new password here (the link works for {minutes} minutes):\n\n{link}\n\n"
            f"If it was not you, ignore this message; your password has not changed.\n")
    return compose(settings, to, f"Reset your {PRODUCT} password", body)
