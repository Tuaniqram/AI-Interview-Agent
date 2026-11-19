"""Tokens in a WebSocket URL must not reach the server's log output."""
import io
import logging

import pytest

from app.utils.log_redaction import REDACTED, UrlSecretFilter, install_url_secret_redaction, redact


def test_query_secrets_are_redacted_and_other_params_kept():
    url = "/ws/interview/abc?token=eyJhbGciOi.payload.sig&access=eyJxyz.a.b&lang=en"
    out = redact(url)
    assert "eyJ" not in out
    assert out == f"/ws/interview/abc?token={REDACTED}&access={REDACTED}&lang=en"


def test_text_without_secrets_is_unchanged():
    assert redact("GET /api/v1/health 200") == "GET /api/v1/health 200"
    assert redact("a path with token in words, no equals") == "a path with token in words, no equals"


@pytest.mark.parametrize("name", ["uvicorn.access", "uvicorn.error"])
def test_uvicorn_style_records_are_rewritten_before_formatting(name):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    log = logging.getLogger(name + ".redaction-test")  # isolated child: attach the filter directly
    log.propagate = False
    log.addHandler(handler)
    log.addFilter(UrlSecretFilter())
    log.warning('%s - "WebSocket %s" [accepted]', "127.0.0.1:5000", "/ws/interview/s1?access=SECRETVALUE&x=1")
    log.warning("plain %s", "/ws/interview/s1?token=SECRETTOKEN")
    text = stream.getvalue()
    assert "SECRETVALUE" not in text and "SECRETTOKEN" not in text
    assert f"access={REDACTED}" in text and "x=1" in text


def test_install_is_idempotent_and_covers_uvicorn_loggers():
    install_url_secret_redaction()
    install_url_secret_redaction()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        assert sum(isinstance(f, UrlSecretFilter) for f in logging.getLogger(name).filters) == 1
