"""
MeetCore — TTS Router
POST /tts — Streams WAV audio via Groq Orpheus.
Validates input voices against the vendor allowlist and defaults unknown voices to 'hannah'.
"""
import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from app.core.config import get_settings

router = APIRouter(prefix="/tts", tags=["tts"])
settings = get_settings()

ALLOWED_VOICES = {"autumn", "diana", "hannah", "austin", "daniel", "troy"}


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str = "hannah"


@router.post("")
async def speak(req: TTSRequest):
    cleaned_text = req.text.strip()
    if not cleaned_text:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Sanitize voice input: replace non-Orpheus voices (e.g., en-US-Wavenet-D) with hannah
    selected_voice = req.voice.lower().strip() if req.voice else "hannah"
    if selected_voice not in ALLOWED_VOICES:
        print(f"[TTS] Unsupported voice '{req.voice}' requested. Defaulting to 'hannah'.", flush=True)
        selected_voice = "hannah"

    # Truncate defensively if a response runs excessively long for a single audio turn
    if len(cleaned_text) > 2500:
        cleaned_text = cleaned_text[:2500].rsplit(".", 1)[0] + "."

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": getattr(settings, "GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english"),
        "input": cleaned_text,
        "voice": selected_voice,
        "response_format": "wav",
    }

    async def get_audio_bytes():
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                print(f"[TTS Error {response.status_code}]: {response.text}", flush=True)
                raise HTTPException(status_code=response.status_code, detail="TTS service error")
            return response.content

    try:
        audio_data = await get_audio_bytes()
        return Response(audio_data, media_type="audio/wav", headers={"X-Content-Type-Options": "nosniff"})
    except httpx.RequestError as exc:
        print(f"[TTS Network Error]: {exc}", flush=True)
        raise HTTPException(status_code=503, detail="TTS upstream unreachable")
