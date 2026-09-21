"""
MeetCore — Tool 2: Deadline Extractor

Function: Extracts all dates, deadlines, and time-sensitive commitments
mentioned in a meeting. Distinguishes specific dates from vague ones,
which matters downstream for Calendar (specific -> single event,
vague -> range event from upload_date to calculated end).
"""
import json
from datetime import datetime, timedelta
from app.tools.lemur_client import run_lemur_prompt
from app.models.meeting import Deadline

PROMPT = """Extract all dates, deadlines, and time-sensitive commitments
mentioned in this meeting.

For each one, identify:
- title: what the deadline is for
- owner: who owns it (speaker label or name if mentioned, else null)
- raw_date_mention: the exact words used for the date (e.g. "by Friday",
  "end of next week", "October 15th", "sometime next month")
- is_specific: true if it's an exact, calculable date/day; false if vague

Return ONLY a JSON array, no other text. Example format:
[
  {"title": "Submit the proposal", "owner": "Sarah", "raw_date_mention": "by Friday", "is_specific": true},
  {"title": "Finalize the contract", "owner": null, "raw_date_mention": "sometime next month", "is_specific": false}
]

If there are no deadlines, return an empty array: []
"""


def _resolve_vague_range(upload_date: datetime, raw_mention: str) -> tuple[str, str]:
    """
    Converts a vague deadline into a start/end date range, starting from
    the upload date as agreed: "end of next week" -> upload_date to the
    following Sunday, "next month" -> upload_date to last day of next month.

    This is intentionally simple pattern matching for MVP — not a full
    NLP date parser. Expand as real transcripts surface more phrasings.
    """
    text = raw_mention.lower()
    start = upload_date

    if "next week" in text:
        days_until_next_sunday = (13 - start.weekday()) % 7 + 7
        end = start + timedelta(days=days_until_next_sunday)
    elif "this week" in text:
        days_until_sunday = (6 - start.weekday()) % 7
        end = start + timedelta(days=days_until_sunday)
    elif "next month" in text:
        # last day of next month
        month = start.month + 2
        year = start.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        end = datetime(year, month, 1) - timedelta(days=1)
    else:
        # Fallback: 14-day window when phrasing isn't recognized
        end = start + timedelta(days=14)

    return start.date().isoformat(), end.date().isoformat()


async def extract_deadlines(transcript_id: str, upload_date: datetime) -> list[Deadline]:
    raw_response = await run_lemur_prompt(transcript_id, PROMPT)
    try:
        cleaned = raw_response.strip().strip("```json").strip("```").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    deadlines = []
    for item in data:
        is_specific = item.get("is_specific", False)
        if is_specific:
            # NOTE: converting "by Friday" -> an actual ISO date still needs
            # a real date-parsing pass (e.g. dateparser lib) relative to
            # upload_date. Stubbed here as a TODO for the wiring session.
            start_date = upload_date.date().isoformat()
            end_date = start_date
        else:
            start_date, end_date = _resolve_vague_range(
                upload_date, item.get("raw_date_mention", "")
            )

        deadlines.append(Deadline(
            title=item["title"],
            owner=item.get("owner"),
            is_specific_date=is_specific,
            start_date=start_date,
            end_date=end_date,
        ))

    return deadlines


# --- EXAMPLE 1 (specific date) ---
# Input: "Let's get the contract signed by October 15th."
# Expected LeMUR output:
EXAMPLE_1_OUTPUT = [
    {"title": "Get the contract signed", "owner": None, "raw_date_mention": "October 15th", "is_specific": True}
]

# --- EXAMPLE 2 (vague date) ---
# Input: "We should have the new pricing model ready sometime next month."
# Expected LeMUR output, then resolved to a range if upload_date is e.g. 2026-09-16:
EXAMPLE_2_OUTPUT = [
    {"title": "Have the new pricing model ready", "owner": None, "raw_date_mention": "sometime next month", "is_specific": False}
]
# Resolved range: start_date="2026-09-16", end_date="2026-10-31"
