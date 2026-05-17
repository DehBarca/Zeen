"""
Ratings & Reviews endpoints
FR-11 Content Ratings & Reviews, FR-23 User's Rating History
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime
from typing import List

from app.core.database import get_mongodb
from app.schemas.ratings import RatingCreate, RatingResponse, ContentRatingSummary
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter(prefix="/ratings", tags=["ratings"])


async def _recalculate_content_rating(db: AsyncDatabase, content_id: ObjectId):
    pipeline = [
        {"$match": {"content_id": content_id}},
        {"$group": {"_id": None, "average": {"$avg": "$score"}, "total": {"$sum": 1}}},
    ]
    result = await db["ratings"].aggregate(pipeline).to_list(1)
    avg = round(result[0]["average"], 1) if result else 0.0
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
    """FR-11: Create or update the authenticated user's rating (and optional review) for content."""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    user_obj_id = ObjectId(current_user.id)
    existing = await db["ratings"].find_one({"user_id": user_obj_id, "content_id": content_obj_id})

    update_fields = {"score": rating_data.score, "created_at": datetime.utcnow()}
    if rating_data.review is not None:
        update_fields["review"] = rating_data.review

    if existing:
        await db["ratings"].update_one({"_id": existing["_id"]}, {"$set": update_fields})
        rating = await db["ratings"].find_one({"_id": existing["_id"]})
    else:
        new_rating = {
            "user_id": user_obj_id,
            "content_id": content_obj_id,
            **update_fields,
        }
        result = await db["ratings"].insert_one(new_rating)
        rating = await db["ratings"].find_one({"_id": result.inserted_id})

    await _recalculate_content_rating(db, content_obj_id)

    # FR-11 Dgraph: create rated edge
    try:
        from app.core.dgraph_client import add_rated_edge
        await add_rated_edge(current_user.id, content_id, rating_data.score)
    except Exception:
        pass

    return RatingResponse(
        id=str(rating["_id"]),
        user_id=str(rating["user_id"]),
        content_id=str(rating["content_id"]),
        score=rating["score"],
        review=rating.get("review"),
        created_at=rating["created_at"],
    )


@router.get("/my-ratings", response_model=List[RatingResponse])
async def get_my_ratings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-23: Get the authenticated user's rating history."""
    user_obj_id = ObjectId(current_user.id)
    ratings = await (
        db["ratings"]
        .find({"user_id": user_obj_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    return [
        RatingResponse(
            id=str(r["_id"]),
            user_id=str(r["user_id"]),
            content_id=str(r["content_id"]),
            score=r["score"],
            review=r.get("review"),
            created_at=r["created_at"],
        )
        for r in ratings
    ]


@router.get("/{content_id}", response_model=ContentRatingSummary)
async def get_content_ratings(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get rating summary for content, including the current user's score/review."""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

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
        user_review=user_rating.get("review") if user_rating else None,
    )


@router.get("/{content_id}/reviews")
async def get_content_reviews(
    content_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """Get all reviews for a content item (public endpoint)."""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    ratings = await (
        db["ratings"]
        .find({"content_id": content_obj_id, "review": {"$exists": True, "$ne": None}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )

    # Enrich with usernames
    results = []
    for r in ratings:
        user = await db["users"].find_one({"_id": r["user_id"]}, {"username": 1})
        results.append({
            "id": str(r["_id"]),
            "username": user["username"] if user else "unknown",
            "score": r["score"],
            "review": r.get("review"),
            "created_at": r["created_at"],
        })
    return results


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Delete the authenticated user's rating for content."""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    result = await db["ratings"].delete_one(
        {"user_id": ObjectId(current_user.id), "content_id": content_obj_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")

    await _recalculate_content_rating(db, content_obj_id)

    # Remove rated edge in Dgraph
    try:
        from app.core.dgraph_client import remove_rated_edge
        await remove_rated_edge(current_user.id, content_id)
    except Exception:
        pass
