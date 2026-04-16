from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RatingCreate(BaseModel):
    score: float = Field(..., ge=1, le=5, description="Rating score from 1 to 5 stars")
    review: Optional[str] = Field(None, max_length=2000, description="Optional written review")


class RatingResponse(BaseModel):
    id: str
    user_id: str
    content_id: str
    score: float
    review: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ContentRatingSummary(BaseModel):
    content_id: str
    average_score: float
    total_ratings: int
    user_score: Optional[float] = None
    user_review: Optional[str] = None
