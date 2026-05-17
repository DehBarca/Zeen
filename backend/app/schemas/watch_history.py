from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PlaybackEventType(str, Enum):
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"


class PlaybackEventCreate(BaseModel):
    event_type: PlaybackEventType
    position_seconds: int = Field(..., ge=0)


class PlaybackEventResponse(BaseModel):
    user_id: str
    content_id: str
    event_type: str
    position_seconds: int
    event_time: datetime


class WatchHistoryEntry(BaseModel):
    content_id: str
    watched_at: datetime
    progress_seconds: int
    duration_seconds: int
    completed: bool


class WatchHistoryResponse(BaseModel):
    user_id: str
    history: List[WatchHistoryEntry]


class UserActivityEntry(BaseModel):
    event_time: datetime
    user_id: str
    action: str
    content_id: Optional[str] = None
    details: Optional[str] = None


class UserActivityResponse(BaseModel):
    activities: List[UserActivityEntry]
