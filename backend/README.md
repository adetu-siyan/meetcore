# MeetCore — Backend

## What's actually done, tested, and working

- Full FastAPI project structure
- Ingestion: `/upload` — validates file, forwards to AssemblyAI, kicks off
  transcription with webhook registered (no polling)
- Processing: `/webhook/assemblyai` — receives completion callback, fires
  all 4 LeMUR tools in parallel, stores results
- 4 Phase 1 tools, each with 2 worked examples in-file:
  `task_extractor.py`, `deadline_extractor.py`, `decision_extractor.py`,
  `priority_brief.py`
- Vague-deadline-to-date-range logic — **tested against real dates, passing**
- Planning/routing agent (`planning_agent.py`) — the Cursor/Claude-Code-style
  layer that decides casual vs core-only vs RAG vs archival vs out-of-scope
  before Nio answers — **tested with 6 cases, all passing, including a
  fixed bug** (a naive greeting-detector was rejecting "Hey Nio, how are
  you?" — caught it, fixed it, re-tested)
- Nio's system prompt + tiered context builder (`nio_prompt.py`) — guardrails
  written in-prompt so Nio declines in-character, not via a bolted-on filter
- `/nio/ask` — ties planning agent + RAG + Groq together
- Supabase schema (`schema.sql`) — meetings table + pgvector chunks table +
  the similarity-search SQL function
- All Python files verified to compile with no syntax errors

## What is stubbed / needs you

1. **Embeddings — wired, not live-tested.** Uses Gemini `text-embedding-004`
   (768-dim). Logic verified with a mocked response matching Gemini's real
   API shape (batch of 2 texts → 2×768-dim vectors, correct). Not yet
   tested against your real `GEMINI_API_KEY` — this container's network
   allowlist blocks `generativelanguage.googleapis.com`, so that last step
   is on you. Schema and SQL function already updated to 768 dimensions
   to match.
2. **Specific-date parsing** (`deadline_extractor.py`) — "by Friday" style
   exact dates currently fall back to upload_date as a placeholder. Needs
   a real relative-date parser (the `dateparser` library is the standard
   choice) wired against `upload_date`.
3. **Email (Brevo) and Calendar (Google) services** — not yet built. The
   webhook handler has a comment marking exactly where they plug in.
4. **LeMUR's `final_model` parameter** — I used
   `anthropic/claude-3-5-sonnet` as a placeholder default. Confirm against
   AssemblyAI's current LeMUR docs which models they actually support —
   this may have changed.
5. **AssemblyAI streaming STT endpoint** — the URL in `config.py` is
   marked with a comment to verify against current docs before wiring the
   frontend's live mic connection.
6. **Real testing against live APIs** — everything above compiles and the
   pure-logic pieces are unit-tested, but nothing has touched a real
   AssemblyAI/Groq/Supabase account yet. That needs your actual API keys.

## Setup steps for you

1. `cd meetcore-backend && pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, fill in your real API keys
3. Run `schema.sql` in your Supabase project's SQL editor
4. Decide on an embeddings provider (see stub #1 above) — tell me and I'll
   wire `rag_service.py` properly
5. `uvicorn app.main:app --reload` to run locally
6. Test `/health` first — should return `{"status": "ok"}`
7. Deploy to Render once local run is clean

## Model note

Using `qwen/qwen3.6-27b` on Groq (dual-mode: thinking for extraction/reasoning,
non-thinking for Nio's conversational replies) — not `qwen3.8-27b`, which
isn't a Groq-hosted model ID as of this build. Flagging this since it
differs from what was asked for.
