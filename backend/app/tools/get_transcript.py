"""
MeetCore — Tool: Get Transcript
Reads transcript_text directly from the meetings table in Supabase.
The pipeline already saved it there — no need to hit AssemblyAI again.
"""
from app.services.supabase_service import get_meeting


async def get_transcript(meeting_id: str) -> str:
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise ValueError("Meeting not found.")
    text = meeting.get("transcript_text", "")
    if not text:
        raise ValueError("Transcript not yet available for this meeting.")
    return text