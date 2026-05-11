"""
API v1 router - aggregates all endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, content, ratings, watch_history, recommendations, admin

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(content.router)
api_router.include_router(ratings.router)
api_router.include_router(watch_history.router)
api_router.include_router(recommendations.router)
api_router.include_router(admin.router)
