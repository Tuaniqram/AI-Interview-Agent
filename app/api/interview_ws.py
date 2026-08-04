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
from app.models.db import InterviewSession
from app.exceptions import SessionNotFoundException

from app.api.interview_v4 import (
    V4StartRequest,
    _build_initial_state,
    _build_start_response,
    _build_state_response,
    process_v4_answer,
)
from app.agents.session_init_node import session_init_node
from app.agents.company_context_node import department_context_node
from app.agents.candidate_profile_node import candidate_profile_node
from app.agents.competency_planner_node import competency_planner_node
from app.agents.strategy_brain_node import strategy_brain_node
from app.agents.hypothesis_node import hypothesis_node
from app.agents.question_generator_node import question_generator_node
from app.config.interview_styles import get_style
from app.data.competency_resolver import (
    default_taxonomy,
    resolve_competencies,
    taxonomy_for_state,
)
from app.services.v4_session_store import get_v4_session_store

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


async def _start_v4_engine(session_id: str) -> dict:
    """Start (or resume) the v4 AURA engine for the given session.

    The session row in the DB is the source of truth for job_role / department_id;
    the engine state lives in the v4 session store under the same session_id.
    """
    store = get_v4_session_store()
    existing = store.get(session_id)
    if existing is not None:
        return _build_start_response(session_id, existing)

    db_session = await _load_db_session_row(session_id)
    if db_session is None:
        raise SessionNotFoundException(session_id)

    style = get_style("AURA")
    taxonomy = default_taxonomy()
    if db_session.department_id:
        async with get_session_factory()() as db:
            taxonomy = await resolve_competencies(db, department_id=db_session.department_id)
    competency_taxonomy, required, domain_label = taxonomy_for_state(taxonomy)

    request = V4StartRequest(
        job_role=db_session.job_role or "Software Engineer",
        style_name="AURA",
        department_id=db_session.department_id,
    )

    state = _build_initial_state(
        session_id, request, style, competency_taxonomy, required, domain_label
    )
    state = session_init_node(state)
    state = await department_context_node(state)
    state = await candidate_profile_node(state)
    state = await competency_planner_node(state)
    state = await strategy_brain_node(state)
    state = await hypothesis_node(state)
    target = state.get("hypothesis_target") or {}
    await get_event_log().append(session_id, "question_selected", {
        "question_number": state.get("question_number", 0),
        "target_hypothesis_id": target.get("id", ""),
        "competency": target.get("competency", ""),
        "status": target.get("status", ""),
        "selection_reason": target.get("selection_reason", ""),
        "information_gain": target.get("information_gain", 0.0),
    })
    state = await question_generator_node(state)

    store.set(session_id, state)
    logger.info(f"WS v4 session started: {session_id[:12]}..., role={request.job_role}")
    await get_event_log().append(session_id, "session_started", {
        "style_name": request.style_name,
        "job_role": request.job_role,
        "department_id": request.department_id,
        "competency_count": len(competency_taxonomy),
        "domain_label": domain_label,
    })
    return _build_start_response(session_id, state)


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
                await websocket.send_json(_send_id({"type": "question", **_build_start_response(sid, state)}, data))

            elif msg_type == "submit_answer":
                sid = conn_state["session_id"]
                if not await _verify_ws_session_access(sid, candidate_id):
                    await websocket.send_json(_send_id({"type": "error", "detail": "Session access denied"}, data))
                    continue
                candidate_answer = data.get("candidate_answer", "")

                await websocket.send_json(_send_id({"type": "status", "phase": "evaluating"}, data))

                try:
                    result = await process_v4_answer(sid, candidate_answer)
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
                status = _build_state_response(sid, state)
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
