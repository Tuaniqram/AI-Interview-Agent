"""
WebSocket-based interview protocol.
Persistent connection replaces HTTP request/response cycle for the interview flow.
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
from app.models.db import InterviewSession
from app.orchestrators.interview_orchestrator import InterviewOrchestrator
from app.exceptions import SessionNotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Interview WS"])

# Per-connection orchestrator instances
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


@router.websocket("/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: str):
    token = websocket.query_params.get("token")
    candidate_id = await _resolve_candidate_from_token(token)

    await websocket.accept()
    orchestrator = InterviewOrchestrator()

    # Per-connection state
    conn_state = {
        "session_id": session_id,
        "conversation_history": [],
        "current_phase": "intro",
        "question_number": 0,
        "difficulty_level": 1,
        "candidate_profile": {},
        "candidate_id": candidate_id,
    }
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
                await websocket.send_json({"type": "pong"})

            elif msg_type == "start_interview":
                existing_session_id = data.get("session_id")
                if existing_session_id:
                    if not await _verify_ws_session_access(existing_session_id, candidate_id):
                        await websocket.send_json({"type": "error", "detail": "Session access denied"})
                        continue
                    conn_state["session_id"] = existing_session_id
                    _connections[existing_session_id] = conn_state
                    await websocket.send_json({
                        "type": "session_created",
                        "session_id": existing_session_id,
                    })
                else:
                    result = await orchestrator.start_interview(
                        department_id=data.get("department_id"),
                        job_role=data["job_role"],
                        total_questions=data.get("total_questions", 10),
                        initial_difficulty=data.get("initial_difficulty", 1),
                        session_type=data.get("session_type", "department"),
                        interaction_mode=data.get("interaction_mode", "typing"),
                        candidate_id=candidate_id,
                    )
                    conn_state["session_id"] = result["session_id"]
                    _connections[result["session_id"]] = conn_state
                    await websocket.send_json({
                        "type": "session_created",
                        **result,
                    })

            elif msg_type == "request_question":
                if not await _verify_ws_session_access(conn_state["session_id"], candidate_id):
                    await websocket.send_json({"type": "error", "detail": "Session access denied"})
                    continue
                result = await orchestrator.initiate_next_question(
                    session_id=conn_state["session_id"],
                    conversation_history=conn_state["conversation_history"],
                    current_phase=conn_state["current_phase"],
                    question_number=conn_state["question_number"],
                    difficulty_level=conn_state["difficulty_level"],
                    candidate_profile=conn_state["candidate_profile"],
                )

                conn_state["current_phase"] = result.get("phase", conn_state["current_phase"])
                conn_state["question_number"] = result.get("question_number", conn_state["question_number"])
                conn_state["difficulty_level"] = result.get("difficulty_level", conn_state["difficulty_level"])

                await websocket.send_json({
                    "type": "question",
                    **result,
                })

            elif msg_type == "submit_answer":
                if not await _verify_ws_session_access(conn_state["session_id"], candidate_id):
                    await websocket.send_json({"type": "error", "detail": "Session access denied"})
                    continue
                question_number = data["question_number"]
                question = data["question"]
                candidate_answer = data["candidate_answer"]

                conn_state["conversation_history"].append({"role": "assistant", "content": question})
                conn_state["conversation_history"].append({"role": "user", "content": candidate_answer})

                result = await orchestrator.submit_answer(
                    session_id=conn_state["session_id"],
                    question_number=question_number,
                    question=question,
                    candidate_answer=candidate_answer,
                    conversation_history=conn_state["conversation_history"],
                    candidate_profile=conn_state["candidate_profile"],
                    difficulty_level=conn_state["difficulty_level"],
                )

                conn_state["current_phase"] = result.get("next_phase", conn_state["current_phase"])
                conn_state["difficulty_level"] = result.get("next_difficulty", conn_state["difficulty_level"])
                conn_state["question_number"] = question_number + 1

                await websocket.send_json({
                    "type": "evaluation",
                    **result,
                })

            elif msg_type == "get_status":
                if not await _verify_ws_session_access(conn_state["session_id"], candidate_id):
                    await websocket.send_json({"type": "error", "detail": "Session access denied"})
                    continue
                try:
                    status = await orchestrator.get_session_status(conn_state["session_id"])
                    await websocket.send_json({"type": "status", **status})
                except SessionNotFoundException:
                    await websocket.send_json({"type": "error", "detail": "Session not found"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"Unknown message type: {msg_type}",
                })

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
        _connections.pop(conn_state.get("session_id", ""), None)
        _connection_timestamps.pop(session_id, None)
        _connection_timestamps.pop(conn_state.get("session_id", ""), None)
