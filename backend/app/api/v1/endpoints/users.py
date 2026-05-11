"""
User endpoints
FR-03 Profile Management, FR-10 Watchlist, FR-12 Multi-Profile,
FR-24 Admin List Users, FR-25 Admin Deactivate, FR-32 Delete Account, FR-33 Search Users
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId
from datetime import datetime
from typing import List
import uuid

from app.core.database import get_mongodb
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    WatchlistResponse,
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
)
from app.api.v1.endpoints.auth import get_current_user, require_admin


router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        is_active=user["is_active"],
        role=user.get("role", "user"),
        watchlist=[str(cid) for cid in user.get("watchlist", [])],
        profiles=user.get("profiles", []),
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


# ── FR-24: Admin — list all users ──────────────────────────────────

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None, description="FR-33: Search by username"),
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-24 / FR-33: List all users (admin) or search by username."""
    filt = {}
    if search:
        filt["username"] = {"$regex": search, "$options": "i"}
    users = await db["users"].find(filt).skip(skip).limit(limit).to_list(limit)
    return [_user_response(u) for u in users]


# ── FR-03: Profile management ─────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get user by ID"""
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-03: Update user profile — own profile only."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update other users")

    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    update_data = {}
    if user_update.email:
        existing = await db["users"].find_one({"email": user_update.email, "_id": {"$ne": user_obj_id}})
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        update_data["email"] = user_update.email

    if user_update.username:
        existing = await db["users"].find_one({"username": user_update.username, "_id": {"$ne": user_obj_id}})
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already in use")
        update_data["username"] = user_update.username

    if user_update.first_name:
        update_data["first_name"] = user_update.first_name
    if user_update.last_name:
        update_data["last_name"] = user_update.last_name

    update_data["updated_at"] = datetime.utcnow()

    result = await db["users"].update_one({"_id": user_obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # FR-03 Dgraph: keep User node in sync
    if user_update.username:
        try:
            from app.core.dgraph_client import update_user_node
            await update_user_node(user_id, username=user_update.username)
        except Exception:
            pass

    user = await db["users"].find_one({"_id": user_obj_id})
    return _user_response(user)


# ── FR-25: Admin — deactivate / activate user ──────────────────────

@router.patch("/{user_id}/activate")
async def toggle_user_active(
    user_id: str,
    active: bool = Query(...),
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-25: Activate or deactivate a user (admin only)."""
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    result = await db["users"].update_one(
        {"_id": user_obj_id},
        {"$set": {"is_active": active, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": f"User {'activated' if active else 'deactivated'}"}


# ── FR-32: Delete own account ──────────────────────────────────────

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-32: Delete own account."""
    if user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete other users")
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    await db["users"].delete_one({"_id": user_obj_id})
    await db["ratings"].delete_many({"user_id": user_obj_id})


# ── FR-10: Watchlist ───────────────────────────────────────────────

@router.get("/{user_id}/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' watchlist")
    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return WatchlistResponse(watchlist=[str(cid) for cid in user.get("watchlist", [])])


@router.post("/{user_id}/watchlist/{content_id}", response_model=WatchlistResponse)
async def add_to_watchlist(
    user_id: str,
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify other users' watchlist")
    try:
        user_obj_id = ObjectId(user_id)
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")

    content = await db["content"].find_one({"_id": content_obj_id})
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    await db["users"].update_one({"_id": user_obj_id}, {"$addToSet": {"watchlist": content_obj_id}})

    # FR-10 Dgraph: add saved edge
    try:
        from app.core.dgraph_client import add_saved_edge
        await add_saved_edge(user_id, content_id)
    except Exception:
        pass

    user = await db["users"].find_one({"_id": user_obj_id})
    return WatchlistResponse(watchlist=[str(cid) for cid in user.get("watchlist", [])])


@router.delete("/{user_id}/watchlist/{content_id}", response_model=WatchlistResponse)
async def remove_from_watchlist(
    user_id: str,
    content_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify other users' watchlist")
    try:
        user_obj_id = ObjectId(user_id)
        content_obj_id = ObjectId(content_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")

    result = await db["users"].update_one({"_id": user_obj_id}, {"$pull": {"watchlist": content_obj_id}})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # FR-10 Dgraph: remove saved edge
    try:
        from app.core.dgraph_client import remove_saved_edge
        await remove_saved_edge(user_id, content_id)
    except Exception:
        pass

    user = await db["users"].find_one({"_id": user_obj_id})
    return WatchlistResponse(watchlist=[str(cid) for cid in user.get("watchlist", [])])


# ── FR-12: Multi-Profile Support ───────────────────────────────────

@router.get("/{user_id}/profiles", response_model=List[ProfileResponse])
async def list_profiles(
    user_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """List all profiles for a user."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' profiles")
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    profiles = user.get("profiles", [])
    return [
        ProfileResponse(
            profile_id=p["profile_id"],
            name=p["name"],
            avatar_url=p.get("avatar_url"),
            maturity_level=p.get("maturity_level", "adult"),
            created_at=p["created_at"],
        )
        for p in profiles
    ]


@router.post("/{user_id}/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    user_id: str,
    profile_data: ProfileCreate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-12: Create a new profile (max 5 per account)."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify other users' profiles")

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    profiles = user.get("profiles", [])
    if len(profiles) >= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 5 profiles per account")

    now = datetime.utcnow()
    new_profile = {
        "profile_id": str(uuid.uuid4()),
        "name": profile_data.name,
        "avatar_url": profile_data.avatar_url,
        "maturity_level": profile_data.maturity_level,
        "created_at": now,
    }

    await db["users"].update_one({"_id": ObjectId(user_id)}, {"$push": {"profiles": new_profile}})

    return ProfileResponse(**new_profile)


@router.put("/{user_id}/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    user_id: str,
    profile_id: str,
    profile_update: ProfileUpdate,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-12: Update an existing profile."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify other users' profiles")

    update_fields = {}
    if profile_update.name is not None:
        update_fields["profiles.$.name"] = profile_update.name
    if profile_update.avatar_url is not None:
        update_fields["profiles.$.avatar_url"] = profile_update.avatar_url
    if profile_update.maturity_level is not None:
        update_fields["profiles.$.maturity_level"] = profile_update.maturity_level

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db["users"].update_one(
        {"_id": ObjectId(user_id), "profiles.profile_id": profile_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    for p in user.get("profiles", []):
        if p["profile_id"] == profile_id:
            return ProfileResponse(
                profile_id=p["profile_id"],
                name=p["name"],
                avatar_url=p.get("avatar_url"),
                maturity_level=p.get("maturity_level", "adult"),
                created_at=p["created_at"],
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


@router.delete("/{user_id}/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    user_id: str,
    profile_id: str,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-12: Delete a profile."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify other users' profiles")
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"profiles": {"profile_id": profile_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
