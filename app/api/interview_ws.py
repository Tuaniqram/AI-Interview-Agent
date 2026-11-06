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

from app.auth.jwt import decode_token
from app.database.session import get_session_factory
from app.services.event_log import get_event_log
from app.models.db import CandidateProfile, InterviewSession
from app.exceptions import SessionNotFoundException

from app.engine.engine import InterviewEngine
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


async def _verify_ws_session_access(session_id: str, candidate_id: Optional[str]) -> bool:
    """Verify the candidate owns the session (conditional — skip if no candidate_id)."""
    if candidate_id is None:
        return True  # org session, out of scope
    async with get_session_factory()() as db:
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.id == UUID(session_id))
        )
        session = result.scalar_one_or_none()
    if not session:
        return False
    if session.candidate_profile_id is not None:
        return str(session.candidate_profile_id) == candidate_id
    return True  # unowned session, allow


def _send_id(message: dict, request: dict) -> dict:
    """Echo the client's _id (when present) so the client can resolve the request."""
    if "_id" in request:
        message["_id"] = request["_id"]
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


async def _start_v4_engine(session_id: str) -> dict:
    """Start (or resume) the v5 AURA engine for the given session.

    The session row in the DB is the source of truth for job_role / department_id;
    the engine state lives in the v4 session store under the same session_id.
    All orchestration is delegated to ``InterviewEngine``.
    """
    store = get_v4_session_store()
    existing = store.get(session_id)
    if existing is not None and existing.get("nodes_executed"):
        return build_start_response(session_id, existing)

    db_session = await _load_db_session_row(session_id)
    if db_session is None:
        raise SessionNotFoundException(session_id)

    style = get_style("AURA")
    from app.agents.planning.difficulty_engine import role_difficulty_floor

    taxonomy = default_taxonomy()
    if db_session.org_id or db_session.scorecard_template_id:
        async with get_session_factory()() as db:
            role_context = None
            try:
                from app.intelligence.role_competency_profiler import build_role_context
                from app.models.db import Organization

                org_name = ""
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
            taxonomy = await resolve_competencies(
                db,
                scorecard_template_id=str(db_session.scorecard_template_id)
                if db_session.scorecard_template_id else None,
                org_id=db_session.org_id,
                role_context=role_context,
            )
    competency_taxonomy, required, domain_label = taxonomy_for_state(
        taxonomy, priority_map=style.get("base_competency_priority")
    )

    candidate_profile, resume_text = await _load_candidate_profile_data(db_session)

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
    company_brain = await get_or_build_company_brain(
        department_id=None,
        job_role=db_session.job_role_snapshot or "Software Engineer",
    )
    response = await engine.start_session(
        state,
        build_intelligence=True,
        company_brain=company_brain,
    )

    logger.info(f"WS v5 session started: {session_id[:12]}..., role={state['job_role']}")
    return response


@router.websocket("/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: str):
    token = websocket.query_params.get("token")
    candidate_id = await _resolve_candidate_from_token(token)

    await websocket.accept()

    conn_state: dict[str, Any] = {"session_id": session_id, "candidate_id": candidate_id}
    _connections[session_id] = conn_state
    _connection_timestamps[session_id] = time_module.time()

    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
        })

        while True:
            _connection_timestamps[session_id] = time_module.time()
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                _connection_timestamps[session_id] = time_module.time()
                await websocket.send_json(_send_id({"type": "pong"}, data))

            elif msg_type == "start_interview":
                sid = data.get("session_id") or session_id
                if not await _verify_ws_session_access(sid, candidate_id):
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session access denied"}, data))
                    continue
                conn_state["session_id"] = sid
                _connections[sid] = conn_state
                try:
                    response = await _start_v4_engine(sid)
                except SessionNotFoundException:
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session not found"}, data))
                    continue
                except Exception as e:
                    logger.exception(f"WS start failed: {e}")
                    await websocket.send_json(_send_id({"type": "error", "detail": f"Failed to start interview: {type(e).__name__}"}, data))
                    continue
                await websocket.send_json(_send_id({"type": "question", **response}, data))

            elif msg_type == "request_question":
                sid = conn_state["session_id"]
                if not await _verify_ws_session_access(sid, candidate_id):
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session access denied"}, data))
                    continue
                store = get_v4_session_store()
                state = store.get(sid)
                if state is None:
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session not initialized"}, data))
                    continue
                await websocket.send_json(_send_id({"type": "question", **build_start_response(sid, state)}, data))

            elif msg_type == "submit_answer":
                sid = conn_state["session_id"]
                if not await _verify_ws_session_access(sid, candidate_id):
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session access denied"}, data))
                    continue
                candidate_answer = data.get("candidate_answer", "")

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

                await websocket.send_json(_send_id({"type": "status", "phase": "evaluating"}, data))

                try:
                    engine = InterviewEngine(
                        store=get_v4_session_store(),
                        v5_persister=_get_v5_persister(),
                    )
                    result = await engine.process_answer(sid, candidate_answer, integrity_meta=integrity_meta)
                except SessionNotFoundException:
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session not found"}, data))
                    continue
                except Exception as e:
                    logger.exception(f"WS answer failed: {e}")
                    await websocket.send_json(_send_id({"type": "error", "detail": f"Error processing answer: {type(e).__name__}"}, data))
                    continue

                completed = result.get("status") == "completed" or result.get("interview_complete")
                if completed:
                    await websocket.send_json(_send_id({"type": "report", **result}, data))
                else:
                    await websocket.send_json(_send_id({"type": "status", "phase": "question_ready"}, data))
                    await websocket.send_json(_send_id({"type": "evaluation", **result}, data))

            elif msg_type == "get_status":
                sid = conn_state["session_id"]
                if not await _verify_ws_session_access(sid, candidate_id):
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session access denied"}, data))
                    continue
                store = get_v4_session_store()
                state = store.get(sid)
                if state is None:
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session not found"}, data))
                    continue
                status = build_state_response(sid, state)
                await websocket.send_json(_send_id({"type": "status_snapshot", **status}, data))

            else:
                await websocket.send_json(_send_id({
                    "type": "error",
                    "detail": f"Unknown message type: {msg_type}",
                }, data))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        _connections.pop(session_id, None)
        _connection_timestamps.pop(session_id, None)
