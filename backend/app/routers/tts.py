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

    async def stream_audio():
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/audio/speech",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    print(f"[TTS Error {response.status_code}]: {body.decode()}", flush=True)
                    return
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    yield chunk

    return StreamingResponse(
        stream_audio(),
        media_type="audio/wav",
        headers={"X-Content-Type-Options": "nosniff"},
    )

# """
# MeetCore — TTS Router
# POST /tts — streams WAV audio via Groq Orpheus as it generates.
# Accommodates full multi-paragraph executive summaries without 422 errors.
# """
# import httpx
# from fastapi import APIRouter, HTTPException, status
# from fastapi.responses import StreamingResponse, Response
# from pydantic import BaseModel, Field

# from app.core.config import get_settings

# router = APIRouter(prefix="/tts", tags=["tts"])
# settings = get_settings()


# class TTSRequest(BaseModel):
#     # Expanded from 500 to 4000 so full spoken summaries do not trigger 422 Unprocessable Entity
#     text: str = Field(..., min_length=1, max_length=4000)
#     voice: str = "hannah"


# @router.post("")
# async def speak(req: TTSRequest):
#     cleaned_text = req.text.strip()
#     if not cleaned_text:
#         return Response(status_code=status.HTTP_204_NO_CONTENT)

#     # Truncate defensively to 2500 chars if an LLM response runs excessively long
#     if len(cleaned_text) > 2500:
#         cleaned_text = cleaned_text[:2500].rsplit(".", 1)[0] + "."

#     headers = {
#         "Authorization": f"Bearer {settings.GROQ_API_KEY}",
#         "Content-Type": "application/json",
#     }

#     payload = {
#         "model": getattr(settings, "GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english"),
#         "input": cleaned_text,
#         "voice": req.voice,
#         "response_format": "wav",
#     }

#     async def stream_audio():
#         async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
#             async with client.stream(
#                 "POST",
#                 "https://api.groq.com/openai/v1/audio/speech",
#                 headers=headers,
#                 json=payload,
#             ) as response:
#                 if response.status_code != 200:
#                     body = await response.aread()
#                     print(f"[TTS Error {response.status_code}]: {body.decode()}", flush=True)
#                     return
#                 async for chunk in response.aiter_bytes(chunk_size=4096):
#                     yield chunk

#     return StreamingResponse(
#         stream_audio(),
#         media_type="audio/wav",
#         headers={"X-Content-Type-Options": "nosniff"},
#     )