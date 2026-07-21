"""
WebSocket-based interview protocol.
Persistent connection replaces HTTP request/response cycle for the interview flow.
"""
import asyncio
import json
import logging
import time as time_module
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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


@router.websocket("/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: str):
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
                result = await orchestrator.start_interview(
                    company_id=data["company_id"],
                    job_role=data["job_role"],
                    candidate_id=data.get("candidate_id", ""),
                    candidate_name=data.get("candidate_name", ""),
                    candidate_email=data.get("candidate_email", ""),
                    total_questions=data.get("total_questions", 10),
                    initial_difficulty=data.get("initial_difficulty", 1),
                    interview_type=data.get("interview_type", "company"),
                    interview_mode=data.get("interview_mode", "typing"),
                )
                conn_state["session_id"] = result["session_id"]
                _connections[result["session_id"]] = conn_state

                await websocket.send_json({
                    "type": "session_created",
                    **result,
                })

            elif msg_type == "request_question":
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
