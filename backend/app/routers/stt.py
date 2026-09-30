# """
# MeetCore — STT via AssemblyAI
# Handles live mic push-to-talk audio by uploading and transcribing via AssemblyAI.
# """
# import httpx
# import asyncio
# from fastapi import APIRouter, File, HTTPException, UploadFile
# from pydantic import BaseModel
# from app.core.config import get_settings
# from app.services import assemblyai_service

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

#     try:
#         upload_url = await assemblyai_service.upload_audio_bytes(audio_bytes)
#         tx_id = await assemblyai_service.create_transcript_job(upload_url)
#         data = await assemblyai_service.get_transcript(tx_id)
#         cleaned_text = data.get("text", "")
#         print(f"[STT AssemblyAI] Transcribed: '{cleaned_text}'", flush=True)
#         return STTResponse(text=cleaned_text)

#     except Exception as e:
#         print(f"[STT Error]: {e}", flush=True)
#         raise HTTPException(status_code=502, detail=f"Speech recognition failed: {e}")

"""
MeetCore — Ultra Low Latency STT via Groq Whisper
"""
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
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
    if len(audio_bytes) < 300:
        raise HTTPException(status_code=400, detail="Audio clip too short.")

    groq_key = settings.GROQ_API_KEY.strip().strip('"').strip("'") if settings.GROQ_API_KEY else ""
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    try:
        # Pass Opus WEBM directly to reduce payload size
        filename = file.filename or "speech.webm"
        content_type = file.content_type or "audio/webm"

        # Using connection reuse via transport pool for faster execution
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key}"},
                files={"file": (filename, audio_bytes, content_type)},
                data={
                    "model": "whisper-large-v3-turbo",
                    "temperature": "0.0",
                    "prompt": "Meeting conversation with Nio assistant.",  # Speeds up Whisper decoding
                    "language": "en",  # Specifying language avoids auto-detection delay
                },
            )

        if response.status_code != 200:
            print(f"[STT Error {response.status_code}]: {response.text}", flush=True)
            raise HTTPException(status_code=response.status_code, detail="STT transcription failed.")

        cleaned_text = response.json().get("text", "").strip()
        print(f"[STT] Transcribed: '{cleaned_text}'", flush=True)
        return STTResponse(text=cleaned_text)

    except httpx.RequestError as exc:
        print(f"[STT Network Error]: {exc}", flush=True)
        raise HTTPException(status_code=503, detail="STT service unreachable.")
    except Exception as e:
        print(f"[STT Error]: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Speech recognition failed: {e}")