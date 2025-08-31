# hopeland_bot/emailer.py
import os
import smtplib
import logging
from email.message import EmailMessage
from typing import List

SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("EMAIL_USERNAME", "")
SMTP_PASS = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", SMTP_USER)
OWNERS_EMAILS = [e.strip() for e in os.environ.get("OWNERS_EMAILS", "").split(",") if e.strip()]

def _smtp_ok() -> bool:
    return all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, OWNERS_EMAILS])

def send_email(subject: str, text: str, html: str = "") -> bool:
    if not _smtp_ok():
        logging.warning("SMTP not configured; skip email.")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(OWNERS_EMAILS)
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        logging.exception("Email send failed: %s", e)
        return False
