"""
MeetCore — Ultra-Low-Latency STT via Groq Whisper
Handles live mic push-to-talk audio directly with sub-250ms latency.
"""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from groq import AsyncGroq
from app.core.config import get_settings

router = APIRouter(prefix="/stt", tags=["stt"])
settings = get_settings()


class STTResponse(BaseModel):
    text: str


@router.post("", response_model=STTResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(audio_bytes) < 500:
        raise HTTPException(status_code=400, detail="Audio clip too short.")

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    try:
        filename = file.filename or "recording.webm"
        transcription = await client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="text",
            temperature=0.0,
        )
        cleaned_text = str(transcription).strip()
        print(f"[STT Groq Turbo] Transcribed: '{cleaned_text}'", flush=True)
        return STTResponse(text=cleaned_text)

    except Exception as e:
        print(f"[STT Error]: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Speech recognition failed: {e}")

# """
# MeetCore — Ultra-Low-Latency STT via Groq Whisper
# Handles real-time mic push-to-talk turns directly from the browser.
# Eliminates ffmpeg subprocess conversion and WebSocket handshake overhead.
# """
# from fastapi import APIRouter, File, HTTPException, UploadFile
# from pydantic import BaseModel
# from groq import AsyncGroq
# from app.core.config import get_settings

# router = APIRouter(prefix="/stt", tags=["stt"])
# settings = get_settings()


# class STTResponse(BaseModel):
#     text: str


# @router.post("", response_model=STTResponse)
# async def transcribe_audio(file: UploadFile = File(...)):
#     audio_bytes = await file.read()

#     if not audio_bytes:
#         raise HTTPException(status_code=400, detail="Empty audio file.")
#     if len(audio_bytes) < 500:
#         raise HTTPException(status_code=400, detail="Audio clip too short.")

#     client = AsyncGroq(api_key=settings.GROQ_API_KEY)

#     try:
#         filename = file.filename or "recording.webm"
#         transcription = await client.audio.transcriptions.create(
#             file=(filename, audio_bytes),
#             model="whisper-large-v3-turbo",
#             response_format="text",
#             temperature=0.0,
#         )
#         cleaned_text = str(transcription).strip()
#         print(f"[STT Groq Turbo] Transcribed: '{cleaned_text}'", flush=True)
#         return STTResponse(text=cleaned_text)

#     except Exception as e:
#         print(f"[STT Error]: {e}", flush=True)
#         raise HTTPException(status_code=502, detail=f"Speech recognition failed: {e}")