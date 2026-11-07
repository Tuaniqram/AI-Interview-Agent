"""
WebSocket-based interview protocol (v4 / AURA engine).

Persistent connection replaces HTTP request/response cycle for the interview flow.

Protocol (JSON messages over WebSocket):
  Client → Server: { _id, type, ...data }
  Server → Client: { _id, type, ...data }   (_id echoed so the client can resolve)
  Server → Client (pushes): { type: "status", phase: "evaluating" | "question_ready" }

Message types:
  start_interview  → { type: "question", ...start_response }      (starts/resumes v4 engine)
  request_question → { type: "question", ...current question }     (idempotent resend)
  submit_answer    → { type: "evaluation", ...answer_response } or { type: "report", ... }
  get_status       → { type: "status_snapshot", ...state_response }
  ping             → { type: "pong" }
"""
import asyncio
import json
import logging
import time as time_module
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth.interview_access import verify_interview_access_token
from app.auth.jwt import decode_token
from app.engine.guards import (
    IDLE_TIMEOUT_S,
    MessageRateLimiter,
    SessionLocks,
    clean_message_id,
    parse_frame,
    validate_answer,
    validate_session_id,
)
from app.database.session import get_session_factory
from app.services.event_log import get_event_log
from app.models.db import CandidateProfile, InterviewSession
from app.exceptions import SessionNotFoundException

from app.engine.engine import InterviewEngine
from app.engine.store_io import store_get
from app.engine.builders import build_start_response, build_state_response
from app.config.interview_styles import get_style
from app.data.competency_resolver import (
    default_taxonomy,
    resolve_competencies,
    taxonomy_for_state,
)
from app.intelligence.company_cache import get_or_build_company_brain
from app.services.v4_session_store import get_v4_session_store
from app.services.v5_brain_persister import V5BrainPersister

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview WS"])

# Per-connection state
_connections: dict[str, dict[str, Any]] = {}
_connection_timestamps: dict[str, float] = {}

_cleanup_task = None

# One lock per session: start / answer steps for the same interview never run concurrently
# (two tabs, a double click, a reconnect racing a slow evaluation).
_session_locks = SessionLocks()

# Upper bound for one answer evaluation (LLM chain included); beyond it the client is told to retry.
ANSWER_TIMEOUT_S = 300
START_TIMEOUT_S = 300

def start_cleanup_task():
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(_cleanup_loop())
    return _cleanup_task

async def _cleanup_loop():
    while True:
        await asyncio.sleep(60)
        now = time_module.time()
        stale = [sid for sid, ts in _connection_timestamps.items() if now - ts > 300]
        for sid in stale:
            logger.info(f"Cleaning up stale WS connection: {sid}")
            _connections.pop(sid, None)
            _connection_timestamps.pop(sid, None)


async def _resolve_candidate_from_token(token: Optional[str]) -> Optional[str]:
    """Validate candidate JWT token and return candidate_id string, or None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "candidate_access":
            return None
        return payload.get("sub")
    except ValueError:
        return None


async def _verify_ws_session_access(
    session_id: str, candidate_id: Optional[str], access_session_id: Optional[str] = None
) -> bool:
    """Deny by default. A client may drive a session only if it holds

    * a valid per-session access token for exactly this session (guests: issued with the
      application invitation / public start), or
    * the login token of the candidate who owns the session.

    Previously a connection without any token was allowed into every session, so anyone
    who learned a session id could read the questions and submit answers.
    """
    if access_session_id is not None and access_session_id == session_id:
        return True
    if candidate_id is None:
        return False
    try:
        sid = UUID(session_id)
    except (ValueError, TypeError):
        return False
    async with get_session_factory()() as db:
        result = await db.execute(select(InterviewSession).where(InterviewSession.id == sid))
        session = result.scalar_one_or_none()
    if not session or session.candidate_profile_id is None:
        return False
    return str(session.candidate_profile_id) == str(candidate_id)


def _send_id(message: dict, request: dict) -> dict:
    """Echo the client's _id (when present and sane) so the client can resolve the request."""
    if isinstance(request, dict) and "_id" in request:
        msg_id = clean_message_id(request["_id"])
        if msg_id is not None:
            message["_id"] = msg_id
    return message


async def _load_db_session_row(session_id: str) -> Optional[InterviewSession]:
    """Load the DB session row that anchors the engine state."""
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.id == UUID(session_id))
        )
        return result.scalar_one_or_none()


_v5_persister_instance: Optional[V5BrainPersister] = None


def _get_v5_persister() -> Optional[V5BrainPersister]:
    """Shared V5 persister instance for the WS flow (engine seam)."""
    global _v5_persister_instance
    if _v5_persister_instance is None:
        _v5_persister_instance = V5BrainPersister()
    return _v5_persister_instance


async def _load_candidate_profile_data(
    db_session: InterviewSession,
) -> tuple[dict, Optional[str]]:
    """Best-effort candidate profile dict + resume-ish text for intelligence.

    Falls back to a neutral stub when there is no profile or the lookup fails,
    so a session can always start.
    """
    stub = {"full_name": "Candidate", "headline": "", "strengths": [], "weaknesses": []}
    if not db_session.candidate_profile_id:
        return stub, None
    try:
        async with get_session_factory()() as db:
            result = await db.execute(
                select(CandidateProfile).where(
                    CandidateProfile.id == db_session.candidate_profile_id
                )
            )
            profile = result.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - intelligence is best-effort
        logger.warning(f"Failed to load candidate profile: {exc}")
        profile = None
    if profile is None:
        return stub, None

    data = dict(profile.profile_data or {})
    data.setdefault("full_name", profile.name)
    data.setdefault("headline", "")
    data.setdefault("strengths", [])
    data.setdefault("weaknesses", [])

    parts = [profile.name or "", profile.skills or ""]
    for value in data.values():
        if isinstance(value, str) and value.strip():
            parts.append(value)
        elif isinstance(value, list):
            parts.append(", ".join(str(v) for v in value if v))
    resume_text = "\n".join(p for p in parts if p.strip()) or None
    return data, resume_text


async def _start_v4_engine(session_id: str, notify=None) -> dict:
    """Start (or resume) the v5 AURA engine for the given session.

    The session row in the DB is the source of truth for job_role / department_id;
    the engine state lives in the v4 session store under the same session_id.
    All orchestration is delegated to ``InterviewEngine``.

    ``notify(phase)`` (optional, awaited) reports coarse progress to the client: preparing an
    interview takes a while, and an unexplained spinner looks like a hang.
    """
    async def _progress(phase: str) -> None:
        if notify is not None:
            try:
                await notify(phase)
            except Exception:  # noqa: BLE001 - progress is cosmetic; never fail a start on it
                logger.debug("progress notification failed", exc_info=True)

    store = get_v4_session_store()
    existing = await store_get(store, session_id)
    if existing is not None and existing.get("nodes_executed"):
        return build_start_response(session_id, existing)

    db_session = await _load_db_session_row(session_id)
    if db_session is None:
        raise SessionNotFoundException(session_id)

    style = get_style("AURA")
    from app.agents.planning.difficulty_engine import role_difficulty_floor

    org_id_str = str(db_session.org_id) if db_session.org_id else None
    job_role = db_session.job_role_snapshot or "Software Engineer"
    await _progress("loading_context")

    async def _resolve_taxonomy() -> list:
        if not (db_session.org_id or db_session.scorecard_template_id or db_session.it_role_id):
            return default_taxonomy()
        async with get_session_factory()() as db:
            role_context = None
            try:
                from app.intelligence.role_competency_profiler import build_role_context
                from app.models.db import Organization

                org_name = ""
                if db_session.org_id:  # practice sessions have no organization to look up
                    org_result = await db.execute(
                        select(Organization).where(Organization.id == db_session.org_id)
                    )
                    org_row = org_result.scalar_one_or_none()
                    if org_row:
                        org_name = org_row.name or ""
                role_context = build_role_context(
                    job_role=db_session.job_role_snapshot or "",
                    department_id=None,
                    department_name="",
                    org_name=org_name,
                )
            except Exception as exc:  # noqa: BLE001 - role context is best-effort
                logger.warning("Failed to build role context: %s", exc)
            return await resolve_competencies(
                db,
                scorecard_template_id=str(db_session.scorecard_template_id)
                if db_session.scorecard_template_id else None,
                org_id=db_session.org_id,
                role_context=role_context,
                it_role_id=db_session.it_role_id,  # the role's catalog competencies drive the interview
            )

    # The three pre-start inputs do not depend on each other (competency taxonomy, the candidate's
    # resume, the organization's company brain), so gather them instead of waiting for each in turn.
    # Each of them is dominated by network time (LLM / remote database / vector search).
    taxonomy, (candidate_profile, resume_text), company_brain = await asyncio.gather(
        _resolve_taxonomy(),
        _load_candidate_profile_data(db_session),
        get_or_build_company_brain(org_id=org_id_str, job_role=job_role),
    )
    competency_taxonomy, required, domain_label = taxonomy_for_state(
        taxonomy, priority_map=style.get("base_competency_priority")
    )
    await _progress("planning_interview")

    state = {
        "session_id": session_id,
        "job_role": db_session.job_role_snapshot or "Software Engineer",
        "org_id": str(db_session.org_id) if db_session.org_id else None,
        "it_role_id": str(db_session.it_role_id),
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": max(
            style.get("difficulty_range", (1, 3))[0],
            role_difficulty_floor(db_session.job_role_snapshot or ""),
        ),
        "candidate_profile": candidate_profile,
        "resume_text": resume_text,
        "scorecard_competencies": [
            {"id": c.get("id", ""), "name": c.get("name", c.get("id", "")), "weight": 1.0}
            for c in (competency_taxonomy or [])
        ],
        "competency_taxonomy": competency_taxonomy,
        "domain_label": domain_label,
        "required_competencies": required,
        "conversation_history": [],
        "question_number": 0,
        "current_question": "",
        "candidate_answer": "",
        "flow_type": "v5_evidence_driven",
        "nodes_executed": [],
        "start_time": time_module.strftime("%Y-%m-%dT%H:%M:%SZ", time_module.gmtime()),
        "hypotheses": [],
        "hypothesis_target": None,
        "evidence_store": [],
        "competency_summary": {},
        "unified_evaluation": {},
        "evaluation_score": None,
        "observations": [],
        "competency_plan": [],
        "next_competency": None,
        "interview_strategy": {},
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "hiring_recommendation": {},
        "contradictions": [],
        "consistency_checks": [],
        "extracted_evidence": [],
        "max_questions": style.get("max_questions", 20),
        "questions_asked": [],
        "question_objective": {},
        "skip_evaluation": False,
        "evaluator_mode": style.get("evaluator_mode", "unified"),
        "strategy_cache_valid": False,
    }

    engine = InterviewEngine(store=store, v5_persister=_get_v5_persister())
    response = await engine.start_session(
        state,
        build_intelligence=True,
        company_brain=company_brain,
    )

    logger.info(f"WS v5 session started: {session_id[:12]}..., role={state['job_role']}")
    return response


@router.websocket("/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: str):
    candidate_id = await _resolve_candidate_from_token(websocket.query_params.get("token"))
    access_session_id = verify_interview_access_token(websocket.query_params.get("access"))

    if validate_session_id(session_id) is None:
        await websocket.close(code=1008, reason="Invalid session")
        return

    await websocket.accept()

    conn_state: dict[str, Any] = {"session_id": session_id, "candidate_id": candidate_id}
    _connections[session_id] = conn_state
    _connection_timestamps[session_id] = time_module.time()
    limiter = MessageRateLimiter()
    authorized: set[str] = set()  # sessions this connection already proved access to (saves DB hits)

    async def reply(message: dict, request: Optional[dict] = None) -> None:
        await websocket.send_json(_send_id(message, request or {}))

    async def deny(sid: str) -> bool:
        """True (and tell the client) when this connection may NOT use ``sid``."""
        if sid in authorized:
            return False
        if await _verify_ws_session_access(sid, candidate_id, access_session_id):
            authorized.add(sid)
            return False
        return True

    try:
        await websocket.send_json({"type": "connected", "session_id": session_id})

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=IDLE_TIMEOUT_S)
            except asyncio.TimeoutError:
                await websocket.close(code=1000, reason="Idle timeout")
                break
            _connection_timestamps[session_id] = time_module.time()

            data, frame_error = parse_frame(raw)
            if frame_error:
                # A bad frame gets an error reply; it must never close the interview connection.
                await reply({"type": "error", "detail": frame_error})
                continue
            msg_type = data["type"]

            if not limiter.allow():
                await reply({"type": "error", "detail": "Too many messages. Please slow down."}, data)
                continue

            if msg_type == "ping":
                await reply({"type": "pong"}, data)

            elif msg_type == "start_interview":
                sid = validate_session_id(data.get("session_id")) or session_id
                if await deny(sid):
                    await reply({"type": "error", "detail": "Session access denied"}, data)
                    continue
                conn_state["session_id"] = sid
                _connections[sid] = conn_state
                async def push_progress(phase: str) -> None:
                    # No _id: it is a push, never the awaited reply (the "question" frame is).
                    await websocket.send_json({"type": "status", "phase": phase})

                try:
                    async with _session_locks.lock(sid):
                        response = await asyncio.wait_for(
                            _start_v4_engine(sid, notify=push_progress), timeout=START_TIMEOUT_S
                        )
                except SessionNotFoundException:
                    await reply({"type": "error", "detail": "Session not found"}, data)
                    continue
                except asyncio.TimeoutError:
                    logger.error(f"WS start timed out for session {sid}")
                    await reply({"type": "error", "detail": "Starting the interview took too long. Please try again."}, data)
                    continue
                except Exception:
                    logger.exception("WS start failed")
                    await reply({"type": "error", "detail": "Failed to start the interview. Please try again."}, data)
                    continue
                await reply({"type": "question", **response}, data)

            elif msg_type == "request_question":
                sid = conn_state["session_id"]
                if await deny(sid):
                    await reply({"type": "error", "detail": "Session access denied"}, data)
                    continue
                state = await store_get(get_v4_session_store(), sid)
                if state is None:
                    await reply({"type": "error", "detail": "Session not initialized"}, data)
                    continue
                await reply({"type": "question", **build_start_response(sid, state)}, data)

            elif msg_type == "submit_answer":
                sid = conn_state["session_id"]
                if await deny(sid):
                    await reply({"type": "error", "detail": "Session access denied"}, data)
                    continue
                candidate_answer, answer_error = validate_answer(data.get("candidate_answer"))
                if answer_error:
                    await reply({"type": "error", "detail": answer_error}, data)
                    continue

                # Optional anti-cheat telemetry (contract docs/anti-cheat-guard.md
                # §4.1 + §4.6). Absent from any client is always valid — no signal.
                integrity_meta = {
                    "paste_chars": data.get("paste_chars"),
                    "focus_lost_count": data.get("focus_lost_count"),
                    "answer_source": data.get("answer_source"),
                    "keystroke_intervals": data.get("keystroke_intervals"),
                    "first_key_ms": data.get("first_key_ms"),
                    "pointer_leaves": data.get("pointer_leaves"),
                    "heartbeat_gaps": data.get("heartbeat_gaps"),
                }

                await reply({"type": "status", "phase": "evaluating"}, data)

                try:
                    engine = InterviewEngine(
                        store=get_v4_session_store(),
                        v5_persister=_get_v5_persister(),
                    )
                    async with _session_locks.lock(sid):
                        result = await asyncio.wait_for(
                            engine.process_answer(sid, candidate_answer, integrity_meta=integrity_meta),
                            timeout=ANSWER_TIMEOUT_S,
                        )
                except SessionNotFoundException:
                    await reply({"type": "error", "detail": "Session not found"}, data)
                    continue
                except asyncio.TimeoutError:
                    logger.error(f"WS answer timed out for session {sid}")
                    await reply({"type": "error", "detail": "Evaluating your answer took too long. Please send it again."}, data)
                    continue
                except Exception:
                    logger.exception("WS answer failed")
                    await reply({"type": "error", "detail": "We could not process your answer. Please try again."}, data)
                    continue

                completed = result.get("status") == "completed" or result.get("interview_complete")
                if completed:
                    await reply({"type": "report", **result}, data)
                else:
                    await reply({"type": "status", "phase": "question_ready"}, data)
                    await reply({"type": "evaluation", **result}, data)

            elif msg_type == "get_status":
                sid = conn_state["session_id"]
                if await deny(sid):
                    await reply({"type": "error", "detail": "Session access denied"}, data)
                    continue
                state = await store_get(get_v4_session_store(), sid)
                if state is None:
                    await reply({"type": "error", "detail": "Session not found"}, data)
                    continue
                await reply({"type": "status_snapshot", **build_state_response(sid, state)}, data)

            else:
                await reply({"type": "error", "detail": "Unknown message type"}, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": "error", "detail": "Connection error"})  # no internals
        except Exception:
            pass
    finally:
        # Only remove our own registry entries (a newer connection may have replaced them).
        for key in {session_id, conn_state.get("session_id")}:
            if _connections.get(key) is conn_state:
                _connections.pop(key, None)
                _connection_timestamps.pop(key, None)
