"""Keep credentials that travel in URL query strings out of the server's own logs.

The interview WebSocket authenticates with ``?token=`` (candidate login) and ``?access=`` (per-session token), and
uvicorn writes the full URL, query string included, to its access log. Anyone who can read those logs could replay
a token while it is valid. The filter rewrites the values before the record is formatted.
"""
import logging
import re

_SECRET_PARAM = re.compile(r"([?&](?:token|access|access_token)=)[^&\s\"']+", re.IGNORECASE)
REDACTED = "[REDACTED]"
_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")


def redact(text: str) -> str:
    return _SECRET_PARAM.sub(lambda m: m.group(1) + REDACTED, text)


class UrlSecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
        return True


def install_url_secret_redaction() -> None:
    """Attach the filter to uvicorn's loggers (once)."""
    for name in _LOGGERS:
        log = logging.getLogger(name)
        if not any(isinstance(f, UrlSecretFilter) for f in log.filters):
            log.addFilter(UrlSecretFilter())
