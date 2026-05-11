"""
Content endpoints
FR-04 Catalog Browsing, FR-13 Content Ingestion, FR-18/19/20/21/22 additional FRs
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from enum import Enum
import re

from app.core.database import get_mongodb
from app.core.semantic_search import (
    delete_content_embedding,
    semantic_search_content_ids,
    upsert_content_embedding,
)
from app.schemas.content import ContentCreate, ContentUpdate, ContentResponse, ContentType
from app.schemas.user import UserResponse, UserRole
from app.api.v1.endpoints.auth import get_current_user, require_admin


router = APIRouter(prefix="/content", tags=["content"])


class SortField(str, Enum):
    RATING = "rating"
    TITLE = "title"
    RELEASE_DATE = "release_date"
    CREATED_AT = "created_at"
    DURATION = "duration_minutes"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@router.post("/", response_model=ContentResponse)
async def create_content(
    content_data: ContentCreate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-13: Create new content — Admin only."""
    new_content = {
        **content_data.model_dump(),
        "content_type": content_data.content_type.value,
        "release_date": content_data.release_date,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db["content"].insert_one(new_content)
    mongo_id = str(result.inserted_id)
    new_content["_id"] = result.inserted_id

    # FR-13 Dgraph: create Content node + genre/actor/director edges
    try:
        from app.core.dgraph_client import create_content_node
        await create_content_node(
            mongo_id,
            content_data.title,
            content_data.genres,
            content_data.cast,
            content_data.directors,
        )
    except Exception:
        pass

    try:
        await upsert_content_embedding(mongo_id, new_content)
    except Exception:
        pass

    return ContentResponse(
        id=mongo_id,
        **{k: v for k, v in new_content.items() if k != "_id"},
    )


@router.post("/batch", response_model=List[ContentResponse])
async def batch_create_content(
    items: List[ContentCreate],
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-34: Batch content ingestion — Admin only."""
    results = []
    for item in items:
        doc = {
            **item.model_dump(),
            "content_type": item.content_type.value,
            "release_date": item.release_date,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        r = await db["content"].insert_one(doc)
        mongo_id = str(r.inserted_id)
        try:
            from app.core.dgraph_client import create_content_node
            await create_content_node(mongo_id, item.title, item.genres, item.cast, item.directors)
        except Exception:
            pass
        try:
            await upsert_content_embedding(mongo_id, doc)
        except Exception:
            pass
        results.append(ContentResponse(id=mongo_id, **{k: v for k, v in doc.items() if k != "_id"}))
    return results


@router.get("/", response_model=List[ContentResponse])
async def list_content(
    content_type: ContentType = Query(None),
    genre: str = Query(None),
    query: str = Query(None, description="Semantic search across title, description, genre, cast, or director"),
    min_similarity: float = Query(0.8, ge=0.0, le=1.0, description="Minimum semantic similarity (0-1) to include results"),
    actor: str = Query(None, description="Filter by actor name"),
    director: str = Query(None, description="Filter by director name"),
    year: int = Query(None, description="FR-18: Filter by release year"),
    min_rating: float = Query(None, ge=0, le=5, description="Minimum rating filter"),
    sort_by: SortField = Query(SortField.CREATED_AT, description="FR-19: Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """FR-04: List content with filters, sorting, and pagination."""
    filter_query = {}

    def _search_matches(term: str):
        regex = {"$regex": term, "$options": "i"}
        return [
            {"title": regex},
            {"description": regex},
            {"genres": {"$elemMatch": regex}},
            {"cast": {"$elemMatch": regex}},
            {"directors": {"$elemMatch": regex}},
        ]

    if content_type:
        filter_query["content_type"] = content_type.value
    if genre:
        filter_query["genres"] = {"$in": [genre]}
    if actor:
        filter_query["cast"] = {"$elemMatch": {"$regex": actor, "$options": "i"}}
    if director:
        filter_query["directors"] = {"$elemMatch": {"$regex": director, "$options": "i"}}
    if year:
        filter_query["release_date"] = {
            "$gte": datetime(year, 1, 1),
            "$lt": datetime(year + 1, 1, 1),
        }
    if min_rating is not None:
        filter_query["rating"] = {"$gte": min_rating}

    sort_dir = 1 if sort_order == SortOrder.ASC else -1

    normalized_query = query.strip() if query else ""
    if normalized_query:
        target_count = max(skip + limit, 20)
        semantic_ids = await semantic_search_content_ids(normalized_query, limit=target_count, min_similarity=min_similarity)

        query_terms = [term for term in re.split(r"\s+", normalized_query) if term]
        regex_filter = dict(filter_query)
        if query_terms:
            if len(query_terms) == 1:
                regex_filter["$or"] = _search_matches(query_terms[0])
            else:
                regex_filter["$and"] = [{"$or": _search_matches(term)} for term in query_terms]
        regex_docs = await db["content"].find(regex_filter).sort(sort_by.value, sort_dir).limit(target_count).to_list(target_count)
        regex_ids = [str(item["_id"]) for item in regex_docs]

        ordered_ids = []
        seen_ids = set()
        for content_id in semantic_ids + regex_ids:
            if content_id not in seen_ids:
                seen_ids.add(content_id)
                ordered_ids.append(content_id)

        if ordered_ids:
            object_ids = []
            for content_id in ordered_ids:
                try:
                    object_ids.append(ObjectId(content_id))
                except Exception:
                    continue

            docs = await db["content"].find({"_id": {"$in": object_ids}, **filter_query}).to_list(len(object_ids))
            docs_by_id = {str(item["_id"]): item for item in docs}
            content_list = [docs_by_id[content_id] for content_id in ordered_ids if content_id in docs_by_id]
        else:
            content_list = []
        content_list = content_list[skip: skip + limit]
    else:
        cursor = db["content"].find(filter_query).sort(sort_by.value, sort_dir).skip(skip).limit(limit)
        content_list = await cursor.to_list(limit)

    return [
        ContentResponse(id=str(item["_id"]), **{k: v for k, v in item.items() if k != "_id"})
        for item in content_list
    ]


@router.get("/top-rated", response_model=List[ContentResponse])
async def top_rated_content(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """FR-20: Get top rated content."""
    docs = await db["content"].find({"rating": {"$gt": 0}}).sort("rating", -1).limit(limit).to_list(limit)
    return [
        ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
        for d in docs
    ]


@router.get("/recently-added", response_model=List[ContentResponse])
async def recently_added_content(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """FR-21: Get most recently added content."""
    docs = await db["content"].find().sort("created_at", -1).limit(limit).to_list(limit)
    return [
        ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
        for d in docs
    ]


@router.get("/genres")
async def list_genres(db: AsyncDatabase = Depends(get_mongodb)):
    """FR-22: List all distinct genres in the catalog."""
    genres = await db["content"].distinct("genres")
    return {"genres": sorted(genres)}


@router.get("/stats")
async def content_stats(db: AsyncDatabase = Depends(get_mongodb)):
    """FR-28: Content count by type and genre."""
    pipeline_type = [
        {"$group": {"_id": "$content_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_type = await db["content"].aggregate(pipeline_type).to_list(20)

    pipeline_genre = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_genre = await db["content"].aggregate(pipeline_genre).to_list(50)

    total = await db["content"].count_documents({})

    return {
        "total": total,
        "by_type": {r["_id"]: r["count"] for r in by_type},
        "by_genre": {r["_id"]: r["count"] for r in by_genre},
    }


@router.get("/cast-search")
async def search_cast_and_directors(
    query: str = Query(..., min_length=1),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """FR-32: Search for content by cast member or director name."""
    filter_q = {
        "$or": [
            {"cast": {"$elemMatch": {"$regex": query, "$options": "i"}}},
            {"directors": {"$elemMatch": {"$regex": query, "$options": "i"}}},
        ]
    }
    docs = await db["content"].find(filter_q).limit(20).to_list(20)
    return [
        ContentResponse(id=str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"})
        for d in docs
    ]


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: str, db: AsyncDatabase = Depends(get_mongodb)):
    """Get content by ID"""
    try:
        content = await db["content"].find_one({"_id": ObjectId(content_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    return ContentResponse(id=str(content["_id"]), **{k: v for k, v in content.items() if k != "_id"})


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: str,
    content_update: ContentUpdate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """Update content — Admin only"""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    update_data = {k: v for k, v in content_update.model_dump(exclude_none=True).items()}
    update_data["updated_at"] = datetime.utcnow()

    result = await db["content"].update_one({"_id": content_obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    content = await db["content"].find_one({"_id": content_obj_id})
    try:
        await upsert_content_embedding(str(content_obj_id), content)
    except Exception:
        pass
    return ContentResponse(id=str(content["_id"]), **{k: v for k, v in content.items() if k != "_id"})


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """Delete content — Admin only"""
    try:
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID")

    result = await db["content"].delete_one({"_id": content_obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    try:
        await delete_content_embedding(str(content_obj_id))
    except Exception:
        pass
