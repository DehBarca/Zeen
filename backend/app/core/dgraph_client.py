"""
Dgraph HTTP client - communicates with Dgraph Alpha via REST API.
"""
import httpx
import json
from typing import Optional, List, Dict, Any
from app.core.config import settings


DGRAPH_HTTP = settings.DGRAPH_URL  # e.g. http://dgraph:8080


# ── Schema ──────────────────────────────────────────────────────────

DGRAPH_SCHEMA = """
    user_id: string @index(exact) .
    username: string @index(exact, term) .
    email: string @index(exact) .
    content_id: string @index(exact) .
    title: string @index(exact, term, fulltext) .
    name: string @index(exact, term) .
    rating_score: float .
    watched_at: datetime .

    watched: [uid] @reverse .
    rated: [uid] @reverse .
    saved: [uid] @reverse .
    has_genre: [uid] @reverse .
    has_actor: [uid] @reverse .
    has_director: [uid] @reverse .

    type User {
        user_id
        username
        email
        watched
        rated
        saved
    }

    type Content {
        content_id
        title
        has_genre
        has_actor
        has_director
    }

    type Genre {
        name
    }

    type Actor {
        name
    }

    type Director {
        name
    }
"""


async def apply_schema():
    """Apply the Dgraph schema on startup."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{DGRAPH_HTTP}/alter", data=DGRAPH_SCHEMA, timeout=10)
        r.raise_for_status()
        print("✓ Dgraph schema applied")


# ── Low-level helpers ───────────────────────────────────────────────

async def _mutate(mutations: Dict[str, Any]) -> Dict:
    """Run a JSON mutation against Dgraph."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{DGRAPH_HTTP}/mutate?commitNow=true",
            headers={"Content-Type": "application/json"},
            json=mutations,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


async def _query(q: str, variables: Optional[Dict] = None) -> Dict:
    """Run a DQL query against Dgraph."""
    payload: Dict[str, Any] = {"query": q}
    if variables:
        payload["variables"] = variables
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{DGRAPH_HTTP}/query",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


# ── Node helpers ────────────────────────────────────────────────────

async def _find_uid(predicate: str, value: str) -> Optional[str]:
    """Find a node's UID by an indexed predicate."""
    q = f'{{ node(func: eq({predicate}, "{value}")) {{ uid }} }}'
    data = await _query(q)
    nodes = data.get("data", {}).get("node", [])
    return nodes[0]["uid"] if nodes else None


async def _get_or_create(dtype: str, name_value: str) -> str:
    """Get or create a Genre/Actor/Director node by name. Returns UID."""
    uid = await _find_uid("name", name_value)
    if uid:
        return uid
    result = await _mutate({
        "set": [{"dgraph.type": dtype, "name": name_value}]
    })
    uids = result.get("data", {}).get("uids", {})
    return list(uids.values())[0] if uids else await _find_uid("name", name_value)


# ── Public API ──────────────────────────────────────────────────────

async def create_user_node(mongo_id: str, username: str, email: str):
    """FR-01: create a User node in Dgraph when a new user registers."""
    existing = await _find_uid("user_id", mongo_id)
    if existing:
        return existing
    result = await _mutate({
        "set": [{
            "dgraph.type": "User",
            "user_id": mongo_id,
            "username": username,
            "email": email,
        }]
    })
    uids = result.get("data", {}).get("uids", {})
    return list(uids.values())[0] if uids else None


async def update_user_node(mongo_id: str, username: Optional[str] = None):
    """FR-03: keep User node in sync after profile update."""
    uid = await _find_uid("user_id", mongo_id)
    if not uid:
        return
    obj: Dict[str, Any] = {"uid": uid}
    if username:
        obj["username"] = username
    await _mutate({"set": [obj]})


async def create_content_node(
    mongo_id: str,
    title: str,
    genres: List[str],
    cast: List[str],
    directors: List[str],
):
    """FR-13: create a Content node + edges to Genre/Actor/Director."""
    existing = await _find_uid("content_id", mongo_id)
    if existing:
        return existing
    content_obj: Dict[str, Any] = {
        "dgraph.type": "Content",
        "content_id": mongo_id,
        "title": title,
    }
    # link genres
    genre_edges = []
    for g in genres:
        gid = await _get_or_create("Genre", g)
        genre_edges.append({"uid": gid})
    if genre_edges:
        content_obj["has_genre"] = genre_edges
    # link actors
    actor_edges = []
    for a in cast:
        aid = await _get_or_create("Actor", a)
        actor_edges.append({"uid": aid})
    if actor_edges:
        content_obj["has_actor"] = actor_edges
    # link directors
    dir_edges = []
    for d in directors:
        did = await _get_or_create("Director", d)
        dir_edges.append({"uid": did})
    if dir_edges:
        content_obj["has_director"] = dir_edges

    result = await _mutate({"set": [content_obj]})
    uids = result.get("data", {}).get("uids", {})
    return list(uids.values())[0] if uids else None


async def add_watched_edge(user_mongo_id: str, content_mongo_id: str):
    """FR-06: record that a user watched a content item."""
    user_uid = await _find_uid("user_id", user_mongo_id)
    content_uid = await _find_uid("content_id", content_mongo_id)
    if not user_uid or not content_uid:
        return
    await _mutate({"set": [{"uid": user_uid, "watched": [{"uid": content_uid}]}]})


async def add_rated_edge(user_mongo_id: str, content_mongo_id: str, score: float):
    """FR-11: record that a user rated a content item."""
    user_uid = await _find_uid("user_id", user_mongo_id)
    content_uid = await _find_uid("content_id", content_mongo_id)
    if not user_uid or not content_uid:
        return
    await _mutate({"set": [{
        "uid": user_uid,
        "rated": [{"uid": content_uid, "rating_score": score}],
    }]})


async def remove_rated_edge(user_mongo_id: str, content_mongo_id: str):
    """Remove a rated edge when a user deletes their rating."""
    user_uid = await _find_uid("user_id", user_mongo_id)
    content_uid = await _find_uid("content_id", content_mongo_id)
    if not user_uid or not content_uid:
        return
    await _mutate({"delete": [{"uid": user_uid, "rated": [{"uid": content_uid}]}]})


async def add_saved_edge(user_mongo_id: str, content_mongo_id: str):
    """FR-10: watchlist – record a 'saved' edge."""
    user_uid = await _find_uid("user_id", user_mongo_id)
    content_uid = await _find_uid("content_id", content_mongo_id)
    if not user_uid or not content_uid:
        return
    await _mutate({"set": [{"uid": user_uid, "saved": [{"uid": content_uid}]}]})


async def remove_saved_edge(user_mongo_id: str, content_mongo_id: str):
    """FR-10: watchlist – remove a 'saved' edge."""
    user_uid = await _find_uid("user_id", user_mongo_id)
    content_uid = await _find_uid("content_id", content_mongo_id)
    if not user_uid or not content_uid:
        return
    await _mutate({"delete": [{"uid": user_uid, "saved": [{"uid": content_uid}]}]})


async def get_recommendations(user_mongo_id: str, limit: int = 10) -> List[str]:
    """
    FR-09: Graph-based recommendations.
    Traverse User → watched/rated → Content → has_genre/has_actor/has_director
    → other Content nodes not yet watched by the user.
    Returns a list of content mongo_ids.
    """
    q = """
    {
        var(func: eq(user_id, "%s")) {
            watched { watched_cids as content_id }
            rated  { rated_cids as content_id }

            watched @filter(has(has_genre)) {
                has_genre {
                    ~has_genre @filter(NOT eq(content_id, val(watched_cids)) AND NOT eq(content_id, val(rated_cids))) {
                        genre_recs as content_id
                    }
                }
            }
            watched @filter(has(has_actor)) {
                has_actor {
                    ~has_actor @filter(NOT eq(content_id, val(watched_cids)) AND NOT eq(content_id, val(rated_cids))) {
                        actor_recs as content_id
                    }
                }
            }
            watched @filter(has(has_director)) {
                has_director {
                    ~has_director @filter(NOT eq(content_id, val(watched_cids)) AND NOT eq(content_id, val(rated_cids))) {
                        dir_recs as content_id
                    }
                }
            }
        }

        recommendations(func: has(content_id), first: %d) @filter(
            eq(content_id, val(genre_recs)) OR
            eq(content_id, val(actor_recs)) OR
            eq(content_id, val(dir_recs))
        ) {
            content_id
        }
    }
    """ % (user_mongo_id, limit)

    try:
        data = await _query(q)
        recs = data.get("data", {}).get("recommendations", [])
        return [r["content_id"] for r in recs if "content_id" in r]
    except Exception:
        return []


async def get_similar_content(content_mongo_id: str, limit: int = 10) -> List[str]:
    """
    FR-14: Content similarity via shared Genre/Actor/Director edges.
    Returns content mongo_ids of similar titles.
    """
    q = """
    {
        var(func: eq(content_id, "%s")) {
            has_genre {
                ~has_genre {
                    genre_sim as content_id
                }
            }
            has_actor {
                ~has_actor {
                    actor_sim as content_id
                }
            }
            has_director {
                ~has_director {
                    dir_sim as content_id
                }
            }
        }

        similar(func: has(content_id), first: %d) @filter(
            (eq(content_id, val(genre_sim)) OR eq(content_id, val(actor_sim)) OR eq(content_id, val(dir_sim)))
            AND NOT eq(content_id, "%s")
        ) {
            content_id
        }
    }
    """ % (content_mongo_id, limit, content_mongo_id)

    try:
        data = await _query(q)
        sims = data.get("data", {}).get("similar", [])
        return [s["content_id"] for s in sims if "content_id" in s]
    except Exception:
        return []


async def get_user_graph(user_mongo_id: str) -> Dict:
    """Get full user graph data (watched, rated, saved) for analytics."""
    q = """
    {
        user(func: eq(user_id, "%s")) {
            uid
            user_id
            username
            watched { content_id title }
            rated { content_id title rating_score }
            saved { content_id title }
        }
    }
    """ % user_mongo_id

    try:
        data = await _query(q)
        users = data.get("data", {}).get("user", [])
        return users[0] if users else {}
    except Exception:
        return {}


async def get_content_engagement(content_mongo_id: str) -> Dict:
    """FR-15: count how many users watched/rated a content item."""
    q = """
    {
        content(func: eq(content_id, "%s")) {
            uid
            content_id
            title
            watchers: ~watched { count(uid) }
            raters: ~rated { count(uid) }
            savers: ~saved { count(uid) }
        }
    }
    """ % content_mongo_id

    try:
        data = await _query(q)
        items = data.get("data", {}).get("content", [])
        return items[0] if items else {}
    except Exception:
        return {}
