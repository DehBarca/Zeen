"""
Content endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime
from typing import List

from app.core.database import get_mongodb
from app.schemas.content import (
    ContentCreate,
    ContentUpdate,
    ContentResponse,
    ContentType,
)
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter(prefix="/content", tags=["content"])


@router.post("/", response_model=ContentResponse)
async def create_content(
    content_data: ContentCreate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Create new content - Admin only for now"""
    # TODO: Add admin role check
    
    new_content = {
        **content_data.model_dump(),
        "content_type": content_data.content_type.value,
        "release_date": content_data.release_date,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    result = await db["content"].insert_one(new_content)
    new_content["_id"] = result.inserted_id
    
    return ContentResponse(
        id=str(new_content["_id"]),
        **{k: v for k, v in new_content.items() if k != "_id"},
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
):
    """Get content by ID"""
    try:
        content = await db["content"].find_one({"_id": ObjectId(content_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )
    
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )
    
    return ContentResponse(
        id=str(content["_id"]),
        **{k: v for k, v in content.items() if k != "_id"},
    )


@router.get("/", response_model=List[ContentResponse])
async def list_content(
    content_type: ContentType = Query(None),
    genre: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncDatabase = Depends(get_mongodb),
):
    """List content with filters"""
    filter_query = {}
    
    if content_type:
        filter_query["content_type"] = content_type.value
    
    if genre:
        filter_query["genres"] = {"$in": [genre]}
    
    content_list = await db["content"].find(filter_query).skip(skip).limit(limit).to_list(limit)
    
    return [
        ContentResponse(
            id=str(item["_id"]),
            **{k: v for k, v in item.items() if k != "_id"},
        )
        for item in content_list
    ]


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: str,
    content_update: ContentUpdate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Update content - Admin only"""
    try:
        content_obj_id = ObjectId(content_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )
    
    # Build update data
    update_data = {}
    for field, value in content_update.model_dump(exclude_none=True).items():
        update_data[field] = value
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db["content"].update_one(
        {"_id": content_obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )
    
    content = await db["content"].find_one({"_id": content_obj_id})
    
    return ContentResponse(
        id=str(content["_id"]),
        **{k: v for k, v in content.items() if k != "_id"},
    )


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Delete content - Admin only"""
    try:
        content_obj_id = ObjectId(content_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content ID",
        )
    
    result = await db["content"].delete_one({"_id": content_obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )
