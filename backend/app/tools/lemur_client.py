"""
MeetCore — Groq Extraction Client (Qwen 3.8 27B)
Routes transcript text to Groq using Qwen/Qwen3.8-27B for 
structured extractions (tasks, deadlines, decisions, priority brief).
"""
import asyncio
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)
from app.core.config import get_settings

settings = get_settings()

# In-memory cache to prevent downloading the same transcript multiple times
_transcript_cache = {}


class ExtractionError(Exception):
    pass


async def _get_transcript_text(transcript_id: str) -> str:
    """Fetches the raw transcript text from AssemblyAI with caching."""
    if transcript_id in _transcript_cache:
        return _transcript_cache[transcript_id]

    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}",
            headers=headers,
        )

    if response.status_code != 200:
        raise ExtractionError(
            f"Failed to fetch transcript: {response.status_code} — {response.text}"
        )

    data = response.json()
    text = data.get("text", "")
    if not text:
        raise ExtractionError("Transcript text is empty")

    _transcript_cache[transcript_id] = text
    return text


@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception_type(ExtractionError),
    reraise=True,
)
async def run_lemur_prompt(transcript_id: str, prompt: str) -> str:
    """
    Fetches transcript text, then sends it to Groq's API
    using Qwen 3.8 27B for structured data extraction.
    """
    transcript_text = await _get_transcript_text(transcript_id)

    headers = {
        "authorization": f"Bearer {settings.GROQ_API_KEY}",
        "content-type": "application/json",
    }

    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that analyzes meeting transcripts. "
                    "The user will provide you with a transcript and a task. "
                    "Respond only with the requested output, no conversational preamble."
                ),
            },
            {
                "role": "user",
                "content": f"TRANSCRIPT:\n{transcript_text}\n\nTASK:\n{prompt}",
            },
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        raise ExtractionError(
            f"Groq extraction call failed: {response.status_code} — {response.text}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]
