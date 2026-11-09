"""Summary endpoint: engine extras must come from the durable
``interview_brain`` snapshot (DB), not the in-memory session store, so the
post-interview report survives restarts/evictions."""
from uuid import uuid4

import pytest

from app.api.interview_agent import _get_engine_summary, _get_legacy_summary
from app.models.db import InterviewBrain as InterviewBrainRecord

_FACTORY_SEAM = "app.api.interview_agent.get_session_factory"
_REPO_SEAM = "app.api.interview_agent.get_session_repo"
_MESSAGE_SEAM = "app.api.interview_agent.get_message_repo"
_EVAL_SEAM = "app.api.interview_agent.get_evaluation_repo"


class _ScalarResult:
    def __init__(self, row=None):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class FakeDB:
    def __init__(self, record=None):
        self.record = record

    async def execute(self, statement):
        return _ScalarResult(self.record)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _record(**overrides) -> InterviewBrainRecord:
    rec = InterviewBrainRecord(
        session_id=uuid4(),
        version=3,
        current_hypotheses=[
            {"status": "confirmed"},
            {"status": "refuted"},
            {"status": "testing"},
            {"status": "untested"},
        ],
        evidence_summary={
            "tech_core": {"evidence_count": 4, "average_score": 7.5, "gap": 0.1},
        },
        decision_state={
            "hiring_recommendation": {
                "verdict": "hire",
                "confidence": 0.7,
                "composite_score": 7.2,
            },
        },
        brain_metadata={"question_number": 6},
    )
    for k, v in overrides.items():
        setattr(rec, k, v)
    return rec


async def test_engine_summary_reads_brain_snapshot(monkeypatch):
    sid = str(uuid4())
    monkeypatch.setattr(_FACTORY_SEAM, lambda: lambda: FakeDB(_record()))

    data = await _get_engine_summary(sid)

    assert data["session_id"] == sid
    assert data["v4_verdict"] == "hire"
    assert data["v4_confidence"] == 0.7
    assert data["v4_composite_score"] == 7.2
    assert data["v4_evidence_count"] == 4
    assert data["v4_questions_asked"] == 6
    assert data["v4_competency_summary"]["tech_core"] == {
        "average_score": 7.5,
        "evidence_count": 4,
        "gap": 0.1,
    }
    assert data["v4_hypothesis_outcomes"] == {
        "confirmed": 1,
        "refuted": 1,
        "testing": 1,
        "untested": 1,
    }


async def test_engine_summary_empty_without_snapshot(monkeypatch):
    monkeypatch.setattr(_FACTORY_SEAM, lambda: lambda: FakeDB(None))

    assert await _get_engine_summary("session-1") == {}


async def test_engine_summary_degrades_on_db_error(monkeypatch):
    class BoomDB:
        async def execute(self, statement):
            raise RuntimeError("db down")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(_FACTORY_SEAM, lambda: BoomDB)

    assert await _get_engine_summary("session-1") == {}


def _fake_repo(session: dict) -> object:
    class _Repo:
        def __init__(self):
            self._session = session

        async def get_session(self, session_id):
            return self._session

        async def get_session_messages(self, session_id):
            return []

        async def get_evaluations(self, session_id):
            return []

    return _Repo()


@pytest.mark.asyncio
async def test_legacy_summary_survives_none_total_questions(monkeypatch):
    """V5 sessions have total_questions=NULL in the DB — the legacy summary
    must not 500 on the None comparison (regression: live demo run crashed
    with TypeError: '>' not supported between instances of 'NoneType' and 'int')."""
    sid = str(uuid4())
    session = {
        "session_id": sid,
        "total_questions": None,  # V5 sessions leave this NULL
        "status": "completed",
        "job_role": "Senior Frontend Engineer",
    }
    monkeypatch.setattr(_REPO_SEAM, lambda: _fake_repo(session))
    monkeypatch.setattr(_MESSAGE_SEAM, lambda: _fake_repo(session))
    monkeypatch.setattr(_EVAL_SEAM, lambda: _fake_repo(session))

    data = await _get_legacy_summary(sid)

    assert data["session_id"] == sid
    assert data["total_questions"] == 14  # falls back to the engine's question cap
    assert data["answered_ratio"] == 0.0  # 0 answered / 14 possible, no crash


# ---- who may read a session's summary -------------------------------------------------------------

from types import SimpleNamespace

from fastapi import HTTPException

from app.api.interview_agent import _verify_session_access


class _SeqDB:
    """execute() returns the queued results in order (session row first, then the org-owner lookup)."""

    def __init__(self, *rows):
        self._rows = list(rows)

    async def execute(self, statement):
        return _ScalarResult(self._rows.pop(0) if self._rows else None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _sess(**kw):
    base = dict(id=uuid4(), org_id=uuid4(), candidate_profile_id=uuid4())
    base.update(kw)
    return SimpleNamespace(**base)


def _factory(db):
    return lambda: (lambda: db)


@pytest.mark.asyncio
async def test_org_owner_can_read_a_candidate_interview_summary(monkeypatch):
    session = _sess()
    monkeypatch.setattr(_FACTORY_SEAM, _factory(_SeqDB(session, uuid4())))  # second row: the org-owner lookup hit
    user = SimpleNamespace(id=uuid4(), is_admin=False)
    assert await _verify_session_access(str(session.id), None, user) is session


@pytest.mark.asyncio
async def test_other_users_still_need_to_own_the_session(monkeypatch):
    session = _sess()
    monkeypatch.setattr(_FACTORY_SEAM, _factory(_SeqDB(session, None)))  # not the org owner
    user = SimpleNamespace(id=uuid4(), is_admin=False)
    with pytest.raises(HTTPException) as e:
        await _verify_session_access(str(session.id), None, user)
    assert e.value.status_code == 401  # a candidate login is still required


@pytest.mark.asyncio
async def test_admin_can_read_any_summary(monkeypatch):
    session = _sess()
    monkeypatch.setattr(_FACTORY_SEAM, _factory(_SeqDB(session)))
    assert await _verify_session_access(str(session.id), None, SimpleNamespace(id=uuid4(), is_admin=True)) is session


@pytest.mark.asyncio
async def test_candidate_access_is_unchanged(monkeypatch):
    mine = SimpleNamespace(id=uuid4())
    session = _sess(candidate_profile_id=mine.id)
    monkeypatch.setattr(_FACTORY_SEAM, _factory(_SeqDB(session)))
    assert await _verify_session_access(str(session.id), mine) is session
    monkeypatch.setattr(_FACTORY_SEAM, _factory(_SeqDB(session)))
    with pytest.raises(HTTPException) as e:
        await _verify_session_access(str(session.id), SimpleNamespace(id=uuid4()))
    assert e.value.status_code == 403


from app.api.interview_agent import split_feedback_items


def test_new_rows_split_on_lines_and_keep_inner_commas():
    assert split_feedback_items("Uses caching, with a TTL\nNames the trade-off") == [
        "Uses caching, with a TTL", "Names the trade-off"]


def test_old_comma_joined_rows_are_not_cut_inside_brackets():
    assert split_feedback_items("Applies concrete fixes (index, cache), Considers edge cases (expiry, stampedes)") == [
        "Applies concrete fixes (index, cache)", "Considers edge cases (expiry, stampedes)"]


def test_empty_feedback_gives_no_items():
    assert split_feedback_items(None) == [] and split_feedback_items("") == [] and split_feedback_items(" , ") == []


@pytest.mark.asyncio
async def test_summary_total_falls_back_to_the_engine_cap_and_never_below_answered(monkeypatch):
    class _Repo:
        def __init__(self, session, messages):
            self._s, self._m = session, messages

        async def get_session(self, sid):
            return self._s

        async def get_session_messages(self, sid):
            return self._m

    class _Evals:
        async def get_evaluations_by_session(self, sid):
            return []

        async def get_evaluations(self, sid):
            return []

    answers = [{"role": "user"}] * 13
    monkeypatch.setattr(_REPO_SEAM, lambda: _Repo({"total_questions": None, "final_score": 4.0}, answers))
    monkeypatch.setattr(_MESSAGE_SEAM, lambda: _MsgRepo(answers))
    monkeypatch.setattr(_EVAL_SEAM, lambda: _Evals())
    out = await _get_legacy_summary(str(uuid4()))
    assert out["total_questions"] >= 13  # was 10 for an organization interview: "13 / 10"

    few = [{"role": "user"}] * 30
    monkeypatch.setattr(_MESSAGE_SEAM, lambda: _MsgRepo(few))
    assert (await _get_legacy_summary(str(uuid4())))["total_questions"] >= 30


class _MsgRepo:
    def __init__(self, messages):
        self._m = messages

    async def get_session_messages(self, sid):
        return self._m

    async def get_evaluations(self, sid):
        return []


from app.api.interview_agent import top_feedback_items


def test_top_feedback_items_rank_by_frequency_and_cap():
    items = ["Clear steps", "Names trade-offs", "clear steps.", "Uses tests", "Clear Steps", "Names trade-offs", "Other"]
    assert top_feedback_items(items, limit=3) == ["Clear steps.", "Names trade-offs.", "Uses tests."]  # "Other" is one word: dropped


def test_top_feedback_items_ignore_blanks_and_keep_a_stable_order():
    assert top_feedback_items(["", " ", "bb cc", "aa dd"]) == ["Bb cc.", "Aa dd."]
    assert top_feedback_items([]) == []


from app.api.interview_agent import build_final_decision


def test_final_decision_carries_the_verdict_and_why_it_was_lowered():
    hd = {
        "decision": "lean_no_hire", "draft_decision": "hire", "decision_score": 5.4, "confidence": 0.61,
        "flag_review": True, "rationale": "deterministic text",
        "llm_draft": {"rationale": "Answers contradicted each other."},
        "adjustments": [
            {"rule": "claim_conflict", "from": "hire", "to": "lean_no_hire", "reason": "2 figures changed", "extra": 1},
            {"rule": "noise", "reason": None},  # no reason: not shown
        ],
        "next_steps": ["archive candidate profile"],
    }
    out = build_final_decision(hd, [{"a": 1}, {"b": 2}])
    assert out["verdict"] == "lean_no_hire" and out["draft_verdict"] == "hire" and out["score"] == 5.4
    assert out["rationale"] == "Answers contradicted each other."  # the readable draft wins over the fallback text
    assert out["adjustments"] == [{"rule": "claim_conflict", "from": "hire", "to": "lean_no_hire", "reason": "2 figures changed"}]
    assert out["flag_review"] is True and out["contradiction_count"] == 2
    assert out["next_steps"] == ["archive candidate profile"]


def test_final_decision_is_none_without_a_decision():
    assert build_final_decision(None) is None
    assert build_final_decision({}) is None
    assert build_final_decision({"decision": ""}) is None


from app.api.interview_agent import _with_feedback_items, tidy_feedback_item


def test_tidy_feedback_item_makes_readable_sentences_and_drops_fragments():
    assert tidy_feedback_item("  concise description of migration steps ") == "Concise description of migration steps."
    assert tidy_feedback_item("Already a sentence.") == "Already a sentence."
    for fragment in ("sources", "or fix", "and monitoring", "cache)", "", None):
        assert tidy_feedback_item(fragment) is None


def test_ranking_ignores_fragments():
    assert top_feedback_items(["or fix", "diagnosis", "Names the trade-off", "names the trade-off."]) == ["Names the trade-off."]


def test_evaluation_gets_clean_per_answer_lists():
    ev = _with_feedback_items({"id": 1, "strengths": "Clear steps\nsources", "weaknesses": "No rollback plan, or fix"})
    assert ev["strengths_items"] == ["Clear steps."]
    assert ev["weaknesses_items"] == ["No rollback plan."]
    assert ev["strengths"] == "Clear steps\nsources"  # the stored text is left untouched


from app.api.v1.system import llm_provider_status


def test_llm_provider_list_follows_the_live_chain():
    configs = [
        {"model": "openai/gpt-oss-120b", "base_url": "https://openrouter.ai/api/v1", "api_key": "k"},
        {"model": "openai/gpt-oss-120b", "base_url": "https://api.groq.com/openai/v1", "api_key": None},
        {"model": "one", "base_url": "http://localhost:20128/v1", "api_key": None},
    ]
    assert llm_provider_status(configs) == [
        {"name": "OpenRouter (openai/gpt-oss-120b)", "configured": True},
        {"name": "Groq (openai/gpt-oss-120b)", "configured": False},  # no key: not usable
        {"name": "Local router (one)", "configured": True},          # a local router needs none
    ]


from app.api.interview_agent import build_evidence_items


def test_evidence_items_keep_what_the_report_needs_and_drop_unusable_rows():
    rows = [
        {"question_number": 2, "competency_id": "tech_core", "dimension": "technical", "score": 7.04, "evidence_text": "  p95 fell   from 900ms\nto 180ms "},
        {"question_number": None, "competency_id": "tech_core", "evidence_text": "no question"},   # not tied to an answer
        {"question_number": 3, "competency_id": "tech_core", "evidence_text": ""},                    # nothing to show
        {"question_number": 4, "competency_id": "tech_db", "dimension": "x", "score": None, "evidence_text": "q" * 500},
    ]
    out = build_evidence_items(rows)
    assert out[0] == {"question_number": 2, "competency": "tech_core", "dimension": "technical", "score": 7.0, "quote": "p95 fell from 900ms to 180ms"}
    assert len(out) == 2 and out[1]["score"] is None and len(out[1]["quote"]) == 400
    assert build_evidence_items([]) == [] and build_evidence_items(None) == []
