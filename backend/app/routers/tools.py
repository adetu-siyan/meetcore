"""
MeetCore — Tools Router
Handles visual drawer endpoints and underground background actions.
Safeguards null parameter edge cases and non-UUID database crashes.
"""
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import AsyncGroq
from app.services import supabase_service, email_service
from app.core.config import get_settings

router   = APIRouter(prefix="/tools", tags=["tools"])
settings = get_settings()


class ToolRequest(BaseModel):
    meeting_id:    str
    transcript_id: str | None = None
    recipient:     str | None = None
    instruction:   str | None = None


class SendEmailBackgroundRequest(BaseModel):
    meeting_id:        str
    recipient:         str | None = None
    include_summary:   bool = True
    include_tasks:     bool = True
    include_decisions: bool = False


def _clean_and_parse_json(raw: str) -> dict:
    """Strips markdown fences and locates valid JSON objects."""
    clean = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _build_meeting_context(meeting: dict) -> str:
    summary    = meeting.get("summary") or ""
    tasks      = meeting.get("tasks") or []
    decisions  = meeting.get("decisions") or []
    transcript = meeting.get("transcript_text") or ""

    task_lines = "\n".join(
        f"- {t.get('description', '')} (Owner: {t.get('owner', 'Unassigned')}, Due: {t.get('deadline', 'TBD')})"
        for t in tasks
    ) or "None"

    decision_lines = "\n".join(
        f"- {d.get('decision', '')}" for d in decisions
    ) or "None"

    return f"""Meeting Summary:
{summary}

Action Items:
{task_lines}

Decisions:
{decision_lines}

Transcript Excerpt:
{transcript[:3000] if transcript else "Not available"}""".strip()


async def _llm_json(messages: list[dict], max_tokens: int = 800) -> dict:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=15.0)
    completion = await client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content.strip()
    return _clean_and_parse_json(content)


# ── 1. Transcript ─────────────────────────────────────────────────────────────

@router.post("/transcript")
async def get_transcript_tool(req: ToolRequest):
    if not req.meeting_id:
        raise HTTPException(status_code=400, detail="Missing meeting_id")

    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    text = meeting.get("transcript_text") or ""
    if not text:
        raise HTTPException(status_code=404, detail="Transcript not available yet")
    return {"transcript": text}


# ── 2. Summary ────────────────────────────────────────────────────────────────

@router.post("/summary")
async def get_summary_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    instruction = req.instruction or ""
    summary     = meeting.get("summary") or ""
    decisions   = meeting.get("decisions") or []

    if instruction:
        context = _build_meeting_context(meeting)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Nio, a meeting assistant. Using the meeting context, "
                    "produce a summary exactly as instructed. "
                    "Respond ONLY with a JSON object:\n"
                    '{"key_points": ["..."], "decisions": ["..."], "open_questions": ["..."]}\n'
                    "Each array must contain plain strings."
                ),
            },
            {
                "role": "user",
                "content": f"Meeting context:\n{context}\n\nInstruction: {instruction}",
            },
        ]
        try:
            data = await _llm_json(messages)
            return {
                "key_points":     data.get("key_points", []),
                "decisions":      data.get("decisions", []),
                "open_questions": data.get("open_questions", []),
            }
        except Exception as e:
            print(f"[summary fallback]: {e}", flush=True)

    key_points = [p.strip() for p in summary.split("\n") if p.strip()] if summary else []
    return {
        "key_points":     key_points,
        "decisions":      [d.get("decision", "") for d in decisions],
        "open_questions": [],
    }


# ── 3. Action Items ───────────────────────────────────────────────────────────

@router.post("/action-items")
async def get_action_items_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    instruction = req.instruction or ""
    tasks       = meeting.get("tasks") or []

    if instruction:
        context  = _build_meeting_context(meeting)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Nio, a meeting assistant. Using the meeting context, "
                    "extract or generate action items exactly as instructed. "
                    "Respond ONLY with a JSON object:\n"
                    '{"items": [{"description": "...", "owner": "...", "deadline": "..."}]}'
                ),
            },
            {
                "role": "user",
                "content": f"Meeting context:\n{context}\n\nInstruction: {instruction}",
            },
        ]
        try:
            data = await _llm_json(messages)
            return {"items": data.get("items", [])}
        except Exception as e:
            print(f"[action-items fallback]: {e}", flush=True)

    return {
        "items": [
            {
                "description": t.get("description", ""),
                "owner":       t.get("owner"),
                "deadline":    t.get("deadline"),
            }
            for t in tasks
        ]
    }


# ── 4. Dynamic Draft Email ───────────────────────────────────────────────────

@router.post("/draft-email")
async def draft_email_tool(req: ToolRequest):
    meeting = await supabase_service.get_meeting(req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    instruction = (req.instruction or "").strip()
    context = _build_meeting_context(meeting)

    messages = [
        {
            "role": "system",
            "content": (
                "You are Nio, an executive meeting assistant. "
                "Draft an email specifically tailored to the USER'S DIRECTIVE.\n\n"
                "RULES:\n"
                "1. If the user gives a specific instruction (e.g. 'email John about the deadline', "
                "'ask Sarah for the API keys'), write the email strictly about that request. "
                "Do NOT dump the entire meeting transcript/summary unless they explicitly request a full recap.\n"
                "2. Extract the recipient name or email address into 'to' if specified in the user's prompt.\n"
                "3. Use the meeting context only as supporting reference material.\n"
                "4. Keep the email clear, human, and professional.\n\n"
                "Respond ONLY with a JSON object:\n"
                "{\n"
                '  "subject": "Clear, contextual subject line",\n'
                '  "to": "Recipient name/email or empty string",\n'
                '  "body": "Formatted email body"\n'
                "}"
            ),
        },
        {
            "role": "user",
            "content": f"User's Directive:\n{instruction if instruction else 'Draft a concise follow-up email covering key points.'}\n\nReference Meeting Context:\n{context}",
        },
    ]

    try:
        data = await _llm_json(messages, max_tokens=1000)
        return {
            "subject": data.get("subject", "Follow-up regarding meeting"),
            "to":      data.get("to", req.recipient or ""),
            "body":    data.get("body", ""),
        }
    except Exception as e:
        print(f"[draft-email fallback]: {e}", flush=True)
        summary = meeting.get("summary") or "Discussion and next steps."
        return {
            "subject": "Follow-Up: Meeting Summary",
            "to":      req.recipient or "",
            "body":    f"Hi,\n\nFollowing up on our discussion:\n\n{summary}\n\nBest regards,\nNio",
        }


# ── 5. Send Email (Background) ────────────────────────────────────────────────

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
        summary=meeting.get("summary")     if req.include_summary   else None,
        tasks=meeting.get("tasks")         if req.include_tasks     else None,
        decisions=meeting.get("decisions") if req.include_decisions else None,
    )

    if not success:
        return {"success": False, "message": "Failed to send email."}

    return {
        "success":     True,
        "message":     "Email sent.",
        "done_speech": f"Done. The {subject_label.lower()} has been sent to your inbox.",
    }

#  5. Schedule Meeting (Calendar) 

@router.post("/schedule-meeting")
async def schedule_meeting_tool(req: ToolRequest):
    return {
        "title": "Follow-up Meeting",
        "time": "Next Tuesday, 2:00 PM",
        "guests": "emmanuel@meetcore.com",
        "agenda": "- Review action items\n- Next steps"
    }