"""Contract tests for the DSPy pilot module (app/intelligence/dspy_modules.py).

The live end-to-end test is marked ``llm`` (excluded from default runs, like
the rest of the LLM-dependent suite) and self-skips when the local gateway is
unreachable. Everything else runs in the default suite.
"""
import pytest

import app.intelligence.dspy_modules as dspy_modules
from app.intelligence.dspy_modules import ResumeAnalysis, ResumeAnalyzerProgram


def test_resume_analysis_signature_has_typed_fields():
    sig = ResumeAnalysis
    for field in ("full_name", "headline"):
        assert field in sig.fields
        assert sig.fields[field].annotation is str
    for field in ("skills", "strengths", "weaknesses", "experience", "education"):
        assert field in sig.fields
        assert sig.fields[field].annotation == list[str]
    assert "years_of_experience" in sig.fields
    assert sig.fields["years_of_experience"].annotation in (int, int | None)


def test_resume_analyzer_program_is_async():
    program = ResumeAnalyzerProgram()
    assert hasattr(program, "aforward")
    assert hasattr(program, "forward")


async def _gateway_up() -> bool:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{dspy_modules.LOCAL_BASE_URL}/models")
            return response.status_code == 200
    except Exception:
        return False


@pytest.mark.llm
async def test_run_resume_analysis_live_typed_shape():
    if not await _gateway_up():
        pytest.skip("local gateway unreachable — DSPy live test skipped")
    data = await dspy_modules.run_resume_analysis(
        "Jordan Rivera\nSenior Python Developer - FastAPI, PostgreSQL, Docker\n8+ years experience.",
        "Senior Python Developer",
    )
    assert set(data) == {
        "full_name", "headline", "skills", "strengths", "weaknesses",
        "experience", "education", "years_of_experience",
    }
    assert isinstance(data["skills"], list)
    assert isinstance(data["strengths"], list)
    assert isinstance(data["weaknesses"], list)
    assert isinstance(data["experience"], list)
    assert isinstance(data["education"], list)
    assert data["years_of_experience"] is None or isinstance(data["years_of_experience"], int)
    assert data["full_name"]
