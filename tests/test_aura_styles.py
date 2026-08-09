"""AURA single-style contract: one conductor, legacy names resolve to AURA."""
from app.config.interview_styles import (
    DEFAULT_STYLE,
    STYLES,
    get_persona,
    get_style,
    list_styles,
)


def test_default_style_is_aura():
    assert DEFAULT_STYLE == "AURA"


def test_get_style_none_returns_aura():
    style = get_style()
    assert style["name"] == "AURA Interview"
    assert style["persona"] == "conductor"
    assert style["difficulty_range"] == (1, 5)
    assert style["max_questions"] == 14
    assert style["evaluator_mode"] == "unified"


def test_get_style_standard_maps_to_aura():
    assert get_style("STANDARD")["name"] == "AURA Interview"


def test_get_style_unknown_maps_to_aura():
    assert get_style("BOGUS_STYLE")["name"] == "AURA Interview"


def test_get_style_is_case_insensitive():
    assert get_style("aura")["name"] == "AURA Interview"


def test_get_persona_returns_conductor():
    assert get_persona() == "conductor"
    assert get_persona("STANDARD") == "conductor"


def test_list_styles_returns_only_aura():
    styles = list_styles()
    assert len(styles) == 1
    assert styles[0]["name"] == "AURA"
    assert styles[0]["persona"] == "conductor"
    assert styles[0]["max_questions"] == 14


def test_legacy_styles_kept_in_config():
    """Old styles stay in STYLES so legacy routes/tests that reference them work."""
    assert "JUNIOR" in STYLES
    assert "FAANG" in STYLES
    assert "STANDARD" in STYLES
