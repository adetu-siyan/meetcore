# """
# MeetCore — RAG Service
# Transcript chunking, Gemini embedding (gemini-embedding-001), and pgvector retrieval for Nio.

# text-embedding-004 was shut down January 14 2026.
# Replaced with gemini-embedding-001 — same API shape, better quality.
# outputDimensionality: 768 keeps existing pgvector column compatible.
# """
# import asyncio
# import httpx
# from app.core.config import get_settings

# settings = get_settings()

# CHUNK_SIZE_WORDS = 200
# CHUNK_OVERLAP_WORDS = 40
# EMBEDDING_DIMENSIONS = 768  # matches pgvector column; gemini-embedding-001 default is 3072
# EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"


# class EmbeddingError(Exception):
#     """Exception raised for errors occurring during embedding operations.
    
#     This exception is used to signal issues such as missing configuration, HTTP failures, or malformed responses from the embedding service."""
#     pass


# # ---------------------------------------------------------------------------
# # Chunking
# # ---------------------------------------------------------------------------

# def _chunk_text(text: str) -> list[str]:
#     """Split a string into overlapping word chunks.
    
#     Args:
#         text (str): The input text to be divided into chunks.
    
#     Returns:
#         list[str]: A list where each element is a chunk of the original text containing up to ``CHUNK_SIZE_WORDS`` words, with an overlap of ``CHUNK_OVERLAP_WORDS`` words between consecutive chunks."""
#     words = text.split()
#     chunks = []
#     start = 0
#     while start < len(words):
#         end = start + CHUNK_SIZE_WORDS
#         chunks.append(" ".join(words[start:end]))
#         start += CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS
#     return chunks


# # ---------------------------------------------------------------------------
# # Embedding
# # ---------------------------------------------------------------------------

# async def _embed_single(text: str, client: httpx.AsyncClient) -> list[float]:
#     """Asynchronously obtain an embedding vector for a single piece of text using the Gemini embedding API.
    
#     Args:
#         text (str): The text to embed.
#         client (httpx.AsyncClient): An asynchronous HTTP client used to perform the request.
    
#     Returns:
#         list[float]: The embedding vector returned by the API.
    
#     Raises:
#         EmbeddingError: If the Gemini API key is not configured, the HTTP request fails (non‑200 status), or the response does not contain embedding values."""
#     if not settings.GEMINI_API_KEY:
#         raise EmbeddingError("GEMINI_API_KEY not set")

#     payload = {
#         "model": "models/gemini-embedding-001",
#         "content": {"parts": [{"text": text}]},
#         "outputDimensionality": EMBEDDING_DIMENSIONS,
#     }
#     headers = {
#         "Content-Type": "application/json",
#         "x-goog-api-key": settings.GEMINI_API_KEY,
#     }

#     response = await client.post(EMBED_URL, json=payload, headers=headers, timeout=30.0)

#     if response.status_code != 200:
#         raise EmbeddingError(
#             f"Gemini embedding failed: {response.status_code} — {response.text}"
#         )

#     values = response.json().get("embedding", {}).get("values")
#     if not values:
#         raise EmbeddingError("Gemini returned no embedding values")

#     return values


# async def _embed_texts(texts: list[str]) -> list[list[float]]:
#     """
#     Embeds a list of texts concurrently, capped at 5 in-flight requests
#     to stay within Gemini's rate limits.
#     """
#     if not texts:
#         return []

#     semaphore = asyncio.Semaphore(5)

#     async def _bounded(text: str, client: httpx.AsyncClient) -> list[float]:
#         """Acquire a semaphore before embedding a single piece of text.
        
#         Args:
#             text (str): The text to embed.
#             client (httpx.AsyncClient): An asynchronous HTTP client used by the underlying embedding function.
        
#         Returns:
#             list[float]: The embedding vector returned by ``_embed_single``.
        
#         Raises:
#             Any exception raised by ``_embed_single`` or by acquiring the semaphore will propagate to the caller.
        
#         Side Effects:
#             Acquires and releases the module‑level ``semaphore`` while the embedding request is in progress."""
#         async with semaphore:
#             return await _embed_single(text, client)

#     async with httpx.AsyncClient() as client:
#         return await asyncio.gather(*[_bounded(t, client) for t in texts])


# # ---------------------------------------------------------------------------
# # Public interface
# # ---------------------------------------------------------------------------

# async def chunk_and_store(meeting_id: str, transcript_text: str) -> None:
#     """
#     Chunks the transcript, embeds each chunk, and stores everything in
#     Supabase for Nio's RAG retrieval.
#     """
#     from app.services import supabase_service

#     if not transcript_text:
#         return

#     chunks = _chunk_text(transcript_text)
#     embeddings = await _embed_texts(chunks)
#     await supabase_service.store_transcript_chunks(meeting_id, chunks, embeddings)


# async def retrieve_relevant_chunks(
#     meeting_id: str, question: str, top_k: int = 5
# ) -> list[str]:
#     """
#     Embeds the user's question and retrieves the most semantically
#     similar transcript chunks from pgvector for Nio's context window.
#     """
#     from app.services import supabase_service

#     query_embedding = (await _embed_texts([question]))[0]
#     return await supabase_service.search_similar_chunks(meeting_id, query_embedding, top_k)


# # ---------------------------------------------------------------------------
# # Sentiment summary (unchanged)
# # ---------------------------------------------------------------------------

# def summarize_sentiment(sentiment_results: list[dict]) -> str:
#     """Summarize a collection of sentiment analysis results.
    
#     Args:
#         sentiment_results (list[dict]): A list where each element is a dictionary containing a "sentiment" key whose value is a string such as "POSITIVE", "NEGATIVE", or "NEUTRAL". If the key is missing, the sentiment is treated as "NEUTRAL".
    
#     Returns:
#         str: A human‑readable summary. If the input list is empty, returns "No strong sentiment detected." Otherwise returns a sentence of the form "Overall tone was mostly <sentiment> (<counts>)" where <sentiment> is the dominant sentiment in lower case and <counts> is the dictionary of sentiment frequencies."""
#     if not sentiment_results:
#         return "No strong sentiment detected."

#     counts: dict[str, int] = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
#     for r in sentiment_results:
#         sentiment = r.get("sentiment", "NEUTRAL")
#         counts[sentiment] = counts.get(sentiment, 0) + 1

#     dominant = max(counts, key=counts.get)
#     return f"Overall tone was mostly {dominant.lower()} ({counts})."

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

    ranges = []
    for match in seed_matches:
        idx = match.get("chunk_index", 0)
        ranges.append((max(0, idx - window_radius), idx + window_radius))

    ranges.sort(key=lambda x: x[0])
    merged_ranges = []
    for r in ranges:
        if not merged_ranges or merged_ranges[-1][1] < r[0]:
            merged_ranges.append(r)
        else:
            merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], r[1]))

    expanded_excerpts = []
    for start_idx, end_idx in merged_ranges:
        nodes = await supabase_service.get_chunks_in_range(meeting_id, start_idx, end_idx)
        if nodes:
            expanded_excerpts.append(" ".join(n["chunk_text"] for n in nodes))

    return expanded_excerpts


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