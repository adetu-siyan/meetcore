"""
MeetCore — Tool: Meeting Sentiment
Fetches sentiment summary analyzed sentence-by-sentence by AssemblyAI.
"""
from app.services.supabase_service import get_meeting


async def get_meeting_sentiment(meeting_id: str) -> dict:
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise ValueError("Meeting not found.")
    return {
        "sentiment_summary": meeting.get("sentiment_summary") or "Neutral tone throughout the meeting."
    }