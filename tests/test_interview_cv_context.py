"""CV-aware interviews: the CV brief, its use in the question prompt, and the fix that stops a
candidate who admits a gap from being pressure-tested as a boasting senior."""
from app.agents.generation.question_generator import _cv_context, _question_prompt_vars
from app.brain.contradiction_detector import seniority_claim_risk
from app.intelligence.cv_brief import build_cv_brief
from app.services.prompt_loader import load_prompt

BRAIN = {
    "headline": "Backend Developer",
    "years_of_experience": 5,
    "experience": [
        "Fintech payments (3 yrs): built the ledger service in FastAPI/PostgreSQL, idempotent Celery settlement jobs",
        "E-commerce startup (2 yrs): order API, Redis caching, read replicas",
    ],
    "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Celery"],
}


# --- build_cv_brief ---------------------------------------------------------------------------


def test_brief_lists_experience_skills_and_probes():
    brief = build_cv_brief(BRAIN, fit={"recommended_probes": ["How did you make settlement idempotent?"]})
    assert "ledger service" in brief
    assert "Skills: Python, FastAPI" in brief
    assert "~5 yrs" in brief
    assert "Worth probing: How did you make settlement idempotent?" in brief


def test_brief_falls_back_to_a_cv_excerpt_when_there_is_no_analysis():
    brief = build_cv_brief({}, resume_text="Rahul Verma\nDjango intern\nLibrary management site")
    assert brief.startswith("CV excerpt: Rahul Verma Django intern")


def test_brief_is_empty_without_any_cv_data_and_is_capped():
    assert build_cv_brief(None, None, None) == ""
    long_brain = {"experience": ["x" * 400] * 10, "skills": ["s"] * 50}
    assert len(build_cv_brief(long_brain)) <= 900


# --- question prompt --------------------------------------------------------------------------


def test_cv_only_opens_or_verifies_an_area():
    state = {"candidate_brain": BRAIN}
    assert "ledger service" in _cv_context(state, "EXPLORER")
    assert "ledger service" in _cv_context(state, "VERIFIER")
    assert _cv_context(state, "PROBER") == "None"
    assert _cv_context(state, "CHALLENGER") == "None"
    assert _cv_context({}, "EXPLORER") == "None"


def test_prompt_renders_the_cv_and_keeps_it_private():
    variables = _question_prompt_vars(
        job_role="Backend Developer", target_competency="tech_db", phase="technical", difficulty=2,
        persona="conductor", hypothesis="", competency_info="", approach="", followup_number=0,
        question_number=0, total_questions=8, conversation_history=[], candidate_profile={},
        cv_brief="Experience: Fintech payments (3 yrs) built the ledger service",
    )
    prompt = load_prompt("interview", "question_generation.md", **variables)
    assert "built the ledger service" in prompt
    assert "{{cv_brief}}" not in prompt
    assert "Never mention the CV analysis" in prompt


# --- seniority risk ---------------------------------------------------------------------------


def _risk(*texts):
    return seniority_claim_risk([{"id": str(i), "evidence_text": t} for i, t in enumerate(texts)], None, None)


def test_hypothetical_and_disclaimer_answers_are_not_seniority_claims():
    risk = _risk(
        "I'd think about scalability and maybe add a load balancer",
        "I haven't done any real design work, I would probably just add more servers",
    )
    assert risk["ownership_claims"] == 0
    assert risk["action"] == "validate"


def test_curly_apostrophes_are_treated_like_straight_ones():
    assert _risk("I’d probably scale it horizontally")["ownership_claims"] == 0


def test_real_past_work_claims_are_still_challenged():
    risk = _risk("I used Kafka in the architecture", "We had microservices with event-driven design")
    assert risk["ownership_claims"] == 2
    assert risk["action"] == "challenge"


def test_a_hedge_next_to_a_real_claim_still_counts():
    risk = _risk("I would do it differently now, but I designed the original scaling approach")
    assert risk["ownership_claims"] == 1
