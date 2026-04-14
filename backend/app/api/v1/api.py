"""
API v1 router - aggregates all endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, content


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(content.router)
