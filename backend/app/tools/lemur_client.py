import logging
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)
from app.core.config import get_settings
from app.services.assemblyai_service import get_transcript, AssemblyAIError

settings = get_settings()
logger = logging.getLogger("meetcore.lemur")

# In-memory cache to prevent redundant transcript network fetches
_transcript_cache = {}


class ExtractionError(Exception):
    """Raised when extraction from transcript fails."""
    pass


async def _get_transcript_text(transcript_id: str) -> str:
    """
    Retrieves the full transcript text by awaiting AssemblyAI completion status,
    with local in-memory caching.
    """
    if transcript_id in _transcript_cache:
        logger.debug(f"[Cache Hit] Returning cached transcript for {transcript_id}")
        return _transcript_cache[transcript_id]

    try:
        # Poll AssemblyAI until status == 'completed'
        data = await get_transcript(transcript_id)
        text = data.get("text", "").strip()

        if not text:
            raise ExtractionError(f"Transcript {transcript_id} returned empty text.")

        _transcript_cache[transcript_id] = text
        return text

    except AssemblyAIError as e:
        raise ExtractionError(f"Failed to obtain transcript text: {str(e)}") from e


@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception_type(ExtractionError),
    reraise=True,
)
async def run_lemur_prompt(transcript_id: str, prompt: str) -> str:
    """
    Fetches completed transcript text, then routes it to Groq API using
    the configured LLM model for extraction tasks.
    """
    transcript_text = await _get_transcript_text(transcript_id)

    headers = {
        "authorization": f"Bearer {settings.GROQ_API_KEY}",
        "content-type": "application/json",
    }

    model = getattr(settings, "GROQ_REASONING_MODEL", getattr(settings, "GROQ_CHAT_MODEL", "openai/gpt-oss-120b"))

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that analyzes meeting transcripts. "
                    "The user will provide you with a transcript and a task. "
                    "Respond only with the requested output format, with no conversational preamble."
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
        logger.error(f"Groq API error ({response.status_code}): {response.text}")
        raise ExtractionError(
            f"Groq extraction call failed: {response.status_code} — {response.text}"
        )

    data = response.json()
    output = data["choices"][0]["message"]["content"]
    return output