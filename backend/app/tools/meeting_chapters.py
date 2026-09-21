"""
MeetCore — Tool: Meeting Chapters
Fetches auto-chapters extracted directly by AssemblyAI's acoustic model.
"""
from app.services.supabase_service import get_meeting


async def get_meeting_chapters(meeting_id: str) -> list[dict]:
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise ValueError("Meeting not found.")
    return meeting.get("chapters", [])