import logging
from pathlib import Path
from string import Template

import resend

from app.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "emails" / "templates"

_email_enabled: bool | None = None


def _check_enabled() -> bool:
    global _email_enabled
    if _email_enabled is not None:
        return _email_enabled
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — emails disabled")
        _email_enabled = False
        return False
    resend.api_key = settings.RESEND_API_KEY
    _email_enabled = True
    return True


def _render(template_name: str, **kwargs) -> str:
    path = TEMPLATES_DIR / template_name
    if not path.exists():
        raise FileNotFoundError(f"Email template not found: {path}")
    tpl = Template(path.read_text(encoding="utf-8"))
    return tpl.safe_substitute(**kwargs)


async def send_email(
    to: str,
    subject: str,
    template_name: str,
    **template_vars,
) -> bool:
    if not _check_enabled():
        logger.info(f"[EMAIL DISABLED] Would send to={to} subject={subject!r}")
        return False
    try:
        html = _render(template_name, **template_vars)
        params: resend.Emails.SendParams = {
            "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_ADDRESS}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }
        response = resend.Emails.send(params)
        logger.info("Email sent to %s — id=%s", to, response.get("id"))
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False
