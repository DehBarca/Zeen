from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RatingCreate(BaseModel):
    """Schema for creating or updating a rating"""
    score: float = Field(..., ge=1, le=10, description="Rating score from 1 to 10")


class RatingResponse(BaseModel):
    """Schema for rating response"""
    id: str
    user_id: str
    content_id: str
    score: float
    created_at: datetime

    class Config:
        from_attributes = True


class ContentRatingSummary(BaseModel):
    """Schema for content rating summary"""
    content_id: str
    average_score: float
    total_ratings: int
    user_score: Optional[float] = None
