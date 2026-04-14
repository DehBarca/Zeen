from motor.motor_asyncio import AsyncClient, AsyncDatabase
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import pydgraph
import chromadb
from app.core.config import settings
from typing import Optional


# MongoDB Connection
mongodb_client: Optional[AsyncClient] = None
mongodb_db: Optional[AsyncDatabase] = None


async def connect_to_mongodb():
    """Connect to MongoDB"""
    global mongodb_client, mongodb_db
    mongodb_client = AsyncClient(settings.DATABASE_URL)
    mongodb_db = mongodb_client["zeen_db"]
    print("Connected to MongoDB")


async def disconnect_from_mongodb():
    """Disconnect from MongoDB"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("Disconnected from MongoDB")


async def get_mongodb() -> AsyncDatabase:
    """Get MongoDB database instance"""
    return mongodb_db


# Cassandra Connection
cassandra_cluster: Optional[Cluster] = None
cassandra_session = None


async def connect_to_cassandra():
    """Connect to Cassandra"""
    global cassandra_cluster, cassandra_session
    try:
        cassandra_cluster = Cluster(
            contact_points=settings.CASSANDRA_HOSTS,
            port=settings.CASSANDRA_PORT
        )
        cassandra_session = cassandra_cluster.connect()
        
        # Create keyspace if it doesn't exist
        cassandra_session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {settings.CASSANDRA_KEYSPACE}
            WITH REPLICATION = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)
        cassandra_session.set_keyspace(settings.CASSANDRA_KEYSPACE)
        print("Connected to Cassandra")
    except Exception as e:
        print(f"Error connecting to Cassandra: {e}")


async def disconnect_from_cassandra():
    """Disconnect from Cassandra"""
    global cassandra_cluster
    if cassandra_cluster:
        cassandra_cluster.shutdown()
        print("Disconnected from Cassandra")


async def get_cassandra_session():
    """Get Cassandra session"""
    return cassandra_session


# Dgraph Connection
dgraph_client: Optional[pydgraph.DgraphClientStub] = None


async def connect_to_dgraph():
    """Connect to Dgraph"""
    global dgraph_client
    try:
        # Dgraph connection (simplified - uses gRPC in production)
        print(f"Dgraph configured at {settings.DGRAPH_URL}")
    except Exception as e:
        print(f"Error connecting to Dgraph: {e}")


# ChromaDB Connection
chroma_client: Optional[chromadb.HttpClient] = None


async def connect_to_chromadb():
    """Connect to ChromaDB"""
    global chroma_client
    try:
        chroma_client = chromadb.HttpClient(host="chromadb", port=8000)
        print("Connected to ChromaDB")
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")


async def get_chromadb_client():
    """Get ChromaDB client"""
    return chroma_client
