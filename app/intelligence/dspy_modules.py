"""DSPy modules for AURA intelligence enrichment.

Pilot scope: resume analysis only. DSPy enriches; every deterministic
fallback stays in the callers.

Security (CVE-2025-69872): DSPy's default on-disk cache uses unrestricted
pickle. We ALWAYS call ``dspy.configure_cache(restrict_pickle=True)`` before
the first LM call — DSPy then deserializes with an allowlist (litellm.types.*,
openai.types.*, numpy helpers; see ``dspy/clients/disk_serialization.py``).
Litellm is used client-only; the proxy and ``PythonInterpreter`` are out of
scope.
"""
import logging
import os

import dspy

from app.intelligence._helpers import dedupe

logger = logging.getLogger(__name__)

# Local OpenAI-compatible gateway — same convention as app/models/llm.py.
# "one"/"coder"/"fallback"/"nvidia" aliases have been flaky; "openrouter"
# reliably routes to the working NVIDIA backend. Override via env if needed.
LOCAL_BASE_URL = os.getenv("DSPY_BASE_URL", "http://localhost:20128/v1")
LOCAL_MODEL = os.getenv("DSPY_MODEL", "openrouter")
LOCAL_API_KEY = "sk-no-key"

_configured = False


def _ensure_configured() -> None:
    """Idempotent one-time setup: restricted-pickle cache + local LM."""
    global _configured
    if _configured:
        return
    dspy.configure_cache(restrict_pickle=True)
    dspy.settings.configure(
        lm=dspy.LM(
            f"openai/{LOCAL_MODEL}",
            api_base=LOCAL_BASE_URL,
            api_key=LOCAL_API_KEY,
        ),
    )
    _configured = True


class ResumeAnalysis(dspy.Signature):
    """Extract structured candidate-brain fields from a resume.

    Be conservative: only list what the resume actually states; empty lists
    are fine; coerce years_of_experience to the first integer found."""

    resume_text: str = dspy.InputField(desc="Raw resume text")
    job_role: str = dspy.InputField(desc="Target job role")
    full_name: str = dspy.OutputField(desc="Candidate full name")
    headline: str = dspy.OutputField(desc="One-line professional summary")
    skills: list[str] = dspy.OutputField(desc="Technical skills and technologies")
    strengths: list[str] = dspy.OutputField(desc="Stated strengths, max 5")
    weaknesses: list[str] = dspy.OutputField(desc="Gaps or missing role keywords")
    experience: list[str] = dspy.OutputField(desc="Role + duration one-liners")
    education: list[str] = dspy.OutputField(desc="Institution, degree, year")
    years_of_experience: int | None = dspy.OutputField(desc="Years of experience as an int")


class ResumeAnalyzerProgram(dspy.Module):
    """Typed resume-analysis program; async via ``aforward``."""

    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(ResumeAnalysis)

    def forward(self, resume_text: str, job_role: str) -> dspy.Prediction:
        return self.predict(resume_text=resume_text, job_role=job_role)

    async def aforward(self, resume_text: str, job_role: str) -> dspy.Prediction:
        return await self.predict.acall(resume_text=resume_text, job_role=job_role)


_program: ResumeAnalyzerProgram | None = None


def _get_program() -> ResumeAnalyzerProgram:
    global _program
    if _program is None:
        _ensure_configured()
        _program = ResumeAnalyzerProgram()
    return _program


async def run_resume_analysis(resume_text: str, job_role: str) -> dict:
    """DSPy enrichment branch for ``analyze_resume``.

    Returns a dict shaped like the old ``parse_llm_json_with_retry`` output
    (full_name/headline/skills/strengths/weaknesses/experience/education/
    years_of_experience). Raises on failure — callers fall back to
    heuristics.
    """
    prediction = await _get_program().aforward(
        resume_text=(resume_text or "")[:8000],
        job_role=job_role or "",
    )
    return {
        "full_name": prediction.full_name or "",
        "headline": prediction.headline or "",
        "skills": dedupe(prediction.skills),
        "strengths": dedupe(prediction.strengths),
        "weaknesses": dedupe(prediction.weaknesses),
        "experience": dedupe(prediction.experience),
        "education": dedupe(prediction.education),
        "years_of_experience": prediction.years_of_experience,
    }
