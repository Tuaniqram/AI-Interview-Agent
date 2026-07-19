import json
import time
import uuid
from typing import Optional
from fastapi import WebSocket

from app.speech.models import WSMessage


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_responses: dict[str, str] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_responses[session_id] = ""
        return session_id

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        self.session_responses.pop(session_id, None)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self.active_connections

    async def send_message(self, session_id: str, message: WSMessage):
        ws = self.active_connections.get(session_id)
        if ws is None:
            return
        try:
            await ws.send_json(message.model_dump(exclude_none=True))
        except Exception as e:
            print(f"[WS] Send error for {session_id}: {e}")
            self.disconnect(session_id)

    async def send_text_json(self, session_id: str, data: dict):
        ws = self.active_connections.get(session_id)
        if ws is None:
            return
        try:
            await ws.send_json(data)
        except Exception as e:
            print(f"[WS] Send error for {session_id}: {e}")
            self.disconnect(session_id)

    def append_response_text(self, session_id: str, text: str):
        if session_id in self.session_responses:
            self.session_responses[session_id] += text

    def get_response_text(self, session_id: str) -> str:
        return self.session_responses.get(session_id, "")

    def clear_response_text(self, session_id: str):
        if session_id in self.session_responses:
            self.session_responses[session_id] = ""

    async def broadcast_speech_event(
        self,
        session_id: str,
        response_id: str,
        event_type: str,
        data: Optional[dict] = None,
        sequence: int = 0,
    ):
        msg = WSMessage(
            session_id=session_id,
            response_id=response_id,
            type=event_type,
            timestamp=time.time(),
            sequence=sequence,
            data=data,
        )
        await self.send_message(session_id, msg)

    async def broadcast_speech_start(
        self, session_id: str, response_id: str, text: str
    ):
        words = text.split()
        estimated_duration = len(words) * 0.3
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "speech_start",
            data={
                "response_id": response_id,
                "text_preview": text[:100],
                "expected_duration": round(estimated_duration, 1),
            },
        )

    async def broadcast_audio_chunk(
        self,
        session_id: str,
        response_id: str,
        b64_data: str,
        sequence: int,
        is_final: bool,
    ):
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "audio_chunk",
            data={
                "audio": b64_data,
                "sample_rate": 24000,
                "is_final": is_final,
            },
            sequence=sequence,
        )

    async def broadcast_viseme(
        self,
        session_id: str,
        response_id: str,
        time_sec: float,
        value: str,
        intensity: float,
        duration: float,
    ):
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "viseme",
            data={
                "time": time_sec,
                "value": value,
                "intensity": intensity,
                "duration": duration,
            },
        )

    async def broadcast_expression(
        self,
        session_id: str,
        response_id: str,
        time_sec: float,
        emotion: str,
        intensity: float,
    ):
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "expression",
            data={
                "time": time_sec,
                "emotion": emotion,
                "intensity": intensity,
            },
        )

    async def broadcast_gesture(
        self,
        session_id: str,
        response_id: str,
        time_sec: float,
        gesture: str,
        intensity: float,
    ):
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "gesture",
            data={
                "time": time_sec,
                "gesture": gesture,
                "intensity": intensity,
            },
        )

    async def broadcast_speech_end(
        self, session_id: str, response_id: str, total_duration: float
    ):
        await self.broadcast_speech_event(
            session_id,
            response_id,
            "speech_end",
            data={
                "total_duration": round(total_duration, 3),
            },
        )


_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
