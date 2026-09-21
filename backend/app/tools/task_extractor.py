"""
MeetCore — Tool 1: Task Extractor

Function: Extracts all action items and tasks mentioned in a meeting.
For each task: what needs to be done, who is responsible, and any
deadline mentioned. Returns a structured list.

This is one of the 4 Phase 1 LeMUR-driven tools.
"""
import json
from app.tools.lemur_client import run_lemur_prompt
from app.models.meeting import Task

PROMPT = """Extract all action items and tasks mentioned in this meeting.

For each task, identify:
- description: what needs to be done
- owner: who is responsible (use the speaker label or name if mentioned, else null)
- deadline: any deadline mentioned in the speaker's own words (else null)

Return ONLY a JSON array, no other text. Example format:
[
  {"description": "Send the proposal to the client", "owner": "Sarah", "deadline": "by Friday"},
  {"description": "Review the budget numbers", "owner": null, "deadline": null}
]

If there are no clear tasks, return an empty array: []
"""


async def extract_tasks(transcript_id: str) -> list[Task]:
    raw_response = await run_lemur_prompt(transcript_id, PROMPT)
    try:
        # Strip markdown fences if the model wraps its JSON in them
        cleaned = raw_response.strip().strip("```json").strip("```").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    return [Task(**item) for item in data]


# --- EXAMPLE 1 ---
# Input meeting excerpt (Speaker A = John, Speaker B = Sarah):
#   John: "Sarah, can you send the proposal to the client by end of day Friday?"
#   Sarah: "Yeah, I'll get that done."
#
# Expected output:
EXAMPLE_1_OUTPUT = [
    {"description": "Send the proposal to the client", "owner": "Sarah", "deadline": "by end of day Friday"}
]

# --- EXAMPLE 2 ---
# Input meeting excerpt (Speaker A = client, Speaker B = internal team):
#   Client: "We also need someone to look at the budget numbers again,
#            they didn't add up on our end."
#   Team: "Noted, we'll review that."
#
# Expected output:
EXAMPLE_2_OUTPUT = [
    {"description": "Review the budget numbers — client flagged they didn't add up", "owner": None, "deadline": None}
]
