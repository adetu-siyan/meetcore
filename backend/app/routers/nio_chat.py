"""
MeetCore — Nio Chat Router
POST /nio/ask — Handles user voice queries, RAG context assembly,
visual tool call detection, and background email action parsing.
"""
import json
import re
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from groq import AsyncGroq

from app.core.config import get_settings
from app.core.nio_prompt import NIO_SYSTEM_PROMPT, build_nio_context_prompt
from app.services import supabase_service, rag_service

router   = APIRouter(prefix="/nio", tags=["nio"])
settings = get_settings()

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=20.0)

LLM_MODEL = "openai/gpt-oss-120b"


class NioAskRequest(BaseModel):
    meeting_id: str
    question:   str
    history:    list[dict] = []


def _extract_tool_call(raw: str) -> str | None:
    """
    Detects if Nio's response is a visual tool call JSON object.
    Handles markdown fences.
    gpt-oss with json_object response_format does not bleed <think> into
    content, so no reasoning tag stripping needed here.
    Returns the tool name string if found, else None.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "tool" in data:
            return data["tool"]
    except Exception:
        pass

    match = re.search(r'\{\s*"tool"\s*:\s*"([a-zA-Z0-9_-]+)"\s*\}', cleaned)
    if match:
        return match.group(1)

    return None


def _extract_background_action(text: str) -> tuple[str, dict | None]:
    """
    Extracts __ACTION:SEND_EMAIL(...)__ tags from Nio's speech output.
    Strips the tag from spoken text and returns parsed email params.
    """
    pattern = r"__ACTION:SEND_EMAIL\((.*?)\)__"
    match   = re.search(pattern, text)
    if not match:
        return text.strip(), None

    raw_args     = match.group(1)
    clean_speech = re.sub(pattern, "", text).strip()
    if not clean_speech:
        clean_speech = "Dispatching that to your inbox now."

    params = {
        "include_summary":   True,
        "include_tasks":     True,
        "include_decisions": False,
    }
    for arg in raw_args.split(","):
        if "=" in arg:
            k, v = arg.split("=", 1)
            k = k.strip()
            v = v.strip().lower()
            if k in params:
                params[k] = v == "true"

    return clean_speech, {"name": "send_email", "params": params}


@router.post("/ask")
async def ask_nio(req: NioAskRequest):
    try:
        # 1. Fetch meeting
        meeting = await supabase_service.get_meeting(req.meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # 2. RAG retrieval — non-fatal, degrades gracefully to summary-only context
        retrieved_chunks = []
        try:
            retrieved_chunks = await rag_service.retrieve_relevant_chunks(
                meeting_id=req.meeting_id,
                question=req.question,
                top_k=3,
                window_radius=1,
            )
        except Exception as rag_err:
            print(f"[Nio] RAG retrieval failed (non-fatal): {rag_err}", flush=True)

        # 3. Assemble grounded context
        meeting_context = build_nio_context_prompt(
            core_summary=meeting.get("summary") or "",
            priority_brief=meeting.get("priority_brief") or "",
            tasks=meeting.get("tasks") or [],
            deadlines=meeting.get("deadlines") or [],
            decisions=meeting.get("decisions") or [],
            retrieved_chunks=retrieved_chunks,
        )

        messages = [
            {"role": "system", "content": NIO_SYSTEM_PROMPT},
            {"role": "system", "content": f"MEETING CONTEXT:\n{meeting_context}"},
        ]

        for h in req.history[-6:]:
            role    = h.get("role")
            content = h.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": req.question})

        # 4. Groq inference
        # gpt-oss parameter rules:
        # - reasoning_effort: "low" | "medium" | "high" only
        # - reasoning_format: NOT supported on gpt-oss — omitted
        # - include_reasoning: False — clean output, no token waste
        try:
            completion = await groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=600,
                reasoning_effort="low",
                include_reasoning=False,
            )
            raw_output = completion.choices[0].message.content or ""
        except Exception as groq_err:
            print(f"[Nio] Groq inference error: {groq_err}", flush=True)
            return {
                "answer":          "I had a brief delay. Could you repeat that?",
                "tool":            None,
                "background_tool": None,
            }

        # 5. Visual tool call — return immediately, no speech
        tool_name = _extract_tool_call(raw_output)
        if tool_name:
            return {"answer": "", "tool": tool_name, "background_tool": None}

        # 6. Background email dispatch
        clean_speech, background_tool = _extract_background_action(raw_output)

        return {
            "answer":          clean_speech,
            "tool":            None,
            "background_tool": background_tool,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Nio error: {e}")