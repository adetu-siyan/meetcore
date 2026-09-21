"""
MeetCore — Supabase Service
Manages meeting state, transcript persistence, and RAG lookups.
Resilient against connection drops and schema ID variations.
"""
import uuid
import time
from datetime import datetime
from typing import Any, Callable
from postgrest.exceptions import APIError
from supabase import create_client, Client
from app.core.config import get_settings
from app.models.meeting import MeetingStatus, Task, Deadline, Decision

settings = get_settings()
_client: Client | None = None


def is_valid_uuid(val: Any) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _make_client() -> Client:
    # Uses SUPABASE_SERVICE_KEY from settings to avoid AttributeError
    return create_client(
        settings.SUPABASE_URL,
        getattr(settings, "SUPABASE_SERVICE_KEY", getattr(settings, "SUPABASE_KEY", None)),
    )


def get_client() -> Client:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def _reset_client() -> Client:
    global _client
    _client = _make_client()
    return _client


def _execute_with_retry(fn: Callable, retries: int = 3, delay: float = 0.5):
    for attempt in range(retries):
        try:
            return fn()
        except APIError as e:
            # Catch Postgres 22P02 (invalid UUID) immediately rather than crashing
            if isinstance(e.args, tuple) and len(e.args) > 0 and isinstance(e.args[0], dict):
                if e.args[0].get("code") == "22P02":
                    return None
            raise
        except Exception as e:
            err = str(e).lower()
            is_connection_err = any(x in err for x in (
                "ssl", "sslv3", "bad record", "read error",
                "connection", "timeout", "eof",
                "server disconnected", "remoteprotocol",
            ))
            if is_connection_err and attempt < retries - 1:
                print(
                    f"[Supabase] Connection error (attempt {attempt + 1}), "
                    f"resetting client: {e}",
                    flush=True,
                )
                _reset_client()
                time.sleep(delay * (attempt + 1))
                continue
            raise


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

async def create_meeting_record(
    meeting_id: str,
    transcript_id: str,
    upload_date: datetime,
    status: MeetingStatus,
) -> None:
    client = get_client()
    _execute_with_retry(lambda: client.table("meetings").insert({
        "meeting_id": meeting_id,
        "transcript_id": transcript_id,
        "upload_date": upload_date.isoformat(),
        "status": status.value,
    }).execute())


async def update_meeting_status(meeting_id: str, status: MeetingStatus) -> None:
    client = get_client()
    _execute_with_retry(lambda: client.table("meetings").update(
        {"status": status.value}
    ).eq("meeting_id", meeting_id).execute())


async def save_meeting_results(
    meeting_id: str,
    transcript_text: str,
    summary: str,
    priority_brief: str,
    tasks: list[Task],
    deadlines: list[Deadline],
    decisions: list[Decision],
    chapters: list[dict],
    sentiment_summary: str,
) -> None:
    client = get_client()
    _execute_with_retry(lambda: client.table("meetings").update({
        "transcript_text": transcript_text,
        "summary": summary,
        "priority_brief": priority_brief,
        "tasks": [t.model_dump() for t in tasks],
        "deadlines": [d.model_dump() for d in deadlines],
        "decisions": [d.model_dump() for d in decisions],
        "chapters": chapters,
        "sentiment_summary": sentiment_summary,
        "status": MeetingStatus.READY.value,
    }).eq("meeting_id", meeting_id).execute())


async def get_meeting(meeting_id: str) -> dict | None:
    """
    Safely retrieves meeting records. Queries both 'meeting_id' (text slug)
    and 'id' (UUID) without triggering 22P02 errors.
    """
    if not meeting_id:
        return None

    def _get():
        client = get_client()
        # 1. Primary check: match by business slug column 'meeting_id' (string)
        res = client.table("meetings").select("*").eq("meeting_id", str(meeting_id)).execute()
        if res.data:
            return res.data[0]

        # 2. Secondary check: if it is a valid UUID, check primary key 'id'
        if is_valid_uuid(meeting_id):
            res_uuid = client.table("meetings").select("*").eq("id", str(meeting_id)).execute()
            if res_uuid.data:
                return res_uuid.data[0]

        return None

    try:
        return _execute_with_retry(_get)
    except Exception as e:
        print(f"[Supabase get_meeting]: {e}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Transcript chunks
# ---------------------------------------------------------------------------

async def delete_chunks_for_meeting(meeting_id: str) -> None:
    def _delete():
        client = get_client()
        client.table("transcript_chunks").delete().eq(
            "meeting_id", meeting_id
        ).execute()

    _execute_with_retry(_delete)


async def store_transcript_chunks(
    meeting_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    start_index: int = 0,
) -> None:
    client = get_client()
    rows = [
        {
            "meeting_id": meeting_id,
            "chunk_text": chunk,
            "embedding": embedding,
            "chunk_index": start_index + i,
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    _execute_with_retry(lambda: client.table("transcript_chunks").insert(rows).execute())


async def search_similar_chunks(
    meeting_id: str,
    query_embedding: list[float],
    match_count: int = 4,
) -> list[dict]:
    def _search():
        client = get_client()
        result = client.rpc("match_transcript_chunks", {
            "query_embedding": query_embedding,
            "target_meeting_id": meeting_id,
            "match_count": match_count,
        }).execute()
        return result.data or []

    try:
        return _execute_with_retry(_search) or []
    except Exception as e:
        print(f"[Supabase search_similar_chunks]: {e}", flush=True)
        return []


async def get_chunks_in_range(
    meeting_id: str,
    start_idx: int,
    end_idx: int,
) -> list[dict]:
    def _fetch():
        client = get_client()
        result = (
            client.table("transcript_chunks")
            .select("chunk_index, chunk_text")
            .eq("meeting_id", meeting_id)
            .gte("chunk_index", start_idx)
            .lte("chunk_index", end_idx)
            .order("chunk_index")
            .execute()
        )
        return result.data or []

    try:
        return _execute_with_retry(_fetch) or []
    except Exception as e:
        print(f"[Supabase get_chunks_in_range]: {e}", flush=True)
        return []

# """
# MeetCore — Supabase Service
# """
# import time
# from datetime import datetime
# from supabase import create_client, Client
# from app.core.config import get_settings
# from app.models.meeting import MeetingStatus, Task, Deadline, Decision

# settings = get_settings()
# _client: Client | None = None


# def _make_client() -> Client:
#     return create_client(
#         settings.SUPABASE_URL,
#         settings.SUPABASE_SERVICE_KEY,
#     )


# def get_client() -> Client:
#     global _client
#     if _client is None:
#         _client = _make_client()
#     return _client


# def _reset_client() -> Client:
#     global _client
#     _client = _make_client()
#     return _client


# def _execute_with_retry(fn, retries: int = 3, delay: float = 0.5):
#     for attempt in range(retries):
#         try:
#             return fn()
#         except Exception as e:
#             err = str(e).lower()
#             is_connection_err = any(x in err for x in (
#                 "ssl", "sslv3", "bad record", "read error",
#                 "connection", "timeout", "eof",
#                 "server disconnected", "remoteprotocol",
#             ))
#             if is_connection_err and attempt < retries - 1:
#                 print(
#                     f"[Supabase] Connection error (attempt {attempt + 1}), "
#                     f"resetting client: {e}",
#                     flush=True,
#                 )
#                 _reset_client()
#                 time.sleep(delay * (attempt + 1))
#                 continue
#             raise


# # ---------------------------------------------------------------------------
# # Meetings
# # ---------------------------------------------------------------------------

# async def create_meeting_record(
#     meeting_id: str,
#     transcript_id: str,
#     upload_date: datetime,
#     status: MeetingStatus,
# ) -> None:
#     client = get_client()
#     _execute_with_retry(lambda: client.table("meetings").insert({
#         "meeting_id": meeting_id,
#         "transcript_id": transcript_id,
#         "upload_date": upload_date.isoformat(),
#         "status": status.value,
#     }).execute())


# async def update_meeting_status(meeting_id: str, status: MeetingStatus) -> None:
#     client = get_client()
#     _execute_with_retry(lambda: client.table("meetings").update(
#         {"status": status.value}
#     ).eq("meeting_id", meeting_id).execute())


# async def save_meeting_results(
#     meeting_id: str,
#     transcript_text: str,
#     summary: str,
#     priority_brief: str,
#     tasks: list[Task],
#     deadlines: list[Deadline],
#     decisions: list[Decision],
#     chapters: list[dict],
#     sentiment_summary: str,
# ) -> None:
#     client = get_client()
#     _execute_with_retry(lambda: client.table("meetings").update({
#         "transcript_text": transcript_text,
#         "summary": summary,
#         "priority_brief": priority_brief,
#         "tasks": [t.model_dump() for t in tasks],
#         "deadlines": [d.model_dump() for d in deadlines],
#         "decisions": [d.model_dump() for d in decisions],
#         "chapters": chapters,
#         "sentiment_summary": sentiment_summary,
#         "status": MeetingStatus.READY.value,
#     }).eq("meeting_id", meeting_id).execute())


# async def get_meeting(meeting_id: str) -> dict | None:
#     def _get():
#         client = get_client()
#         result = client.table("meetings").select("*").eq(
#             "meeting_id", meeting_id
#         ).execute()
#         return result.data[0] if result.data else None

#     return _execute_with_retry(_get)


# # ---------------------------------------------------------------------------
# # Transcript chunks
# # ---------------------------------------------------------------------------

# async def delete_chunks_for_meeting(meeting_id: str) -> None:
#     def _delete():
#         client = get_client()
#         client.table("transcript_chunks").delete().eq(
#             "meeting_id", meeting_id
#         ).execute()

#     _execute_with_retry(_delete)


# async def store_transcript_chunks(
#     meeting_id: str,
#     chunks: list[str],
#     embeddings: list[list[float]],
#     start_index: int = 0,
# ) -> None:
#     client = get_client()
#     rows = [
#         {
#             "meeting_id": meeting_id,
#             "chunk_text": chunk,
#             "embedding": embedding,
#             "chunk_index": start_index + i,
#         }
#         for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
#     ]
#     _execute_with_retry(lambda: client.table("transcript_chunks").insert(rows).execute())


# async def search_similar_chunks(
#     meeting_id: str,
#     query_embedding: list[float],
#     match_count: int = 4,
# ) -> list[dict]:
#     def _search():
#         client = get_client()
#         result = client.rpc("match_transcript_chunks", {
#             "query_embedding": query_embedding,
#             "target_meeting_id": meeting_id,
#             "match_count": match_count,
#         }).execute()
#         return result.data or []

#     return _execute_with_retry(_search)


# async def get_chunks_in_range(
#     meeting_id: str,
#     start_idx: int,
#     end_idx: int,
# ) -> list[dict]:
#     def _fetch():
#         client = get_client()
#         result = (
#             client.table("transcript_chunks")
#             .select("chunk_index, chunk_text")
#             .eq("meeting_id", meeting_id)
#             .gte("chunk_index", start_idx)
#             .lte("chunk_index", end_idx)
#             .order("chunk_index")
#             .execute()
#         )
#         return result.data or []

#     return _execute_with_retry(_fetch)