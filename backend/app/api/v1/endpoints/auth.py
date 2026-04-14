"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from motor.motor_asyncio import AsyncDatabase
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )
    
    user = await db["users"].find_one({"_id": ObjectId(token_data.user_id)})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        is_active=user["is_active"],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncDatabase = Depends(get_mongodb),
):
    """Register a new user"""
    # Check if user already exists
    existing_user = await db["users"].find_one(
        {"$or": [{"email": user_data.email}, {"username": user_data.username}]}
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    from datetime import datetime
    
    new_user = {
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": hashed_password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    result = await db["users"].insert_one(new_user)
    new_user["_id"] = result.inserted_id
    
    return UserResponse(
        id=str(new_user["_id"]),
        email=new_user["email"],
        username=new_user["username"],
        first_name=new_user["first_name"],
        last_name=new_user["last_name"],
        is_active=new_user["is_active"],
        created_at=new_user["created_at"],
        updated_at=new_user["updated_at"],
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncDatabase = Depends(get_mongodb),
):
    """Login user and return access token"""
    # Find user by email
    user = await db["users"].find_one({"email": credentials.email})
    
    if user is None or not verify_password(
        credentials.password, user["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    # Create access token
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]},
        expires_delta=access_token_expires,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user
