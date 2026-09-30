# import asyncio
# import logging
# import uuid
# from datetime import datetime
# from typing import Dict, List, Any

# from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException

# from app.services.assemblyai_service import (
#     upload_audio_bytes,
#     create_transcript_job,
#     get_transcript,
# )
# from app.services import supabase_service
# from app.models.meeting import MeetingStatus
# from app.tools.task_extractor import extract_tasks
# from app.tools.deadline_extractor import extract_deadlines
# from app.tools.decision_extractor import extract_decisions
# from app.tools.priority_brief import generate_priority_brief

# router = APIRouter(prefix="/upload", tags=["Upload & Pipeline"])
# logger = logging.getLogger("meetcore.upload")

# _progress: Dict[str, List[Dict[str, Any]]] = {}
# _pipeline_results: Dict[str, Dict[str, Any]] = {}


# def _emit(meeting_id: str, step: str, message: str, done: bool = False, error: bool = False):
#     event = {
#         "step": step,
#         "message": message,
#         "done": done,
#         "error": error,
#         "timestamp": datetime.utcnow().isoformat(),
#     }
#     _progress.setdefault(meeting_id, []).append(event)
#     logger.info(f"[{meeting_id[:8]}] step='{step}' msg='{message}' done={done}")


# async def _run_extraction_pipeline(meeting_id: str, file_bytes: bytes, filename: str):
#     try:
#         _emit(meeting_id, "uploading", "Uploading audio to transcription engine...")
#         audio_url = await upload_audio_bytes(file_bytes)

#         _emit(meeting_id, "transcribing", "Submitting audio for transcription...")
#         transcript_id = await create_transcript_job(audio_url)

#         _emit(meeting_id, "transcribing", f"Transcribing audio (ID: {transcript_id})...")
#         transcript_data = await get_transcript(transcript_id)
#         transcript_text = transcript_data.get("text", "")
#         upload_date = datetime.utcnow()

#         _emit(meeting_id, "extracting", "Extracting tasks, deadlines, decisions, and priority brief...")

#         tasks, deadlines, decisions, brief = await asyncio.gather(
#             extract_tasks(transcript_id),
#             extract_deadlines(transcript_id, upload_date),
#             extract_decisions(transcript_id),
#             generate_priority_brief(transcript_id),
#             return_exceptions=False,
#         )

#         # Save to Supabase so Nio can find the meeting
#         _emit(meeting_id, "saving", "Saving results...")
#         try:
#             await supabase_service.create_meeting_record(
#                 meeting_id=meeting_id,
#                 transcript_id=transcript_id,
#                 upload_date=upload_date,
#                 status=MeetingStatus.READY,
#             )
#             await supabase_service.save_meeting_results(
#                 meeting_id=meeting_id,
#                 transcript_text=transcript_text,
#                 summary="",
#                 priority_brief=brief if isinstance(brief, str) else "",
#                 tasks=tasks,
#                 deadlines=deadlines,
#                 decisions=decisions,
#                 chapters=[],
#                 sentiment_summary="",
#             )
#         except Exception as db_err:
#             logger.warning(f"[{meeting_id[:8]}] Supabase save failed (non-fatal): {db_err}")

#         # Also store in-memory for status polling
#         _pipeline_results[meeting_id] = {
#             "meeting_id": meeting_id,
#             "filename": filename,
#             "transcript_id": transcript_id,
#             "transcript_text": transcript_text,
#             "tasks": [t.dict() if hasattr(t, "dict") else t for t in tasks],
#             "deadlines": [d.dict() if hasattr(d, "dict") else d for d in deadlines],
#             "decisions": [dec.dict() if hasattr(dec, "dict") else dec for dec in decisions],
#             "priority_brief": brief,
#             "completed_at": datetime.utcnow().isoformat(),
#         }

#         _emit(meeting_id, "completed", "Pipeline finished successfully!", done=True)

#     except Exception as exc:
#         logger.exception(f"Pipeline failure for meeting {meeting_id}: {str(exc)}")
#         _emit(meeting_id, "error", f"Pipeline error: {str(exc)}", done=True, error=True)


# @router.post("")
# async def upload_file(
#     background_tasks: BackgroundTasks,
#     file: UploadFile = File(...),
# ):
#     meeting_id = str(uuid.uuid4())
#     file_bytes = await file.read()

#     if not file_bytes:
#         raise HTTPException(status_code=400, detail="Uploaded file is empty.")

#     logger.info(f"[MeetCore] Background task queued for {meeting_id} ({file.filename})")
#     _progress[meeting_id] = []
#     _emit(meeting_id, "init", "File received, queuing pipeline...")
#     background_tasks.add_task(_run_extraction_pipeline, meeting_id, file_bytes, file.filename)

#     return {
#         "status": "queued",
#         "meeting_id": meeting_id,
#         "filename": file.filename,
#     }


# @router.get("/status/{meeting_id}")
# async def get_status(meeting_id: str):
#     events = _progress.get(meeting_id, [])
#     result = _pipeline_results.get(meeting_id)

#     return {
#         "meeting_id": meeting_id,
#         "events": events,
#         "is_complete": any(e.get("done") for e in events),
#         "result": result,
#     }

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException

from app.services.assemblyai_service import (
    upload_audio_bytes,
    create_transcript_job,
    get_transcript,
)
from app.services import supabase_service
from app.models.meeting import MeetingStatus
from app.tools.task_extractor import extract_tasks
from app.tools.deadline_extractor import extract_deadlines
from app.tools.decision_extractor import extract_decisions
from app.tools.priority_brief import generate_priority_brief

router = APIRouter(prefix="/upload", tags=["Upload & Pipeline"])
logger = logging.getLogger("meetcore.upload")

_progress: Dict[str, List[Dict[str, Any]]] = {}
_pipeline_results: Dict[str, Dict[str, Any]] = {}


def _emit(meeting_id: str, step: str, message: str, done: bool = False, error: bool = False):
    event = {
        "step": step,
        "message": message,
        "done": done,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _progress.setdefault(meeting_id, []).append(event)
    logger.info(f"[{meeting_id[:8]}] step='{step}' msg='{message}' done={done}")


async def _run_extraction_pipeline(meeting_id: str, file_bytes: bytes, filename: str):
    try:
        _emit(meeting_id, "uploading", "Uploading audio to transcription engine...")
        audio_url = await upload_audio_bytes(file_bytes)

        _emit(meeting_id, "transcribing", "Submitting audio for transcription & AI feature analysis...")
        transcript_id = await create_transcript_job(audio_url)

        _emit(meeting_id, "transcribing", f"Processing audio & AssemblyAI intelligence (ID: {transcript_id})...")
        transcript_data = await get_transcript(transcript_id)

        # Extract AssemblyAI Audio Intelligence Output
        transcript_text = transcript_data.get("text", "")
        aai_summary = transcript_data.get("summary", "")
        aai_chapters = transcript_data.get("chapters", [])
        aai_highlights = transcript_data.get("auto_highlights_result", {}).get("results", [])
        aai_entities = transcript_data.get("entities", [])
        aai_sentiments = transcript_data.get("sentiment_analysis_results", [])
        aai_utterances = transcript_data.get("utterances", [])

        upload_date = datetime.utcnow()

        _emit(meeting_id, "extracting", "Extracting tasks, deadlines, decisions, and priority brief...")

        tasks, deadlines, decisions, brief = await asyncio.gather(
            extract_tasks(transcript_id),
            extract_deadlines(transcript_id, upload_date),
            extract_decisions(transcript_id),
            generate_priority_brief(transcript_id),
            return_exceptions=False,
        )

        # Save to Supabase
        _emit(meeting_id, "saving", "Saving meeting transcript and intelligence results...")
        try:
            await supabase_service.create_meeting_record(
                meeting_id=meeting_id,
                transcript_id=transcript_id,
                upload_date=upload_date,
                status=MeetingStatus.READY,
            )
            await supabase_service.save_meeting_results(
                meeting_id=meeting_id,
                transcript_text=transcript_text,
                summary=aai_summary,
                priority_brief=brief if isinstance(brief, str) else "",
                tasks=tasks,
                deadlines=deadlines,
                decisions=decisions,
                chapters=aai_chapters,
                sentiment_summary=str(aai_sentiments[:5]) if aai_sentiments else "",
            )
        except Exception as db_err:
            logger.warning(f"[{meeting_id[:8]}] Supabase save failed (non-fatal): {db_err}")

        # Store in-memory for status polling
        _pipeline_results[meeting_id] = {
            "meeting_id": meeting_id,
            "filename": filename,
            "transcript_id": transcript_id,
            "transcript_text": transcript_text,
            "summary": aai_summary,
            "chapters": aai_chapters,
            "highlights": aai_highlights,
            "entities": aai_entities,
            "sentiments": aai_sentiments,
            "utterances": aai_utterances,
            "tasks": [t.dict() if hasattr(t, "dict") else t for t in tasks],
            "deadlines": [d.dict() if hasattr(d, "dict") else d for d in deadlines],
            "decisions": [dec.dict() if hasattr(dec, "dict") else dec for dec in decisions],
            "priority_brief": brief,
            "completed_at": datetime.utcnow().isoformat(),
        }

        _emit(meeting_id, "completed", "Pipeline finished successfully!", done=True)

    except Exception as exc:
        logger.exception(f"Pipeline failure for meeting {meeting_id}: {str(exc)}")
        _emit(meeting_id, "error", f"Pipeline error: {str(exc)}", done=True, error=True)


@router.post("")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    meeting_id = str(uuid.uuid4())
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info(f"[MeetCore] Background task queued for {meeting_id} ({file.filename})")
    _progress[meeting_id] = []
    _emit(meeting_id, "init", "File received, queuing pipeline...")
    background_tasks.add_task(_run_extraction_pipeline, meeting_id, file_bytes, file.filename)

    return {
        "status": "queued",
        "meeting_id": meeting_id,
        "filename": file.filename,
    }


@router.get("/status/{meeting_id}")
async def get_status(meeting_id: str):
    events = _progress.get(meeting_id, [])
    result = _pipeline_results.get(meeting_id)

    return {
        "meeting_id": meeting_id,
        "events": events,
        "is_complete": any(e.get("done") for e in events),
        "result": result,
    }