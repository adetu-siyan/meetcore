"""
MeetCore — Tool: Meeting Summary
Accepts raw transcript text, sends to Groq for structured summary.
"""
import json
from app.tools.lemur_client import run_lemur_prompt_text

PROMPT = """Summarize this meeting in three sections.

Return ONLY a JSON object, no other text, in this exact format:
{
  "key_points": ["concise bullet — one sentence each"],
  "decisions": ["what was agreed or decided — one sentence each"],
  "open_questions": ["unresolved items — one sentence each"]
}

Rules:
- key_points: main topics discussed, 3–6 items
- decisions: only explicitly agreed items; empty array if none
- open_questions: things raised but not resolved; empty array if none
- Every item is one short clear sentence
- No numbering or bullets in the strings
"""


async def summarize_meeting(transcript_text: str) -> dict:
    raw_response = await run_lemur_prompt_text(transcript_text, PROMPT)
    try:
        cleaned = raw_response.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"key_points": [], "decisions": [], "open_questions": []}