"""
Watch history & playback endpoints — backed by Cassandra.
Covers FR-06 (Playback & Watch Tracking) and FR-07 (Watch History).
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from datetime import datetime
from typing import List

from app.core.database import get_cassandra_session, get_mongodb
from app.schemas.watch_history import (
    PlaybackEventCreate,
    PlaybackEventResponse,
    WatchHistoryEntry,
    WatchHistoryResponse,
)
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter(prefix="/watch", tags=["watch-history"])


def _log_activity(session, user_id: str, action: str, content_id: str = "", details: str = ""):
    """Write an entry to the user_activity table for analytics."""
    if session is None:
        return
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    session.execute(
        "INSERT INTO user_activity (activity_date, event_time, user_id, action, content_id, details) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (date_str, now, user_id, action, content_id, details),
    )


# ── FR-06: Playback events ─────────────────────────────────────────

@router.post("/{content_id}/event", response_model=PlaybackEventResponse, status_code=status.HTTP_201_CREATED)
async def create_playback_event(
    content_id: str,
    event: PlaybackEventCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    """Record a playback event (play, pause, resume, complete)."""
    session = await get_cassandra_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Cassandra unavailable")

    now = datetime.utcnow()
    session.execute(
        "INSERT INTO playback_events (user_id, content_id, event_type, position_seconds, event_time) "
        "VALUES (%s, %s, %s, %s, %s)",
        (current_user.id, content_id, event.event_type.value, event.position_seconds, now),
    )

    _log_activity(session, current_user.id, f"playback_{event.event_type.value}", content_id)

    # If it's a play or complete event, upsert watch_history
    if event.event_type.value in ("play", "complete"):
        db = await get_mongodb()
        from bson import ObjectId
        try:
            content = await db["content"].find_one({"_id": ObjectId(content_id)})
        except Exception:
            content = None
        duration = content.get("duration_minutes", 0) * 60 if content else 0
        completed = event.event_type.value == "complete"

        session.execute(
            "INSERT INTO watch_history (user_id, watched_at, content_id, progress_seconds, duration_seconds, completed) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (current_user.id, now, content_id, event.position_seconds, duration, completed),
        )

    # Sync watched edge in Dgraph
    if event.event_type.value == "play":
        try:
            from app.core.dgraph_client import add_watched_edge
            await add_watched_edge(current_user.id, content_id)
        except Exception:
            pass

    return PlaybackEventResponse(
        user_id=current_user.id,
        content_id=content_id,
        event_type=event.event_type.value,
        position_seconds=event.position_seconds,
        event_time=now,
    )


@router.get("/{content_id}/events", response_model=List[PlaybackEventResponse])
async def get_playback_events(
    content_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get playback events for a specific content item (for resume position)."""
    session = await get_cassandra_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Cassandra unavailable")

    rows = session.execute(
        "SELECT user_id, content_id, event_type, position_seconds, event_time "
        "FROM playback_events WHERE user_id = %s AND content_id = %s LIMIT %s",
        (current_user.id, content_id, limit),
    )
    return [
        PlaybackEventResponse(
            user_id=r.user_id,
            content_id=r.content_id,
            event_type=r.event_type,
            position_seconds=r.position_seconds,
            event_time=r.event_time,
        )
        for r in rows
    ]


@router.get("/{content_id}/resume")
async def get_resume_position(
    content_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the last known playback position for resume."""
    session = await get_cassandra_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Cassandra unavailable")

    rows = session.execute(
        "SELECT position_seconds, event_type FROM playback_events "
        "WHERE user_id = %s AND content_id = %s LIMIT 1",
        (current_user.id, content_id),
    )
    row = rows.one()
    if row is None:
        return {"position_seconds": 0, "completed": False}
    return {
        "position_seconds": row.position_seconds,
        "completed": row.event_type == "complete",
    }


# ── FR-07: Watch history ───────────────────────────────────────────

@router.get("/history/me", response_model=WatchHistoryResponse)
async def get_my_watch_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the authenticated user's full watch history (most recent first)."""
    session = await get_cassandra_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Cassandra unavailable")

    rows = session.execute(
        "SELECT content_id, watched_at, progress_seconds, duration_seconds, completed "
        "FROM watch_history WHERE user_id = %s LIMIT %s",
        (current_user.id, limit),
    )
    entries = [
        WatchHistoryEntry(
            content_id=r.content_id,
            watched_at=r.watched_at,
            progress_seconds=r.progress_seconds,
            duration_seconds=r.duration_seconds,
            completed=r.completed,
        )
        for r in rows
    ]
    return WatchHistoryResponse(user_id=current_user.id, history=entries)


@router.get("/continue-watching")
async def get_continue_watching(
    limit: int = Query(10, ge=1, le=50),
    current_user: UserResponse = Depends(get_current_user),
):
    """FR-08 partial: get titles the user started but didn't complete."""
    session = await get_cassandra_session()
    if session is None:
        raise HTTPException(status_code=503, detail="Cassandra unavailable")

    rows = session.execute(
        "SELECT content_id, watched_at, progress_seconds, duration_seconds, completed "
        "FROM watch_history WHERE user_id = %s LIMIT %s",
        (current_user.id, limit * 3),  # fetch more, then filter
    )

    seen = set()
    results = []
    for r in rows:
        if r.content_id not in seen and not r.completed:
            seen.add(r.content_id)
            results.append({
                "content_id": r.content_id,
                "progress_seconds": r.progress_seconds,
                "duration_seconds": r.duration_seconds,
                "last_watched": r.watched_at.isoformat(),
            })
            if len(results) >= limit:
                break

    return {"continue_watching": results}
