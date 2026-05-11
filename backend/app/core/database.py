from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import chromadb
from app.core.config import settings
from typing import Optional
from urllib.parse import urlparse


# ── MongoDB ─────────────────────────────────────────────────────────

mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongodb():
    global mongodb_client, mongodb_db
    mongodb_client = AsyncIOMotorClient(settings.DATABASE_URL)
    mongodb_db = mongodb_client["zeen_db"]
    print("Connected to MongoDB")


async def disconnect_from_mongodb():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("Disconnected from MongoDB")


async def get_mongodb() -> AsyncIOMotorDatabase:
    return mongodb_db


# ── Cassandra ───────────────────────────────────────────────────────

cassandra_cluster: Optional[Cluster] = None
cassandra_session = None

CASSANDRA_TABLES = [
    # FR-06: Playback events (play, pause, resume, complete)
    """
    CREATE TABLE IF NOT EXISTS playback_events (
        user_id text,
        content_id text,
        event_type text,
        position_seconds int,
        event_time timestamp,
        PRIMARY KEY ((user_id, content_id), event_time)
    ) WITH CLUSTERING ORDER BY (event_time DESC)
    """,
    # FR-07: Watch history per user, ordered by recency
    """
    CREATE TABLE IF NOT EXISTS watch_history (
        user_id text,
        watched_at timestamp,
        content_id text,
        progress_seconds int,
        duration_seconds int,
        completed boolean,
        PRIMARY KEY (user_id, watched_at)
    ) WITH CLUSTERING ORDER BY (watched_at DESC)
    """,
    # FR-15 / FR-30: Activity log for analytics (partitioned by date)
    """
    CREATE TABLE IF NOT EXISTS user_activity (
        activity_date text,
        event_time timestamp,
        user_id text,
        action text,
        content_id text,
        details text,
        PRIMARY KEY (activity_date, event_time)
    ) WITH CLUSTERING ORDER BY (event_time DESC)
    """,
]


async def connect_to_cassandra():
    global cassandra_cluster, cassandra_session
    try:
        cassandra_cluster = Cluster(
            contact_points=settings.CASSANDRA_HOSTS,
            port=settings.CASSANDRA_PORT,
        )
        cassandra_session = cassandra_cluster.connect()

        cassandra_session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
            WITH REPLICATION = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)
        cassandra_session.set_keyspace(settings.CASSANDRA_KEYSPACE)

        for ddl in CASSANDRA_TABLES:
            cassandra_session.execute(ddl)

        print("Connected to Cassandra (tables ready)")
    except Exception as e:
        print(f"Error connecting to Cassandra: {e}")


async def disconnect_from_cassandra():
    global cassandra_cluster
    if cassandra_cluster:
        cassandra_cluster.shutdown()
        print("Disconnected from Cassandra")


async def get_cassandra_session():
    return cassandra_session


# ── Dgraph ──────────────────────────────────────────────────────────
# Dgraph uses HTTP via dgraph_client.py helper; no persistent object needed.

async def connect_to_dgraph():
    """Apply Dgraph schema on startup."""
    try:
        from app.core.dgraph_client import apply_schema
        await apply_schema()
    except Exception as e:
        print(f"Error connecting to Dgraph: {e}")


# ── ChromaDB ────────────────────────────────────────────────────────

chroma_client: Optional[chromadb.HttpClient] = None


async def connect_to_chromadb():
    global chroma_client
    try:
        parsed = urlparse(settings.CHROMADB_URL)
        host = parsed.hostname or "chromadb"
        port = parsed.port or 8000
        chroma_client = chromadb.HttpClient(host=host, port=port)
        print("Connected to ChromaDB")
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")


async def get_chromadb_client():
    return chroma_client
