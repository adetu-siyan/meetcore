
"""
MeetCore — AssemblyAI Service
"""
import httpx
from app.core.config import get_settings

settings = get_settings()


class AssemblyAIError(Exception):
    pass


async def upload_file(file_bytes: bytes) -> str:
    headers = {
        "authorization": settings.ASSEMBLYAI_API_KEY,
        "content-type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/upload",
            headers=headers,
            content=file_bytes,
        )

    if response.status_code != 200:
        raise AssemblyAIError(f"Upload failed: {response.status_code} — {response.text}")

    upload_url = response.json().get("upload_url")
    if not upload_url:
        raise AssemblyAIError("AssemblyAI did not return an upload_url")

    return upload_url


async def start_transcription(upload_url: str, meeting_id: str, **kwargs) -> str:
    headers = {
        "authorization": settings.ASSEMBLYAI_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "audio_url": upload_url,
        "speech_models": ["universal-3-5-pro", "universal-2"],
        "speaker_labels": True,
        "auto_chapters": True,
        "sentiment_analysis": True,
        "entity_detection": True,
        "punctuate": True,
        "format_text": True,
    }
    payload.update(kwargs)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        raise AssemblyAIError(
            f"Transcription request failed: {response.status_code} — {response.text}"
        )

    transcript_id = response.json().get("id")
    if not transcript_id:
        raise AssemblyAIError("AssemblyAI did not return a transcript id")

    return transcript_id


async def get_transcript(transcript_id: str) -> dict:
    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}",
            headers=headers,
        )

    if response.status_code != 200:
        raise AssemblyAIError(
            f"Fetching transcript failed: {response.status_code} — {response.text}"
        )

    return response.json()