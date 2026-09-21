"""
MeetCore — Data models
Pydantic schemas used across ingestion, processing, and storage.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class MeetingStatus(str, Enum):
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class Task(BaseModel):
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None  # raw string as extracted; parsed separately


class Deadline(BaseModel):
    title: str
    owner: Optional[str] = None
    is_specific_date: bool
    start_date: Optional[str] = None  # ISO date
    end_date: Optional[str] = None    # ISO date — same as start if specific


class Decision(BaseModel):
    decision: str
    made_by: Optional[str] = None


class MeetingRecord(BaseModel):
    meeting_id: str
    status: MeetingStatus
    upload_date: datetime
    transcript_id: Optional[str] = None
    transcript_text: Optional[str] = None
    summary: Optional[str] = None
    priority_brief: Optional[str] = None
    tasks: list[Task] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    chapters: list[dict] = Field(default_factory=list)
    sentiment_summary: Optional[str] = None


class UploadResponse(BaseModel):
    meeting_id: str
    status: MeetingStatus
    message: str
