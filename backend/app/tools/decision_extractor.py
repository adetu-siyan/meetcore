"""
MeetCore — Tool 3: Key Decision Extractor

Function: Identifies the key decisions made in a meeting and who made them.
"""
import json
from app.tools.lemur_client import run_lemur_prompt
from app.models.meeting import Decision

PROMPT = """What were the key decisions made in this meeting?

For each decision, identify:
- decision: what was decided, stated clearly and concisely
- made_by: who made or confirmed the decision (speaker label or name if
  mentioned, else null)

Return ONLY a JSON array, no other text. Example format:
[
  {"decision": "The team will use Option B for the pricing model", "made_by": "John"},
  {"decision": "Launch date moved to Q4", "made_by": null}
]

If there were no clear decisions, return an empty array: []
"""


async def extract_decisions(transcript_id: str) -> list[Decision]:
    raw_response = await run_lemur_prompt(transcript_id, PROMPT)
    try:
        cleaned = raw_response.strip().strip("```json").strip("```").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    return [Decision(**item) for item in data]


# --- EXAMPLE 1 ---
# Input excerpt:
#   John: "So we're going with Option B for the pricing model, agreed?"
#   Sarah: "Agreed."
#
# Expected output:
EXAMPLE_1_OUTPUT = [
    {"decision": "Going with Option B for the pricing model", "made_by": "John"}
]

# --- EXAMPLE 2 ---
# Input excerpt:
#   Client: "We'd rather push the launch to Q4 than rush it in Q3."
#   Team: "That works on our end too."
#
# Expected output:
EXAMPLE_2_OUTPUT = [
    {"decision": "Launch pushed from Q3 to Q4", "made_by": None}
]
