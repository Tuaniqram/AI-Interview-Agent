import time
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.speech.websocket_manager import get_connection_manager
from app.speech.tts_service import get_tts_service
from app.speech.speech_timeline import build_speech_timeline
from app.speech.models import EmotionType

router = APIRouter(tags=["avatar"])


@router.websocket("/ws/avatar/{session_id}")
async def avatar_websocket(websocket: WebSocket, session_id: str):
    manager = get_connection_manager()
    tts = get_tts_service()

    await manager.connect(session_id, websocket)
    response_id = str(uuid.uuid4())

    try:
        await manager.broadcast_speech_event(
            session_id,
            response_id,
            "session_ready",
            data={
                "session_id": session_id,
                "voice_name": "eleven_labs",
                "sample_rate": 24000,
            },
        )

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "speak":
                text = data.get("text", "")
                emotion_str = data.get("emotion", "neutral")
                emotion = EmotionType(emotion_str) if emotion_str in [e.value for e in EmotionType] else EmotionType.neutral

                response_id = str(uuid.uuid4())
                timeline_data = build_speech_timeline(text, emotion=emotion)
                manager.clear_response_text(session_id)
                manager.append_response_text(session_id, text)

                await manager.broadcast_speech_start(session_id, response_id, text)

                async def on_viseme_timestamps(timestamps: list[dict]):
                    from app.speech.viseme_generator import timestamps_to_visemes
                    visemes = timestamps_to_visemes(timestamps)
                    for v in visemes:
                        duration = v.get("duration", 0.1)
                        await manager.broadcast_viseme(
                            session_id,
                            response_id,
                            v["time"],
                            v["value"],
                            v.get("intensity", 0.8),
                            duration,
                        )

                chunk_num = 0

                async def on_chunk(b64_data: str, seq: int, is_final: bool):
                    nonlocal chunk_num
                    await manager.broadcast_audio_chunk(
                        session_id, response_id, b64_data, chunk_num, is_final
                    )
                    chunk_num += 1

                await tts.stream_audio(
                    text,
                    on_chunk=on_chunk,
                    on_timestamps=on_viseme_timestamps,
                )

                total_duration = timeline_data.get("duration", len(text.split()) * 0.3)
                await manager.broadcast_speech_end(
                    session_id, response_id, total_duration
                )

                for expr in timeline_data.get("expressions", []):
                    await manager.broadcast_expression(
                        session_id,
                        response_id,
                        expr["time"],
                        expr["emotion"],
                        expr["intensity"],
                    )

                for gest in timeline_data.get("gestures", []):
                    await manager.broadcast_gesture(
                        session_id,
                        response_id,
                        gest["time"],
                        gest["gesture"],
                        gest["intensity"],
                    )

            elif msg_type == "ping":
                await manager.send_text_json(
                    session_id,
                    {"type": "pong", "timestamp": time.time()},
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        print(f"[Avatar WS] Error: {e}")
        try:
            await manager.broadcast_speech_event(
                session_id,
                response_id,
                "error",
                data={"code": "internal_error", "message": str(e)},
            )
        except Exception:
            pass
        manager.disconnect(session_id)
