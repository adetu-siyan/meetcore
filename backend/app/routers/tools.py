
# """
# MeetCore — Tools Router
# Endpoints: transcript, summary, action-items, chapters, sentiment
# """
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
# from typing import Optional

# from app.tools.get_transcript import get_transcript
# from app.tools.meeting_summary import summarize_meeting
# from app.tools.action_items import get_action_items
# from app.tools.meeting_chapters import get_meeting_chapters
# from app.tools.meeting_sentiment import get_meeting_sentiment

# router = APIRouter(prefix="/tools", tags=["tools"])


# class ToolRequest(BaseModel):
#     meeting_id: Optional[str] = None
#     transcript_id: Optional[str] = None

#     @property
#     def id(self) -> str:
#         res = self.meeting_id or self.transcript_id
#         if not res:
#             raise ValueError("meeting_id is required")
#         return res


# @router.post("/transcript")
# async def transcript(req: ToolRequest):
#     try:
#         text = await get_transcript(req.id)
#         return {"transcript": text}
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/summary")
# async def summary(req: ToolRequest):
#     try:
#         transcript_text = await get_transcript(req.id)
#         data = await summarize_meeting(transcript_text)
#         return data
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/action-items")
# async def action_items(req: ToolRequest):
#     try:
#         transcript_text = await get_transcript(req.id)
#         tasks = await get_action_items(transcript_text)
#         return {"items": [t.dict() for t in tasks]}
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/chapters")
# async def chapters(req: ToolRequest):
#     try:
#         data = await get_meeting_chapters(req.id)
#         return {"chapters": data}
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/sentiment")
# async def sentiment(req: ToolRequest):
#     try:
#         data = await get_meeting_sentiment(req.id)
#         return data
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

"""
MeetCore — Tools Router
Handles visual drawer endpoints and underground background actions (like sending emails via Brevo).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import supabase_service, email_service

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolRequest(BaseModel):
    meeting_id: str
    transcript_id: str | None = None
    recipient: str | None = None


class SendEmailBackgroundRequest(BaseModel):
    meeting_id: str
    recipient: str | None = None
    include_summary: bool = True
    include_tasks: bool = True
    include_decisions: bool = False


# ── 1. Transcript Visual Tool ─────────────────────────────────────────────────
@router.post("/transcript")
async def get_transcript_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    text = meeting.get("transcript_text") or ""
    if not text:
        raise HTTPException(status_code=404, detail="Transcript text not available yet")

    return {"transcript": text}


# ── 2. Summary Visual Tool ────────────────────────────────────────────────────
@router.post("/summary")
async def get_summary_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    summary_text = meeting.get("summary") or ""
    decisions = [d.get("decision", "") for d in (meeting.get("decisions") or [])]
    key_points = [p.strip() for p in summary_text.split("\n") if p.strip()] if summary_text else []

    return {
        "key_points": key_points,
        "decisions": decisions,
        "open_questions": [],
    }


# ── 3. Action Items Visual Tool ───────────────────────────────────────────────
@router.post("/action-items")
async def get_action_items_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    tasks = meeting.get("tasks") or []
    return {
        "items": [
            {
                "description": t.get("description", ""),
                "owner": t.get("owner"),
                "deadline": t.get("deadline"),
            }
            for t in tasks
        ]
    }


# ── 4. Draft Email Visual Tool ────────────────────────────────────────────────
@router.post("/draft-email")
async def draft_email_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    summary = meeting.get("summary") or "No summary recorded."
    tasks = meeting.get("tasks") or []

    task_bullets = "\n".join(
        [
            f"• {t.get('description', '')} (Owner: {t.get('owner') or 'Unassigned'} | Due: {t.get('deadline') or 'TBD'})"
            for t in tasks
        ]
    ) or "• No urgent action items."

    draft_body = (
        f"Hi team,\n\n"
        f"Here is a summary of our discussion and the next steps from our meeting:\n\n"
        f"Summary:\n{summary}\n\n"
        f"Key Action Items:\n{task_bullets}\n\n"
        f"Best regards,\nNio"
    )

    return {
        "subject": "Executive Briefing: Meeting Summary & Next Steps",
        "to": req.recipient or "team@meetcore.ai",
        "body": draft_body,
    }


# ── 5. Underground Background Email Dispatch (Brevo) ──────────────────────────
@router.post("/send-email")
async def send_email_background_tool(req: SendEmailBackgroundRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    subject_parts = []
    if req.include_summary:
        subject_parts.append("Summary")
    if req.include_tasks:
        subject_parts.append("Action Items")
    if req.include_decisions:
        subject_parts.append("Decisions")
    subject_label = " & ".join(subject_parts) or "Meeting Briefing"

    success = await email_service.send_meeting_email_brevo(
        to_email=req.recipient,
        subject=subject_label,
        summary=meeting.get("summary") if req.include_summary else None,
        tasks=meeting.get("tasks") if req.include_tasks else None,
        decisions=meeting.get("decisions") if req.include_decisions else None,
    )

    if not success:
        return {"success": False, "message": "Failed to send email."}

    return {
        "success": True,
        "message": "Email sent.",
        "done_speech": f"Done! The {subject_label.lower()} has been sent to your email.",
    }