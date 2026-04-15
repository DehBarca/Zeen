"""
Ratings endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime

from app.core.database import get_mongodb
from app.schemas.ratings import RatingCreate, RatingResponse, ContentRatingSummary
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter(prefix="/ratings", tags=["ratings"])


async def _recalculate_content_rating(db: AsyncDatabase, content_id: ObjectId):
    """Recalculate and update the average rating for a content item"""
    pipeline = [
        {"$match": {"content_id": content_id}},
        {"$group": {"_id": None, "average": {"$avg": "$score"}, "total": {"$sum": 1}}},
    ]
    result = await db["ratings"].aggregate(pipeline).to_list(1)

    if result:
        avg = round(result[0]["average"], 1)
    else:
        avg = 0.0

    await db["content"].update_one(
        {"_id": content_id},
        {"$set": {"rating": avg, "updated_at": datetime.utcnow()}},
    )


@router.post("/{content_id}", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_content(
    content_id: str,
    rating_data: RatingCreate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Create or update the authenticated user's rating for a content item"""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    user_obj_id = ObjectId(current_user.id)

    existing = await db["ratings"].find_one(
        {"user_id": user_obj_id, "content_id": content_obj_id}
    )

    if existing:
        await db["ratings"].update_one(
            {"_id": existing["_id"]},
            {"$set": {"score": rating_data.score, "created_at": datetime.utcnow()}},
        )
        rating = await db["ratings"].find_one({"_id": existing["_id"]})
    else:
        new_rating = {
            "user_id": user_obj_id,
            "content_id": content_obj_id,
            "score": rating_data.score,
            "created_at": datetime.utcnow(),
        }
        result = await db["ratings"].insert_one(new_rating)
        rating = await db["ratings"].find_one({"_id": result.inserted_id})

    await _recalculate_content_rating(db, content_obj_id)

    return RatingResponse(
        id=str(rating["_id"]),
        user_id=str(rating["user_id"]),
        content_id=str(rating["content_id"]),
        score=rating["score"],
        created_at=rating["created_at"],
    )


@router.get("/{content_id}", response_model=ContentRatingSummary)
async def get_content_ratings(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get rating summary for a content item, including the current user's score if any"""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    pipeline = [
        {"$match": {"content_id": content_obj_id}},
        {"$group": {"_id": None, "average": {"$avg": "$score"}, "total": {"$sum": 1}}},
    ]
    result = await db["ratings"].aggregate(pipeline).to_list(1)

    average_score = round(result[0]["average"], 1) if result else 0.0
    total_ratings = result[0]["total"] if result else 0

    user_rating = await db["ratings"].find_one(
        {"user_id": ObjectId(current_user.id), "content_id": content_obj_id}
    )

    return ContentRatingSummary(
        content_id=content_id,
        average_score=average_score,
        total_ratings=total_ratings,
        user_score=user_rating["score"] if user_rating else None,
    )


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Delete the authenticated user's rating for a content item"""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )

    result = await db["ratings"].delete_one(
        {"user_id": ObjectId(current_user.id), "content_id": content_obj_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found",
        )

    await _recalculate_content_rating(db, content_obj_id)
