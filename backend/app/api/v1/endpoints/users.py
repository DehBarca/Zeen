"""
User endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime

from app.core.database import get_mongodb
from app.schemas.user import UserResponse, UserUpdate, WatchlistResponse
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get user by ID"""
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        is_active=user["is_active"],
        watchlist=[str(cid) for cid in user.get("watchlist", [])],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Update user information - only own profile"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users",
        )
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )
    
    # Build update data
    update_data = {}
    if user_update.email:
        # Check if email already exists
        existing = await db["users"].find_one(
            {"email": user_update.email, "_id": {"$ne": user_obj_id}}
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        update_data["email"] = user_update.email
    
    if user_update.username:
        # Check if username already exists
        existing = await db["users"].find_one(
            {"username": user_update.username, "_id": {"$ne": user_obj_id}}
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use",
            )
        update_data["username"] = user_update.username
    
    if user_update.first_name:
        update_data["first_name"] = user_update.first_name
    if user_update.last_name:
        update_data["last_name"] = user_update.last_name
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db["users"].update_one(
        {"_id": user_obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Get updated user
    user = await db["users"].find_one({"_id": user_obj_id})

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        is_active=user["is_active"],
        watchlist=[str(cid) for cid in user.get("watchlist", [])],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


@router.get("/{user_id}/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the watchlist of a user"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' watchlist",
        )

    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return WatchlistResponse(
        watchlist=[str(cid) for cid in user.get("watchlist", [])]
    )


@router.post("/{user_id}/watchlist/{content_id}", response_model=WatchlistResponse)
async def add_to_watchlist(
    user_id: str,
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Add a content item to the user's watchlist"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other users' watchlist",
        )

    try:
        user_obj_id = ObjectId(user_id)
        content_obj_id = ObjectId(content_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID",
        )

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    await db["users"].update_one(
        {"_id": user_obj_id},
        {"$addToSet": {"watchlist": content_obj_id}},
    )

    user = await db["users"].find_one({"_id": user_obj_id})
    return WatchlistResponse(
        watchlist=[str(cid) for cid in user.get("watchlist", [])]
    )


@router.delete("/{user_id}/watchlist/{content_id}", response_model=WatchlistResponse)
async def remove_from_watchlist(
    user_id: str,
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Remove a content item from the user's watchlist"""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify other users' watchlist",
        )

    try:
        user_obj_id = ObjectId(user_id)
        content_obj_id = ObjectId(content_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID",
        )

    result = await db["users"].update_one(
        {"_id": user_obj_id},
        {"$pull": {"watchlist": content_obj_id}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = await db["users"].find_one({"_id": user_obj_id})
    return WatchlistResponse(
        watchlist=[str(cid) for cid in user.get("watchlist", [])]
    )
