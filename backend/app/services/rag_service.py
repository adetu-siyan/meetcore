"""
MeetCore — RAG Service (Ordered Knowledge Framework / Temporal Windowing)
"""
import httpx
from app.core.config import get_settings

settings = get_settings()

CHUNK_SIZE_WORDS = 320
CHUNK_OVERLAP_WORDS = 50
EMBEDDING_DIMENSIONS = 768
BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
)


class EmbeddingError(Exception):
    pass


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_SIZE_WORDS
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS
    return chunks


async def _embed_batch(chunks: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    if not settings.GEMINI_API_KEY:
        raise EmbeddingError("GEMINI_API_KEY not set")

    requests_payload = [
        {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": c}]},
            "outputDimensionality": EMBEDDING_DIMENSIONS,
        }
        for c in chunks
    ]

    response = await client.post(
        BATCH_EMBED_URL,
        json={"requests": requests_payload},
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        },
        timeout=60.0,
    )

    if response.status_code != 200:
        raise EmbeddingError(
            f"Gemini batch embedding failed ({response.status_code}): {response.text}"
        )

    return [item.get("values", []) for item in response.json().get("embeddings", [])]


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    BATCH_SIZE = 50
    all_embeddings = []

    async with httpx.AsyncClient() as client:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            all_embeddings.extend(await _embed_batch(batch, client))

    return all_embeddings


async def chunk_and_store(meeting_id: str, transcript_text: str) -> None:
    from app.services import supabase_service

    if not transcript_text:
        return

    # Wipe existing chunks for this meeting before re-inserting
    await supabase_service.delete_chunks_for_meeting(meeting_id)

    chunks = _chunk_text(transcript_text)
    embeddings = await _embed_texts(chunks)

    BATCH_INSERT_SIZE = 50
    for i in range(0, len(chunks), BATCH_INSERT_SIZE):
        await supabase_service.store_transcript_chunks(
            meeting_id,
            chunks[i : i + BATCH_INSERT_SIZE],
            embeddings[i : i + BATCH_INSERT_SIZE],
            start_index=i,
        )


async def retrieve_relevant_chunks(
    meeting_id: str, question: str, top_k: int = 3, window_radius: int = 1
) -> list[str]:
    from app.services import supabase_service

    query_embedding = (await _embed_texts([question]))[0]
    seed_matches = await supabase_service.search_similar_chunks(
        meeting_id, query_embedding, match_count=top_k
    )

    if not seed_matches:
        return []

    # Since 'chunk_index' is not stored in the database, we skip window expansion
    # and simply return the matched chunks directly to provide RAG context.
    return [match.get("chunk_text", "") for match in seed_matches if match.get("chunk_text")]


def summarize_sentiment(sentiment_results: list[dict] | None) -> str:
    if not sentiment_results:
        return "Neutral tone overall."

    counts: dict[str, int] = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    for r in sentiment_results:
        counts[r.get("sentiment", "NEUTRAL")] = counts.get(r.get("sentiment", "NEUTRAL"), 0) + 1

    dominant = max(counts, key=counts.get)
    return (
        f"Overall tone was mostly {dominant.lower()} "
        f"(Positive: {counts['POSITIVE']}, Neutral: {counts['NEUTRAL']}, Negative: {counts['NEGATIVE']})."
    )
