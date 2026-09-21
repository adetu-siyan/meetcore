"""
MeetCore — Tool: Action Items
Accepts raw transcript text, extracts tasks via Groq.
"""
import json
from app.tools.lemur_client import run_lemur_prompt_text
from app.models.meeting import Task

PROMPT = """Extract all action items and tasks mentioned in this meeting.

For each task, identify:
- description: what needs to be done
- owner: who is responsible (speaker label or name if mentioned, else null)
- deadline: any deadline mentioned in the speaker's own words (else null)

Return ONLY a JSON array, no other text. Example format:
[
  {"description": "Send the proposal to the client", "owner": "Sarah", "deadline": "by Friday"},
  {"description": "Review the budget numbers", "owner": null, "deadline": null}
]

If there are no clear tasks, return an empty array: []
"""


async def get_action_items(transcript_text: str) -> list[Task]:
    raw_response = await run_lemur_prompt_text(transcript_text, PROMPT)
    try:
        cleaned = raw_response.strip().strip("```json").strip("```").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    return [Task(**item) for item in data]