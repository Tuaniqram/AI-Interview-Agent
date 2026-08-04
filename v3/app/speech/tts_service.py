import os
import io
import base64
import json
from typing import AsyncGenerator, Optional, Callable, Awaitable
import httpx

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")


class TTSService:
    def __init__(self, api_key: str = ELEVENLABS_API_KEY):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def stream_audio(
        self,
        text: str,
        on_chunk: Callable[[bytes, int, bool], Awaitable[None]],
        on_timestamps: Optional[Callable[[list[dict]], Awaitable[None]]] = None,
    ) -> None:
        if not self.api_key:
            await self._fallback_silence(text, on_chunk)
            return

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.7,
                "speed": 1.0,
            },
        }

        chunk_num = 0
        audio_buffer = bytearray()

        async with self.client.stream(
            "POST", url, headers=headers, json=payload
        ) as resp:
            if resp.status_code != 200:
                error_text = await resp.aread()
                print(f"[TTS] ElevenLabs error {resp.status_code}: {error_text}")
                await self._fallback_silence(text, on_chunk)
                return

            async for chunk in resp.aiter_bytes():
                audio_buffer.extend(chunk)
                if len(audio_buffer) >= 4096:
                    b64 = base64.b64encode(bytes(audio_buffer)).decode("utf-8")
                    await on_chunk(b64, chunk_num, False)
                    chunk_num += 1
                    audio_buffer.clear()

        if audio_buffer:
            b64 = base64.b64encode(bytes(audio_buffer)).decode("utf-8")
            await on_chunk(b64, chunk_num, True)
        elif chunk_num > 0:
            await on_chunk("", chunk_num, True)

        if on_timestamps:
            fake_timestamps = self._generate_timestamps(text)
            await on_timestamps(fake_timestamps)

    async def close(self):
        await self.client.aclose()

    def _generate_timestamps(self, text: str) -> list[dict]:
        timestamps: list[dict] = []
        words = text.split()
        current_time = 0.0

        for word in words:
            word_duration = len(word) * 0.08
            char_duration = word_duration / max(len(word), 1)

            for ch in word:
                timestamps.append({
                    "char": ch,
                    "start": round(current_time, 3),
                    "end": round(current_time + char_duration, 3),
                })
                current_time += char_duration

            current_time += 0.02

        return timestamps

    async def _fallback_silence(
        self,
        text: str,
        on_chunk: Callable[[bytes, int, bool], Awaitable[None]],
    ) -> None:
        duration = len(text.split()) * 0.3
        silence_duration = min(duration, 30.0)
        num_chunks = max(1, int(silence_duration * 10))
        chunk_size = int(16000 * silence_duration / num_chunks) * 2

        for i in range(num_chunks):
            silence = bytes(chunk_size)
            b64 = base64.b64encode(silence).decode("utf-8")
            await on_chunk(b64, i, False)

        await on_chunk("", num_chunks, True)


_tts_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSService()
    return _tts_instance
