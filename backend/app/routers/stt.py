"""
MeetCore — STT via AssemblyAI
Handles live mic push-to-talk audio by uploading and transcribing via AssemblyAI.
"""
import httpx
import asyncio
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from app.core.config import get_settings
from app.services import assemblyai_service

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

    try:
        # 1. Upload audio
        upload_url = await assemblyai_service.upload_file(audio_bytes)

        # 2. Start transcription
        tx_id = await assemblyai_service.start_transcription(
            upload_url=upload_url,
            meeting_id="",
            speech_models=["universal-3-5-pro", "universal-2"],
            speaker_labels=False,
            auto_chapters=False,
            sentiment_analysis=False,
            entity_detection=False,
            punctuate=True,
            format_text=True,
        )

        # 3. Poll for completion
        start_time = asyncio.get_event_loop().time()
        while True:
            if asyncio.get_event_loop().time() - start_time > 30:
                raise Exception("Transcription timed out after 30 seconds.")
                
            data = await assemblyai_service.get_transcript(tx_id)
            if data["status"] == "completed":
                cleaned_text = data["text"]
                break
            elif data["status"] == "error":
                raise Exception(data.get("error"))
            await asyncio.sleep(0.2)

        print(f"[STT AssemblyAI] Transcribed: '{cleaned_text}'", flush=True)
        return STTResponse(text=cleaned_text)

    except Exception as e:
        print(f"[STT Error]: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"Speech recognition failed: {e}")
