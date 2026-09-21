# """
# MeetCore — TTS Router
# POST /tts — takes text, returns WAV audio via Groq Orpheus TTS.
# No extra API key needed — uses GROQ_API_KEY.

# Available voices: autumn, diana, hannah, austin, daniel, troy
# """
# import httpx
# from fastapi import APIRouter, HTTPException
# from fastapi.responses import Response
# from pydantic import BaseModel, Field

# from app.core.config import get_settings

# router = APIRouter(prefix="/tts", tags=["tts"])
# settings = get_settings()


# class TTSRequest(BaseModel):
#     text: str = Field(..., max_length=500)  # Safeguard against overly long text blocks
#     voice: str = "hannah"


# @router.post("", response_class=Response)
# async def speak(req: TTSRequest):
#     cleaned_text = req.text.strip()
#     if not cleaned_text:
#         raise HTTPException(status_code=400, detail="Text cannot be empty.")

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

#     # Increased timeout limits to prevent premature cutting
#     timeout_config = httpx.Timeout(60.0, connect=10.0)

#     try:
#         async with httpx.AsyncClient(timeout=timeout_config) as client:
#             response = await client.post(
#                 "https://api.groq.com/openai/v1/audio/speech",
#                 headers=headers,
#                 json=payload,
#             )
#     except httpx.ReadTimeout:
#         raise HTTPException(
#             status_code=504,
#             detail="Orpheus TTS service took too long to respond. Try sending shorter text blocks."
#         )
#     except httpx.HTTPError as e:
#         raise HTTPException(
#             status_code=502,
#             detail=f"Network error communicating with Groq TTS: {str(e)}"
#         )

#     if response.status_code != 200:
#         raise HTTPException(
#             status_code=502,
#             detail=f"Groq TTS error: {response.status_code} — {response.text}",
#         )

#     return Response(content=response.content, media_type="audio/wav")
"""
MeetCore — TTS Router
POST /tts — streams WAV audio via Groq Orpheus as it generates.
First audio chunk plays on the frontend within ~200-400ms.
"""
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(prefix="/tts", tags=["tts"])
settings = get_settings()


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=500)
    voice: str = "hannah"


@router.post("")
async def speak(req: TTSRequest):
    cleaned_text = req.text.strip()
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": getattr(settings, "GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english"),
        "input": cleaned_text,
        "voice": req.voice,
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
                    # Drain error body and raise
                    body = await response.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=f"Groq TTS error: {response.status_code} — {body.decode()}",
                    )
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    yield chunk

    return StreamingResponse(
        stream_audio(),
        media_type="audio/wav",
        headers={"X-Content-Type-Options": "nosniff"},
    )