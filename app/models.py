from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class MeetingSummary(BaseModel):
    id: str
    started_at: str
    ended_at: Optional[str] = None
    status: str
    project: Optional[str] = None
    summary: Optional[str] = None


class MeetingDetail(MeetingSummary):
    transcript: List[TranscriptSegment] = []
    topics: List[str] = []
    modules: List[str] = []
    participants_mentioned: List[str] = []
    action_items: List[str] = []
    error_message: Optional[str] = None


class AnalysisResult(BaseModel):
    summary: str
    topics: List[str] = []
    project: Optional[str] = None
    modules: List[str] = []
    participants_mentioned: List[str] = []
    action_items: List[str] = []
