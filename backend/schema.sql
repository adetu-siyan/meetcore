-- MeetCore Supabase Schema
-- Run this in your Supabase SQL editor before the backend will work.

create extension if not exists vector;

create table if not exists meetings (
    meeting_id uuid primary key,
    transcript_id text,
    upload_date timestamptz not null,
    status text not null default 'uploaded',
    transcript_text text,
    summary text,
    priority_brief text,
    tasks jsonb default '[]',
    deadlines jsonb default '[]',
    decisions jsonb default '[]',
    chapters jsonb default '[]',
    sentiment_summary text,
    created_at timestamptz default now()
);

create table if not exists transcript_chunks (
    id bigserial primary key,
    meeting_id uuid references meetings(meeting_id) on delete cascade,
    chunk_text text not null,
    embedding vector(768), -- Gemini text-embedding-004 output dimension
    created_at timestamptz default now()
);

create index if not exists transcript_chunks_meeting_idx on transcript_chunks(meeting_id);

-- Cosine similarity search scoped to one meeting, used by rag_service.py
create or replace function match_transcript_chunks (
    query_embedding vector(768),
    target_meeting_id uuid,
    match_count int default 5
)
returns table (chunk_text text, similarity float)
language sql stable
as $$
    select
        chunk_text,
        1 - (embedding <=> query_embedding) as similarity
    from transcript_chunks
    where meeting_id = target_meeting_id
    order by embedding <=> query_embedding
    limit match_count;
$$;
