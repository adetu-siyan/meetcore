import asyncio
import logging
from typing import AsyncGenerator
import httpx
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("meetcore.assemblyai")


class AssemblyAIError(Exception):
    """Custom exception raised for AssemblyAI API errors."""
    pass


def _get_headers() -> dict:
    """Returns AssemblyAI headers, stripping quotes or whitespace from the key."""
    api_key = settings.ASSEMBLYAI_API_KEY.strip().strip('"').strip("'") if settings.ASSEMBLYAI_API_KEY else ""
    if not api_key:
        raise AssemblyAIError("ASSEMBLYAI_API_KEY is not set in environment settings.")
    return {"authorization": api_key}


def _get_base_url() -> str:
    """Ensures base URL ends with /v2 without duplication."""
    base = settings.ASSEMBLYAI_BASE_URL.rstrip("/") if hasattr(settings, "ASSEMBLYAI_BASE_URL") and settings.ASSEMBLYAI_BASE_URL else "https://api.assemblyai.com/v2"
    if not base.endswith("/v2"):
        base = f"{base}/v2"
    return base


async def upload_audio_bytes(file_bytes: bytes, chunk_size: int = 5 * 1024 * 1024) -> str:
    """
    Upload audio to AssemblyAI in chunks and return its hosted audio URL.

    Chunked transfer avoids building another full-size request body in memory.
    """
    headers = _get_headers()
    headers["content-type"] = "application/octet-stream"
    url = f"{_get_base_url()}/upload"

    async def file_chunk_generator() -> AsyncGenerator[bytes, None]:
        """Yield consecutive chunks from the in-memory audio file."""
        for i in range(0, len(file_bytes), chunk_size):
            yield file_bytes[i : i + chunk_size]

    timeout = httpx.Timeout(600.0, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, content=file_chunk_generator())

    if response.status_code != 200:
        logger.error(f"[AssemblyAI] Upload failed HTTP {response.status_code}: {response.text}")
        raise AssemblyAIError(f"Upload to AssemblyAI failed ({response.status_code}): {response.text}")

    data = response.json()
    upload_url = data.get("upload_url")
    if not upload_url:
        raise AssemblyAIError("AssemblyAI upload response missing 'upload_url'.")

    logger.info(f"[AssemblyAI] File successfully uploaded to {upload_url}")
    return upload_url


async def create_transcript_job(audio_url: str) -> str:
    """
    Start an AssemblyAI transcription with meeting analysis features enabled.

    Summarization is enabled; auto-chapters is disabled because the two options
    cannot be requested together. Return the created transcript ID.
    """
    headers = _get_headers()
    headers["content-type"] = "application/json"
    url = f"{_get_base_url()}/transcript"

    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,          # Speaker Diarization
        "auto_chapters": False,          # Mutually exclusive with summarization
        "summarization": True,           # Executive Summary Generation
        "summary_type": "bullets",       # Options: 'bullets', 'gist', 'headline', 'paragraph'
        "summary_model": "informative",   # Options: 'informative', 'conversational', 'catchy'
        "sentiment_analysis": True,     # Sentiment per sentence
        "auto_highlights": True,         # Key phrases and key topics
        "entity_detection": True,        # Detect names, locations, dates, objects
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        logger.error(f"[AssemblyAI] Transcript job creation failed ({response.status_code}): {response.text}")
        raise AssemblyAIError(f"Failed to submit transcript job: {response.status_code} — {response.text}")

    data = response.json()
    transcript_id = data.get("id")
    if not transcript_id:
        raise AssemblyAIError("AssemblyAI transcript job response missing 'id'.")

    logger.info(f"[AssemblyAI] Created full-feature transcript job ID: {transcript_id}")
    return transcript_id


async def get_transcript(transcript_id: str, poll_interval: int = 3, max_attempts: int = 300) -> dict:
    """
    Poll AssemblyAI until the transcript completes or fails.

    Return the completed transcript response, or raise an error if the provider
    reports failure or the polling limit is reached.
    """
    headers = _get_headers()
    url = f"{_get_base_url()}/transcript/{transcript_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, max_attempts + 1):
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                logger.error(f"[AssemblyAI] Fetch transcript failed ({response.status_code}): {response.text}")
                raise AssemblyAIError(f"Fetching transcript failed ({response.status_code}): {response.text}")

            data = response.json()
            status = data.get("status")

            if status == "completed":
                logger.info(f"[AssemblyAI] Processing completed for ID: {transcript_id}")
                return data

            if status == "error":
                error_msg = data.get("error", "Unknown AssemblyAI error")
                logger.error(f"[AssemblyAI] Transcription error for {transcript_id}: {error_msg}")
                raise AssemblyAIError(f"AssemblyAI transcription failed: {error_msg}")

            logger.info(f"[AssemblyAI] Poll {attempt}/{max_attempts} — status: '{status}'. Waiting {poll_interval}s...")
            await asyncio.sleep(poll_interval)

    raise AssemblyAIError(f"Timed out waiting for transcript {transcript_id} after {max_attempts} attempts.")