"""
Zeen - Streaming Platform
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import (
    connect_to_mongodb,
    disconnect_from_mongodb,
    connect_to_cassandra,
    disconnect_from_cassandra,
    connect_to_dgraph,
    connect_to_chromadb,
    get_mongodb,
)
from app.api.v1.api import api_router


async def create_indexes():
    """Create MongoDB indexes on startup"""
    db = await get_mongodb()
    await db["content"].create_index([("title", "text"), ("description", "text")])
    await db["ratings"].create_index([("user_id", 1), ("content_id", 1)], unique=True)
    await db["users"].create_index("email", unique=True)
    await db["users"].create_index("username", unique=True)
    await db["content"].create_index([("rating", -1)])
    await db["content"].create_index([("created_at", -1)])
    await db["content"].create_index([("content_type", 1)])
    await db["content"].create_index([("genres", 1)])
    print("✓ MongoDB indexes created")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    print("Starting up Zeen application...")
    await connect_to_mongodb()
    await connect_to_cassandra()
    await connect_to_dgraph()
    await connect_to_chromadb()
    await create_indexes()
    print("✓ All databases connected")

    yield

    print("Shutting down Zeen application...")
    await disconnect_from_mongodb()
    await disconnect_from_cassandra()
    print("✓ All databases disconnected")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Zeen: See it. Feel it. Keep it Zeen - A streaming platform powered by multiple NoSQL databases",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to Zeen - Streaming Platform",
        "version": settings.PROJECT_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
