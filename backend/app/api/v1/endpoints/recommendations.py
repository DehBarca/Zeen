"""
Recommendation & graph endpoints — backed by Dgraph.
Covers FR-09 (Recommendations), FR-14 (Content Similarity), FR-08 partial (Personalized Homepage).
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List
from bson import ObjectId

from app.core.database import get_mongodb, get_cassandra_session
from app.core.dgraph_client import (
    get_recommendations,
    get_similar_content,
    get_user_graph,
)
from app.schemas.content import ContentResponse
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


async def _fetch_content_by_ids(db, content_ids: List[str]) -> List[ContentResponse]:
    """Fetch full content docs from MongoDB for a list of content IDs."""
    if not content_ids:
        return []
    try:
        obj_ids = [ObjectId(cid) for cid in content_ids]
    except Exception:
        return []
    docs = await db["content"].find({"_id": {"$in": obj_ids}}).to_list(len(obj_ids))
    return [
        ContentResponse(
            id=str(d["_id"]),
            **{k: v for k, v in d.items() if k != "_id"},
        )
        for d in docs
    ]


@router.get("/for-you", response_model=List[ContentResponse])
async def recommendations_for_you(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-09: Get graph-based recommendations for the authenticated user."""
    content_ids = await get_recommendations(current_user.id, limit)
    if not content_ids:
        # Fallback: return top-rated content
        docs = await db["content"].find().sort("rating", -1).limit(limit).to_list(limit)
        return [
            ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
            for d in docs
        ]
    return await _fetch_content_by_ids(db, content_ids)


@router.get("/similar/{content_id}", response_model=List[ContentResponse])
async def similar_content(
    content_id: str,
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_mongodb),
):
    """FR-14: Get structurally similar content (shared genres/actors/directors)."""
    content_ids = await get_similar_content(content_id, limit)
    if not content_ids:
        # Fallback: same-genre content
        try:
            source = await db["content"].find_one({"_id": ObjectId(content_id)})
        except Exception:
            source = None
        if source and source.get("genres"):
            docs = (
                await db["content"]
                .find({"genres": {"$in": source["genres"]}, "_id": {"$ne": ObjectId(content_id)}})
                .limit(limit)
                .to_list(limit)
            )
            return [
                ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
                for d in docs
            ]
        return []
    return await _fetch_content_by_ids(db, content_ids)


@router.get("/homepage")
async def personalized_homepage(
    db=Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    FR-08: Personalized homepage with curated rows:
    - Continue Watching (Cassandra)
    - Recommended For You (Dgraph)
    - Trending Now (MongoDB — highest rated)
    - Recently Added (MongoDB — newest)
    """
    # Continue Watching
    continue_watching = []
    session = await get_cassandra_session()
    if session:
        rows = session.execute(
            "SELECT content_id, progress_seconds, duration_seconds, completed "
            "FROM watch_history WHERE user_id = %s LIMIT 30",
            (current_user.id,),
        )
        seen = set()
        for r in rows:
            if r.content_id not in seen and not r.completed:
                seen.add(r.content_id)
                continue_watching.append(r.content_id)
                if len(continue_watching) >= 10:
                    break

    continue_docs = await _fetch_content_by_ids(db, continue_watching)

    # Recommended For You
    rec_ids = await get_recommendations(current_user.id, 10)
    rec_docs = await _fetch_content_by_ids(db, rec_ids)
    if not rec_docs:
        # fallback
        docs = await db["content"].find().sort("rating", -1).limit(10).to_list(10)
        rec_docs = [
            ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
            for d in docs
        ]

    # Trending Now (top rated)
    trending_docs = await db["content"].find().sort("rating", -1).limit(10).to_list(10)
    trending = [
        ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
        for d in trending_docs
    ]

    # Recently Added
    recent_docs = await db["content"].find().sort("created_at", -1).limit(10).to_list(10)
    recently_added = [
        ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
        for d in recent_docs
    ]

    return {
        "continue_watching": continue_docs,
        "recommended_for_you": rec_docs,
        "trending_now": trending,
        "recently_added": recently_added,
    }


@router.get("/user-graph")
async def my_graph(
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the current user's full graph data (watched, rated, saved)."""
    data = await get_user_graph(current_user.id)
    return data or {"message": "No graph data yet"}
