"""
Email sending abstraction.

v1: synchronous via resend.Emails.send().
To convert to async (arq worker), modify ONLY this module.
"""
import resend
from config import config

resend.api_key = config.RESEND_API_KEY


def send_email(to: str, subject: str, html: str) -> None:
    """
    Send a transactional email via Resend.

    Raises whatever Resend raises. Caller decides whether to retry/log.
    """
    resend.Emails.send({
        "from": config.FROM_EMAIL,
        "to": to,
        "subject": subject,
        "html": html,
    })
