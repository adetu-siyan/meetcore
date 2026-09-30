"""
MeetCore — Nio Chat Router
POST /nio/ask — Handles user voice queries, RAG context assembly,
visual tool call detection, and background email action parsing.
"""
import json
import re
import traceback
import asyncio
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


def _extract_tool_call(raw: str) -> tuple[str, str | None]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "tool" in data:
            return "", data["tool"]
    except Exception:
        pass

    match = re.search(r'\{\s*"tool"\s*:\s*"([a-zA-Z0-9_-]+)"\s*\}', cleaned)
    if match:
        speech = cleaned.replace(match.group(0), "").strip()
        return speech, match.group(1)

    return cleaned, None


def _extract_background_action(text: str) -> tuple[str, dict | None]:
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
        # 1. Fetch meeting — non-fatal, Nio handles greetings without context
        meeting = None
        try:
            meeting = await supabase_service.get_meeting(req.meeting_id)
        except Exception:
            pass

        # 2. RAG retrieval — only if meeting exists
        retrieved_chunks = []
        if meeting:
            try:
                retrieved_chunks = await asyncio.wait_for(
                    rag_service.retrieve_relevant_chunks(
                        meeting_id=req.meeting_id,
                        question=req.question,
                        top_k=3,
                        window_radius=1,
                    ),
                    timeout=1.5
                )
            except Exception as rag_err:
                print(f"[Nio] RAG retrieval failed (non-fatal): {rag_err}", flush=True)

        # 3. Assemble context
        meeting_context = build_nio_context_prompt(
            core_summary=meeting.get("summary") or "" if meeting else "",
            priority_brief=meeting.get("priority_brief") or "" if meeting else "",
            tasks=meeting.get("tasks") or [] if meeting else [],
            deadlines=meeting.get("deadlines") or [] if meeting else [],
            decisions=meeting.get("decisions") or [] if meeting else [],
            retrieved_chunks=retrieved_chunks,
        )

        messages = [
            {"role": "system", "content": NIO_SYSTEM_PROMPT},
        ]

        if meeting and meeting_context != "No meeting context available yet.":
            messages.append({
                "role": "system",
                "content": f"MEETING CONTEXT:\n{meeting_context}"
            })

        for h in req.history[-6:]:
            role    = h.get("role")
            content = h.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": req.question})

        # 4. Groq inference — no tools, plain chat only
        try:
            completion = await groq_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=600,
            )
            raw_output = completion.choices[0].message.content or ""
        except Exception as groq_err:
            print(f"[Nio] Groq inference error: {groq_err}", flush=True)
            return {
                "answer":          "I had a brief delay. Could you repeat that?",
                "tool":            None,
                "background_tool": None,
            }

        # 5. Visual tool call detection
        speech_text, tool_name = _extract_tool_call(raw_output)
        if tool_name:
            if not speech_text:
                speech_text = "I'm opening that for you right now."
            return {"answer": speech_text, "tool": tool_name, "background_tool": None}

        # 6. Background email dispatch
        clean_speech, background_tool = _extract_background_action(speech_text)

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