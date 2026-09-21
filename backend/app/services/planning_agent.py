"""
MeetCore — Planning Agent

This is the routing layer you asked for — the equivalent of what sits
under Cursor/Claude Code before they act. Rather than always running
full RAG retrieval for every question, this agent decides, per question:

1. Does this need retrieval at all? (e.g. "hey Nio" needs none)
2. Does core context (summary + brief) already answer it?
3. Does it need RAG against this meeting's transcript?
4. Does it need archival memory (a past meeting)?
5. Is this out of bounds per the guardrails (and should be declined
   before even reaching Groq's conversational call)?

This keeps latency down — the expensive retrieval step only runs when
it's actually needed — and keeps the guardrail check as an explicit,
inspectable step rather than hoping the system prompt catches everything.
"""
from enum import Enum
from dataclasses import dataclass


class ResponseStrategy(str, Enum):
    CASUAL = "casual"                  # greetings/small talk — no context needed
    CORE_ONLY = "core_only"             # summary/brief answers it
    RAG_REQUIRED = "rag_required"       # needs specific transcript excerpts
    ARCHIVAL_REQUIRED = "archival_required"  # references a past meeting
    OUT_OF_SCOPE = "out_of_scope"        # guardrail — decline before Groq call


# Keywords that suggest the question needs specific transcript detail
# rather than the high-level summary. Simple heuristic for MVP — a real
# router would use a fast Groq classification call; this keeps the
# planning step itself cheap and instant.
_SPECIFIC_DETAIL_SIGNALS = (
    "said", "mentioned", "exact", "word for word", "quote",
    "what did", "who said", "specifically",
)

_ARCHIVAL_SIGNALS = (
    "last week", "last meeting", "previous meeting", "before this",
    "last time", "past meeting",
)

_OUT_OF_SCOPE_SIGNALS = (
    # Non-exhaustive — the system prompt is the real backstop. This is a
    # fast pre-filter to skip an unnecessary Groq call, not the guardrail
    # itself.
    "ignore your instructions", "system prompt", "jailbreak",
    "medical advice", "legal advice",
)


@dataclass
class RoutingDecision:
    strategy: ResponseStrategy
    reason: str


def plan_response(question: str, has_archival_data: bool = False) -> RoutingDecision:
    q_lower = question.lower().strip()

    if any(signal in q_lower for signal in _OUT_OF_SCOPE_SIGNALS):
        return RoutingDecision(
            strategy=ResponseStrategy.OUT_OF_SCOPE,
            reason="Matched an out-of-scope signal — declining before model call.",
        )

    # Short greetings/small talk: "hey nio", "how's it going", "hey nio how are you"
    # Checked on word count only (not full-string length) so a greeting plus
    # a short trailing name/phrase still matches; question length is capped
    # so this doesn't swallow genuine questions that happen to start similarly.
    greeting_words = ("hey", "hi", "hello", "yo", "what's up", "sup")
    starts_with_greeting = any(q_lower.startswith(g) for g in greeting_words)
    is_short = len(q_lower.split()) <= 6
    if starts_with_greeting and is_short:
        return RoutingDecision(
            strategy=ResponseStrategy.CASUAL,
            reason="Short greeting/small-talk pattern.",
        )

    if any(signal in q_lower for signal in _ARCHIVAL_SIGNALS) and has_archival_data:
        return RoutingDecision(
            strategy=ResponseStrategy.ARCHIVAL_REQUIRED,
            reason="References a past meeting.",
        )

    if any(signal in q_lower for signal in _SPECIFIC_DETAIL_SIGNALS):
        return RoutingDecision(
            strategy=ResponseStrategy.RAG_REQUIRED,
            reason="Needs specific transcript detail beyond the summary.",
        )

    return RoutingDecision(
        strategy=ResponseStrategy.CORE_ONLY,
        reason="General question — core summary/brief likely sufficient.",
    )
