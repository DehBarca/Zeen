from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """Enum for content types"""
    MOVIE = "movie"
    SERIES = "series"
    EPISODE = "episode"


class ContentBase(BaseModel):
    """Base content schema"""
    title: str
    description: str
    content_type: ContentType
    duration_minutes: int
    release_date: datetime
    poster_url: Optional[str] = None
    banner_url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=10)
    genres: List[str] = []
    cast: List[str] = []
    directors: List[str] = []


class ContentCreate(ContentBase):
    """Schema for creating content"""
    pass


class ContentUpdate(BaseModel):
    """Schema for updating content"""
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    release_date: Optional[datetime] = None
    poster_url: Optional[str] = None
    banner_url: Optional[str] = None
    rating: Optional[float] = None
    genres: Optional[List[str]] = None
    cast: Optional[List[str]] = None
    directors: Optional[List[str]] = None


class ContentResponse(ContentBase):
    """Schema for content response"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EpisodeSchema(BaseModel):
    """Schema for TV episodes"""
    episode_number: int
    season_number: int
    title: str
    description: Optional[str] = None
    duration_minutes: int
    release_date: datetime
    video_url: Optional[str] = None
    rating: Optional[float] = None


class SeriesSchema(ContentBase):
    """Schema for TV series with episodes"""
    total_seasons: int
    total_episodes: int
    episodes: Optional[List[EpisodeSchema]] = []


class MovieSchema(ContentBase):
    """Schema for movies"""
    video_url: Optional[str] = None


class WatchHistoryEntry(BaseModel):
    """Schema for watch history"""
    content_id: str
    watched_at: datetime
    progress_minutes: int
    is_completed: bool
    
    class Config:
        from_attributes = True
