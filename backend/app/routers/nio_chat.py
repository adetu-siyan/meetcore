
# """
# MeetCore — Nio Chat Router
# POST /nio/ask — main Q&A endpoint for the frontend chat interface.

# Response shape:
#   Normal:    { answer: str, strategy_used: str, tool: None }
#   Tool call: { answer: None, strategy_used: str, tool: "get_transcript" | "summarize_meeting" | "action_items" }
# """
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from groq import Groq

# from app.core.config import get_settings
# from app.core.nio_prompt import NIO_SYSTEM_PROMPT, build_nio_context_prompt
# from app.services import supabase_service, rag_service
# from app.services.planning_agent import plan_response, ResponseStrategy

# router = APIRouter(prefix="/nio", tags=["nio"])
# settings = get_settings()
# groq_client = Groq(api_key=settings.GROQ_API_KEY)

# DECLINE = (
#     "That's outside what I can help with here. "
#     "Anything else from the meeting?"
# )

# ARCHIVAL_UNAVAILABLE = (
#     "I only have access to this meeting right now — "
#     "cross-meeting memory isn't wired yet. "
#     "What do you want to know about this call?"
# )

# # Injected as the last system message so Nio knows about tools
# TOOL_SYSTEM_PROMPT = """
# You have access to the following tools. When the user's request clearly maps
# to one of them, respond with ONLY the tool name on its own line, exactly as
# shown — no other text, no punctuation, no explanation:

#   get_transcript       — user wants the full meeting transcript
#   summarize_meeting    — user wants a summary or overview of the meeting
#   action_items         — user wants tasks, todos, or action items

# If the request does not clearly map to a tool, respond normally in plain text.
# Do not mention tools unless you are invoking one.
# """

# KNOWN_TOOLS = {"get_transcript", "summarize_meeting", "action_items"}


# class AskRequest(BaseModel):
#     meeting_id: str
#     question: str
#     history: list[dict] | None = None


# class AskResponse(BaseModel):
#     answer: str | None = None
#     strategy_used: str
#     tool: str | None = None


# @router.post("/ask", response_model=AskResponse)
# async def ask_nio(req: AskRequest):
#     # 1. Meeting must exist
#     meeting = await supabase_service.get_meeting(req.meeting_id)
#     if not meeting:
#         raise HTTPException(status_code=404, detail="Meeting not found.")

#     # 2. Route
#     decision = plan_response(req.question, has_archival_data=False)

#     if decision.strategy == ResponseStrategy.OUT_OF_SCOPE:
#         return AskResponse(answer=DECLINE, strategy_used=decision.strategy.value)

#     if decision.strategy == ResponseStrategy.ARCHIVAL_REQUIRED:
#         return AskResponse(answer=ARCHIVAL_UNAVAILABLE, strategy_used=decision.strategy.value)

#     # 3. Build context
#     retrieved_chunks = None
#     if decision.strategy == ResponseStrategy.RAG_REQUIRED:
#         try:
#             retrieved_chunks = await rag_service.retrieve_relevant_chunks(
#                 req.meeting_id, req.question, top_k=5
#             )
#         except Exception as e:
#             print(f"[Nio] RAG retrieval failed (non-fatal): {e}", flush=True)

#     tasks     = meeting.get("tasks") or []
#     decisions = meeting.get("decisions") or []
#     deadlines = meeting.get("deadlines") or []

#     context_block = None
#     if decision.strategy != ResponseStrategy.CASUAL:
#         context_block = build_nio_context_prompt(
#             core_summary=meeting.get("summary", ""),
#             priority_brief=meeting.get("priority_brief", ""),
#             tasks=tasks,
#             decisions=decisions,
#             deadlines=deadlines,
#             retrieved_chunks=retrieved_chunks,
#         )

#     # 4. Build messages
#     messages = [{"role": "system", "content": NIO_SYSTEM_PROMPT}]

#     if context_block:
#         messages.append({"role": "system", "content": context_block})

#     # Tool awareness — always injected last before history
#     messages.append({"role": "system", "content": TOOL_SYSTEM_PROMPT})

#     if req.history:
#         for turn in req.history[-10:]:
#             if turn.get("role") in ("user", "assistant") and turn.get("content"):
#                 messages.append({"role": turn["role"], "content": turn["content"]})

#     messages.append({"role": "user", "content": req.question})

#     # 5. Call Groq
#     try:
#         completion = groq_client.chat.completions.create(
#             model=settings.GROQ_CHAT_MODEL,
#             messages=messages,
#             max_tokens=600,
#             temperature=0.3,
#         )
#         raw = completion.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"[Nio] Groq call failed: {e}", flush=True)
#         raise HTTPException(status_code=502, detail="Nio couldn't reach the model.")

#     # 6. Check if Groq returned a tool call
#     if raw in KNOWN_TOOLS:
#         print(f"[Nio] tool call detected: {raw}", flush=True)
#         return AskResponse(tool=raw, strategy_used=decision.strategy.value)

#     return AskResponse(answer=raw, strategy_used=decision.strategy.value)

"""
MeetCore — Nio Conversational Interface Router
POST /nio/ask — Handles user voice queries, RAG context assembly, tool dispatching,
and background underground tool triggers (e.g. Brevo email actions).
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

router = APIRouter(prefix="/nio", tags=["nio"])
settings = get_settings()

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)


class NioRequest(BaseModel):
    meeting_id: str
    question: str
    history: list[dict] = []


class NioResponse(BaseModel):
    answer: str = ""
    tool: str | None = None
    background_tool: dict | None = None


def _extract_tool_call(raw_text: str) -> str | None:
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

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


@router.post("/ask", response_model=NioResponse)
async def ask_nio(req: NioRequest):
    try:
        # 1. Fetch meeting record
        meeting = await supabase_service.get_meeting(req.meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found.")

        # 2. RAG retrieval — non-fatal, Nio degrades gracefully to summary context
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

        # 3. Assemble context
        context_text = build_nio_context_prompt(
            core_summary=meeting.get("summary") or "",
            priority_brief=meeting.get("priority_brief") or "",
            tasks=meeting.get("tasks") or [],
            deadlines=meeting.get("deadlines") or [],
            decisions=meeting.get("decisions") or [],
            retrieved_chunks=retrieved_chunks,
        )

        messages = [
            {"role": "system", "content": NIO_SYSTEM_PROMPT},
            {"role": "system", "content": f"CONTEXT FOR THIS MEETING:\n{context_text}"},
        ]

        for msg in req.history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": req.question})

        # 4. Groq inference
        try:
            completion = await groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.3,
                max_tokens=600,
            )
            raw_output = completion.choices[0].message.content or ""
        except Exception as groq_err:
            print(f"[Nio] Groq inference failed: {groq_err}", flush=True)
            raise HTTPException(status_code=502, detail=f"Inference error: {groq_err}")

        # 5. Visual drawer tool call
        tool_name = _extract_tool_call(raw_output)
        if tool_name:
            return NioResponse(answer="", tool=tool_name, background_tool=None)

        # 6. Underground email dispatch
        if "__ACTION:SEND_EMAIL" in raw_output:
            include_summary = True
            include_tasks = True
            include_decisions = False

            match = re.search(r"__ACTION:SEND_EMAIL\((.*?)\)__", raw_output)
            if match:
                params = match.group(1).lower()
                include_summary = "include_summary=true" in params
                include_tasks = "include_tasks=true" in params
                include_decisions = "include_decisions=true" in params

            clean_speech = re.sub(r"__ACTION:SEND_EMAIL(?:\(.*?\))?__", "", raw_output).strip()
            if not clean_speech:
                clean_speech = "Understood. Dispatching that to your inbox now."

            return NioResponse(
                answer=clean_speech,
                tool=None,
                background_tool={
                    "name": "send_email",
                    "params": {
                        "include_summary": include_summary,
                        "include_tasks": include_tasks,
                        "include_decisions": include_decisions,
                    },
                },
            )

        # 7. Conversational response
        return NioResponse(answer=raw_output.strip(), tool=None, background_tool=None)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Nio error: {e}")