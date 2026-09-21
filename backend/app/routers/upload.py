"""
MeetCore — Upload Router
POST /upload                      — receives file, starts transcription, kicks off pipeline
GET  /upload/status/{meeting_id}  — SSE endpoint for live progress
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.models.meeting import MeetingStatus, UploadResponse
from app.services import assemblyai_service, rag_service, supabase_service, validation
from app.tools import task_extractor, deadline_extractor, decision_extractor, priority_brief

router = APIRouter(prefix="/upload", tags=["ingestion"])
settings = get_settings()

_progress: dict[str, list[dict]] = {}


def _emit(meeting_id: str, step: str, message: str, done: bool = False):
    _progress.setdefault(meeting_id, []).append(
        {"step": step, "message": message, "done": done}
    )
    print(f"[MeetCore] [{meeting_id[:8]}] {step}: {message}", flush=True)


# ─── SSE ──────────────────────────────────────────────────────────────────────

@router.get("/status/{meeting_id}")
async def stream_status(meeting_id: str):
    async def event_generator():
        sent_index = 0
        while True:
            events = _progress.get(meeting_id, [])
            while sent_index < len(events):
                event = events[sent_index]
                yield f"data: {json.dumps(event)}\n\n"
                sent_index += 1
                if event.get("done"):
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── UPLOAD ───────────────────────────────────────────────────────────────────

@router.post("", response_model=UploadResponse)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    file_bytes = await file.read()

    try:
        validation.validate_upload(file.filename, len(file_bytes))
    except validation.ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    meeting_id = str(uuid.uuid4())
    upload_date = datetime.now(timezone.utc)

    try:
        upload_url = await assemblyai_service.upload_file(file_bytes)
        transcript_id = await assemblyai_service.start_transcription(upload_url, meeting_id)
    except assemblyai_service.AssemblyAIError as e:
        raise HTTPException(status_code=502, detail=f"AssemblyAI error: {e}")

    try:
        await supabase_service.create_meeting_record(
            meeting_id=meeting_id,
            transcript_id=transcript_id,
            upload_date=upload_date,
            status=MeetingStatus.TRANSCRIBING,
        )
    except Exception as e:
        print(f"[MeetCore] Supabase create_meeting_record failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    background_tasks.add_task(_run_pipeline, meeting_id, transcript_id, upload_date)
    print(f"[MeetCore] Background task queued for {meeting_id}", flush=True)

    return UploadResponse(
        meeting_id=meeting_id,
        status=MeetingStatus.TRANSCRIBING,
        message="File received. Connect to /upload/status/{meeting_id} for live progress.",
    )


# ─── PIPELINE ─────────────────────────────────────────────────────────────────

async def _run_pipeline(meeting_id: str, transcript_id: str, upload_date: datetime):
    try:
        print(f"[MeetCore] PIPELINE STARTED for {meeting_id}", flush=True)
        _emit(meeting_id, "transcribing", "Transcription in progress...")

        try:
            transcript_data = await _poll_until_complete(meeting_id, transcript_id)
        except Exception as e:
            _emit(meeting_id, "failed", f"Transcription failed: {e}", done=True)
            await supabase_service.update_meeting_status(meeting_id, MeetingStatus.FAILED)
            return

        transcript_text = transcript_data.get("text", "")
        _emit(meeting_id, "transcribed", "Transcription complete.")

        await supabase_service.update_meeting_status(meeting_id, MeetingStatus.EXTRACTING)

        extractors = [
            ("tasks",     "Extracting tasks...",          lambda: task_extractor.extract_tasks(transcript_id)),
            ("deadlines", "Extracting deadlines...",      lambda: deadline_extractor.extract_deadlines(transcript_id, upload_date)),
            ("decisions", "Extracting decisions...",      lambda: decision_extractor.extract_decisions(transcript_id)),
            ("brief",     "Generating priority brief...", lambda: priority_brief.generate_priority_brief(transcript_id)),
        ]

        results = {}
        for name, message, func in extractors:
            _emit(meeting_id, name, message)
            try:
                results[name] = await func()
                await asyncio.sleep(2.0)
            except Exception as e:
                results[name] = e
                print(f"[MeetCore] {name} extractor failed: {e}", flush=True)

        tasks     = results["tasks"]     if not isinstance(results.get("tasks"),     Exception) else []
        deadlines = results["deadlines"] if not isinstance(results.get("deadlines"), Exception) else []
        decisions = results["decisions"] if not isinstance(results.get("decisions"), Exception) else []
        brief     = results["brief"]     if not isinstance(results.get("brief"),     Exception) else "Unable to generate priority brief."

        summary = transcript_text[:500] if transcript_text else "No summary available."
        sentiment_results = transcript_data.get("sentiment_analysis_results", [])
        sentiment_summary = rag_service.summarize_sentiment(sentiment_results)

        _emit(meeting_id, "saving", "Saving results...")
        try:
            await supabase_service.save_meeting_results(
                meeting_id=meeting_id,
                transcript_text=transcript_text,
                summary=summary,
                priority_brief=brief,
                tasks=tasks,
                deadlines=deadlines,
                decisions=decisions,
                chapters=[],
                sentiment_summary=sentiment_summary,
            )
        except Exception as e:
            print(f"[MeetCore] Failed to save results: {e}", flush=True)

        _emit(meeting_id, "embedding", "Building Nio's knowledge base...")
        try:
            await rag_service.chunk_and_store(meeting_id, transcript_text)
        except Exception as e:
            print(f"[MeetCore] RAG chunking failed (non-fatal): {e}", flush=True)

        _emit(meeting_id, "ready", "Meeting ready. Nio is loaded.", done=True)
        await supabase_service.update_meeting_status(meeting_id, MeetingStatus.READY)

    except Exception as e:
        print(f"[MeetCore] PIPELINE CRASHED: {e}", flush=True)
        import traceback
        traceback.print_exc()


# ─── POLLING ──────────────────────────────────────────────────────────────────

async def _poll_until_complete(meeting_id: str, transcript_id: str) -> dict:
    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}
    url = f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"
    poll_interval = 5
    max_polls = 240

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_polls):
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Poll failed: {response.status_code} — {response.text}")

            data = response.json()
            status = data.get("status")

            if status == "completed":
                return data

            if status == "error":
                raise Exception(data.get("error", "Unknown transcription error"))

            elapsed = (attempt + 1) * poll_interval
            _emit(meeting_id, "transcribing", f"Transcribing... ({elapsed}s elapsed)")
            await asyncio.sleep(poll_interval)

    raise Exception("Transcription timed out after 20 minutes.")