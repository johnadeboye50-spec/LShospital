from datetime import datetime
import secrets
import os
import smtplib
from email.message import EmailMessage
from flask import url_for
from pkg import app


def generate_email_token():
    """Generate a secure random token for email verification or reset links."""
    return secrets.token_urlsafe(32)


def send_email(to_email, subject, body):
    """Send a plain-text email via SMTP."""
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("SMTP_FROM") or user
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    if not host or not user or not password or not sender:
        app.logger.warning("SMTP not configured. Email not sent.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        app.logger.error(f"Email send failed: {exc}")
        return False


def send_verification_message(to_email, verify_link, expiry_hours=24):
    """Send a verification email with a confirmation link."""
    body = (
        "Welcome to LS Hospital.\n\n"
        "Please verify your email address by clicking the link below:\n"
        f"{verify_link}\n\n"
        f"This link expires in {expiry_hours} hours."
    )
    return send_email(to_email, "Verify your email", body)


def send_password_reset_message(to_email, reset_link, expiry_hours=1):
    """Send a password reset email with a reset link."""
    body = (
        "You requested a password reset for your LS Hospital account.\n\n"
        "Click the link below to reset your password:\n"
        f"{reset_link}\n\n"
        f"This link expires in {expiry_hours} hour(s).\n\n"
        "If you didn't request this, ignore this email.\n"
        "Your password will remain unchanged."
    )
    return send_email(to_email, "Reset your password", body)
