"""
Admin & Analytics endpoints
FR-15 Platform Analytics, FR-26 Content Statistics, FR-29 User Activity Summary,
FR-30 Trending Content, FR-35 Database Health Check
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase as AsyncDatabase
from datetime import datetime, timedelta

from app.core.database import get_mongodb, get_cassandra_session
from app.schemas.user import UserResponse
from app.api.v1.endpoints.auth import require_admin


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics")
async def platform_analytics(
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """
    FR-15: Platform-wide analytics dashboard.
    - User growth, active users
    - Content stats
    - Rating stats
    - Activity from Cassandra
    """
    # User metrics
    total_users = await db["users"].count_documents({})
    active_users = await db["users"].count_documents({"is_active": True})
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users_30d = await db["users"].count_documents({"created_at": {"$gte": thirty_days_ago}})

    # Content metrics
    total_content = await db["content"].count_documents({})
    pipeline_type = [
        {"$group": {"_id": "$content_type", "count": {"$sum": 1}}},
    ]
    by_type = await db["content"].aggregate(pipeline_type).to_list(10)

    # Rating metrics
    total_ratings = await db["ratings"].count_documents({})
    pipeline_avg = [
        {"$group": {"_id": None, "avg": {"$avg": "$score"}, "count": {"$sum": 1}}},
    ]
    rating_agg = await db["ratings"].aggregate(pipeline_avg).to_list(1)
    avg_rating = round(rating_agg[0]["avg"], 2) if rating_agg else 0

    # Top rated content
    pipeline_top = [
        {"$match": {"rating": {"$gt": 0}}},
        {"$sort": {"rating": -1}},
        {"$limit": 5},
        {"$project": {"title": 1, "rating": 1, "content_type": 1}},
    ]
    top_rated = await db["content"].aggregate(pipeline_top).to_list(5)

    # Most rated content (by number of ratings)
    pipeline_most_rated = [
        {"$group": {"_id": "$content_id", "count": {"$sum": 1}, "avg": {"$avg": "$score"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    most_rated = await db["ratings"].aggregate(pipeline_most_rated).to_list(5)

    # Activity from Cassandra
    activity_summary = {}
    session = await get_cassandra_session()
    if session:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        rows = session.execute(
            "SELECT action, count(*) as cnt FROM user_activity WHERE activity_date = %s GROUP BY activity_date, event_time ALLOW FILTERING",
            (today,),
        )
        # Cassandra doesn't support GROUP BY on non-PK columns easily,
        # so we aggregate in Python
        action_counts = {}
        for r in rows:
            action_counts[r.action] = action_counts.get(r.action, 0) + 1
        activity_summary = {"today": action_counts}

    # Dgraph engagement
    dgraph_stats = {}
    try:
        from app.core.dgraph_client import _query
        data = await _query("""
        {
            total_users(func: type(User)) { count(uid) }
            total_content(func: type(Content)) { count(uid) }
            total_genres(func: type(Genre)) { count(uid) }
            total_actors(func: type(Actor)) { count(uid) }
            total_directors(func: type(Director)) { count(uid) }
        }
        """)
        d = data.get("data", {})
        dgraph_stats = {
            "graph_users": d.get("total_users", [{}])[0].get("count", 0),
            "graph_content": d.get("total_content", [{}])[0].get("count", 0),
            "graph_genres": d.get("total_genres", [{}])[0].get("count", 0),
            "graph_actors": d.get("total_actors", [{}])[0].get("count", 0),
            "graph_directors": d.get("total_directors", [{}])[0].get("count", 0),
        }
    except Exception:
        dgraph_stats = {"status": "unavailable"}

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_last_30_days": new_users_30d,
        },
        "content": {
            "total": total_content,
            "by_type": {r["_id"]: r["count"] for r in by_type},
        },
        "ratings": {
            "total": total_ratings,
            "average_score": avg_rating,
            "top_rated": [
                {"title": t["title"], "rating": t["rating"], "type": t.get("content_type")}
                for t in top_rated
            ],
        },
        "activity": activity_summary,
        "dgraph": dgraph_stats,
    }


@router.get("/user-growth")
async def user_growth(
    days: int = Query(30, ge=1, le=365),
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-29: User registration growth over time."""
    pipeline = [
        {"$match": {"created_at": {"$gte": datetime.utcnow() - timedelta(days=days)}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    results = await db["users"].aggregate(pipeline).to_list(days)
    return {"growth": [{"date": r["_id"], "registrations": r["count"]} for r in results]}


@router.get("/trending")
async def trending_content(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncDatabase = Depends(get_mongodb),
    current_user: UserResponse = Depends(require_admin),
):
    """FR-30: Most recently rated content (trending)."""
    since = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": "$content_id",
            "rating_count": {"$sum": 1},
            "avg_score": {"$avg": "$score"},
        }},
        {"$sort": {"rating_count": -1}},
        {"$limit": limit},
    ]
    trending = await db["ratings"].aggregate(pipeline).to_list(limit)

    # Enrich with content details
    from bson import ObjectId
    results = []
    for t in trending:
        content = await db["content"].find_one({"_id": t["_id"]})
        results.append({
            "content_id": str(t["_id"]),
            "title": content["title"] if content else "Unknown",
            "rating_count": t["rating_count"],
            "avg_score": round(t["avg_score"], 1),
        })
    return {"trending": results}


@router.get("/health")
async def database_health(
    current_user: UserResponse = Depends(require_admin),
):
    """FR-35: Health check for all databases."""
    health = {}

    # MongoDB
    try:
        db = await get_mongodb()
        await db.command("ping")
        health["mongodb"] = "healthy"
    except Exception as e:
        health["mongodb"] = f"unhealthy: {e}"

    # Cassandra
    try:
        session = await get_cassandra_session()
        if session:
            session.execute("SELECT now() FROM system.local")
            health["cassandra"] = "healthy"
        else:
            health["cassandra"] = "not connected"
    except Exception as e:
        health["cassandra"] = f"unhealthy: {e}"

    # Dgraph
    try:
        import httpx
        from app.core.config import settings
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{settings.DGRAPH_URL}/health", timeout=5)
            health["dgraph"] = "healthy" if r.status_code == 200 else f"status {r.status_code}"
    except Exception as e:
        health["dgraph"] = f"unhealthy: {e}"

    # ChromaDB
    try:
        from app.core.database import get_chromadb_client
        chroma = await get_chromadb_client()
        if chroma:
            chroma.heartbeat()
            health["chromadb"] = "healthy"
        else:
            health["chromadb"] = "not connected"
    except Exception as e:
        health["chromadb"] = f"unhealthy: {e}"

    all_healthy = all(v == "healthy" for v in health.values())
    return {"overall": "healthy" if all_healthy else "degraded", "databases": health}
