"""
MeetCore — Tool 4: Priority Brief Generator

Function: Based on the meeting, generates the 3 most important things
the participants need to act on immediately. This is the "here's what
you need to do right now" output that closes the summary.
"""
from app.tools.lemur_client import run_lemur_prompt

PROMPT = """Based on this meeting, what are the 3 most important things
the participants need to act on immediately? Be direct and concise —
one short sentence per item. If there are fewer than 3 genuinely urgent
items, only list what's actually urgent; don't pad the list.

Return as plain text, one item per line, no numbering or bullets needed —
just the three sentences.
"""


async def generate_priority_brief(transcript_id: str) -> str:
    return await run_lemur_prompt(transcript_id, PROMPT)


# --- EXAMPLE 1 ---
# Input: a sales call where pricing was contested and a follow-up promised
# Expected output:
EXAMPLE_1_OUTPUT = """Send the client the revised pricing sheet before end of day.
Confirm with legal whether the discount clause needs sign-off.
Follow up with the client by Friday if no response."""

# --- EXAMPLE 2 ---
# Input: an internal planning meeting with no urgent follow-up
# Expected output:
EXAMPLE_2_OUTPUT = """Share the updated roadmap doc with the wider team.
No other immediate action — next check-in is the regular Monday sync."""
