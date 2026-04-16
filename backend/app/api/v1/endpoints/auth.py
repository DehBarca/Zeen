"""
Authentication endpoints
FR-01 User Registration, FR-02 User Login, FR-16 Logout, FR-17 Change Password
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from bson import ObjectId

from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    TokenData,
)
from app.core.database import get_mongodb
from app.core.config import settings
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    ChangePassword,
    Token,
)


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncDatabase = Depends(get_mongodb),
) -> UserResponse:
    """Get current user from JWT token"""
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user = await db["users"].find_one({"_id": ObjectId(token_data.user_id)})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

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


async def require_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Dependency that requires admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncDatabase = Depends(get_mongodb)):
    """FR-01: Register a new user"""
    existing = await db["users"].find_one(
        {"$or": [{"email": user_data.email}, {"username": user_data.username}]}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already registered")

    hashed_password = get_password_hash(user_data.password)
    now = datetime.utcnow()

    new_user = {
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": hashed_password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "is_active": True,
        "role": user_data.role.value,
        "watchlist": [],
        "profiles": [],
        "created_at": now,
        "updated_at": now,
    }

    result = await db["users"].insert_one(new_user)
    mongo_id = str(result.inserted_id)

    # FR-01 Dgraph: create User node
    try:
        from app.core.dgraph_client import create_user_node
        await create_user_node(mongo_id, user_data.username, user_data.email)
    except Exception:
        pass

    return UserResponse(
        id=mongo_id,
        email=new_user["email"],
        username=new_user["username"],
        first_name=new_user["first_name"],
        last_name=new_user["last_name"],
        is_active=True,
        role=new_user["role"],
        watchlist=[],
        profiles=[],
        created_at=now,
        updated_at=now,
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncDatabase = Depends(get_mongodb)):
    """FR-02: Login and return access token"""
    user = await db["users"].find_one({"email": credentials.email})
    if user is None or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-17: Change the authenticated user's password"""
    user = await db["users"].find_one({"_id": ObjectId(current_user.id)})
    if not verify_password(data.current_password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    new_hash = get_password_hash(data.new_password)
    await db["users"].update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"hashed_password": new_hash, "updated_at": datetime.utcnow()}},
    )
    return {"message": "Password changed successfully"}


@router.post("/validate-token")
async def validate_token(current_user: UserResponse = Depends(get_current_user)):
    """FR-16: Validate the current token (acts as a session check)"""
    return {"valid": True, "user_id": current_user.id, "email": current_user.email}
