# Zeen - Streaming Platform

**See it. Feel it. Keep it Zeen**

Zeen is a modern streaming platform prototype built with **React**, **TypeScript**, and **FastAPI**. It demonstrates how a media application can combine multiple NoSQL databases to handle users, content metadata, analytics, recommendations, and semantic search in one system.

## What the app does

- Browse movies, series, and episodes from a catalog
- Search content by title, description, genres, cast, and directors
- Open a detail modal with banner, poster, description, duration, categories, rating, and play action
- Authenticate users with JWT
- Separate admin and regular-user flows
- Prepare the backend for analytics and recommendation workflows

## Database roles

Zeen uses each database for a specific part of the product:

- **MongoDB** stores the main application documents: users, content catalog entries, movie metadata, profiles, and update timestamps.
- **Cassandra** is reserved for high-volume watch history and event-style data, where fast writes and time-based queries matter.
- **Dgraph** models relationships for recommendations, such as which content a user watches, preferred genres, actors, and directors.
- **ChromaDB** stores local embeddings for semantic search so users can search with natural language and still find relevant titles.

## Database keys, fields, and where they are used

### MongoDB

MongoDB stores the main documents for the application.

**Why MongoDB for this data**

- User profiles and content metadata are document-shaped and change over time, so a schema-flexible document store fits better than a rigid relational model.
- The app frequently reads and updates whole user/content documents, which is a common MongoDB strength.
- Content cards, profile data, and admin edits benefit from keeping nested arrays like `genres`, `cast`, `directors`, `watchlist`, and `profiles` inside the document.

**Collections and fields**

- `users`: `_id`, `email`, `username`, `hashed_password`, `first_name`, `last_name`, `is_active`, `role`, `watchlist`, `profiles`, `created_at`, `updated_at`
- `content`: `_id`, `title`, `description`, `content_type`, `duration_minutes`, `release_date`, `poster_url`, `banner_url`, `rating`, `genres`, `cast`, `directors`, `created_at`, `updated_at`

**Why these keys/fields**

- `_id` is the natural primary key for direct document lookup and for linking to Dgraph and ChromaDB.
- `email` and `username` are the main login and uniqueness fields because authentication and sign-up checks need fast equality lookups.
- `role`, `is_active`, `watchlist`, and `profiles` model user state without requiring extra joins.
- `content_type`, `genres`, `cast`, and `directors` are queryable fields because the UI filters, search, and semantic index all need them.
- `created_at` and `updated_at` support sorting, recent content views, and admin audit flows.

**Where it is used**

```python
# backend/app/api/v1/endpoints/auth.py
user = await db["users"].find_one({"email": credentials.email})

new_user = {
	"email": user_data.email,
	"username": user_data.username,
	"hashed_password": hashed_password,
	"role": user_data.role.value,
	"watchlist": [],
	"profiles": [],
}
```

```python
# backend/app/api/v1/endpoints/content.py
new_content = {
	**content_data.model_dump(),
	"content_type": content_data.content_type.value,
	"release_date": content_data.release_date,
	"created_at": datetime.utcnow(),
	"updated_at": datetime.utcnow(),
}
```

### Cassandra

Cassandra stores high-volume event and history data.

**Why Cassandra for this data**

- Playback and watch events are append-heavy and grow quickly, so Cassandra handles that write volume better than a document store.
- The app needs recent history by user and time-ordered lookups, which matches Cassandra's partition + clustering key model.
- Event data is mostly read by user and recency, not by many ad hoc joins, so Cassandra is a good fit.

**Keyspaces and tables**

- Keyspace: `zeen_keyspace`
- `playback_events`: `user_id`, `content_id`, `event_type`, `position_seconds`, `event_time`
  - Primary key: `((user_id, content_id), event_time)`
- `watch_history`: `user_id`, `watched_at`, `content_id`, `progress_seconds`, `duration_seconds`, `completed`
  - Primary key: `(user_id, watched_at)`
- `user_activity`: `activity_date`, `event_time`, `user_id`, `action`, `content_id`, `details`
  - Primary key: `(activity_date, event_time)`

**Why these keys**

- `playback_events` uses `(user_id, content_id)` as the partition key because resume position and playback history are always queried per user and content pair.
- `event_time` is the clustering key so the newest playback event appears first, which helps resume playback and recent event checks.
- `watch_history` uses `user_id` as the partition key because history is primarily read per user.
- `watched_at` is the clustering key because the UI and analytics need the most recent entries first.
- `user_activity` uses `activity_date` as the partition key so daily analytics and admin summaries can scan one day at a time.
- `event_time` as clustering key preserves chronological ordering within each day.

**Where it is used**

```python
# backend/app/api/v1/endpoints/watch_history.py
session.execute(
	"INSERT INTO playback_events (user_id, content_id, event_type, position_seconds, event_time) "
	"VALUES (%s, %s, %s, %s, %s)",
	(current_user.id, content_id, event.event_type.value, event.position_seconds, now),
)
```

```python
# backend/app/api/v1/endpoints/watch_history.py
session.execute(
	"INSERT INTO watch_history (user_id, watched_at, content_id, progress_seconds, duration_seconds, completed) "
	"VALUES (%s, %s, %s, %s, %s, %s)",
	(current_user.id, now, content_id, event.position_seconds, duration, completed),
)
```

```python
# backend/app/api/v1/endpoints/watch_history.py
session.execute(
	"INSERT INTO user_activity (activity_date, event_time, user_id, action, content_id, details) "
	"VALUES (%s, %s, %s, %s, %s, %s)",
	(date_str, now, user_id, action, content_id, details),
)
```

### Dgraph

Dgraph stores graph relationships used for recommendations.

**Why Dgraph for this data**

- Recommendations depend on relationships between users, content, genres, actors, and directors, which is exactly what graph databases are built for.
- Traversing shared interests is cheaper and simpler in a graph than in many relational joins.
- The app needs edges like watched, saved, rated, and shared entities, and Dgraph naturally models those connections.

**Predicates and node types**

- User node fields: `user_id`, `username`, `email`
- Content node fields: `content_id`, `title`
- Shared entity nodes: `Genre.name`, `Actor.name`, `Director.name`
- Edges: `watched`, `rated`, `saved`, `has_genre`, `has_actor`, `has_director`

**Why these predicates/indexes**

- `user_id` and `content_id` are indexed with `exact` so MongoDB IDs can be resolved directly and reliably.
- `username` and `name` use `exact` and `term` because the app needs both exact matches and partial name lookups for graph entities.
- `title` uses `exact`, `term`, and `fulltext` so the graph layer can support content lookup and text-oriented graph queries.
- The edges (`watched`, `rated`, `saved`, `has_genre`, `has_actor`, `has_director`) are reverse-linked because recommendations need to traverse from a person or an entity back to related content.

**Where it is used**

```python
# backend/app/core/dgraph_client.py
async def create_user_node(mongo_id: str, username: str, email: str):
	result = await _mutate({
		"set": [{
			"dgraph.type": "User",
			"user_id": mongo_id,
			"username": username,
			"email": email,
		}]
	})
```

```python
# backend/app/core/dgraph_client.py
async def create_content_node(mongo_id: str, title: str, genres: list[str], cast: list[str], directors: list[str]):
	content_obj = {
		"dgraph.type": "Content",
		"content_id": mongo_id,
		"title": title,
	}
```

```python
# backend/app/api/v1/endpoints/watch_history.py
if event.event_type.value == "play":
	from app.core.dgraph_client import add_watched_edge
	await add_watched_edge(current_user.id, content_id)
```

```python
# backend/app/api/v1/endpoints/recommendations.py
content_ids = await get_recommendations(current_user.id, limit)
```

### ChromaDB

ChromaDB stores the semantic search index for content.

**Why ChromaDB for this data**

- Search queries are natural language, not only exact keywords, so embeddings are a better fit than pure text indexes.
- Similarity search works well for queries like “movies about betrayal” or “shows with a detective vibe”, where the exact words may not appear in the title.
- The content catalog is small enough that local embeddings are practical and avoid external API costs.

**Collection and metadata fields**

- Collection: `content_semantic_index`
- Stored per item: `id`, `document`, `embedding`, `metadata`
- Metadata fields: `title`, `content_type`, `genres`, `cast`, `directors`, `release_date`

**Why these fields**

- `id` is the MongoDB content ID so semantic results can be mapped back to the main document quickly.
- `document` stores the canonical text used to generate the embedding.
- `embedding` is the vector representation that enables similarity search.
- `metadata` keeps the most useful filters next to the vector so the app can still reason about title, type, genres, cast, directors, and release date without reloading everything.
- `title`, `content_type`, `genres`, `cast`, and `directors` are included because they are the same fields used by the UI filters and fallback lexical search.

**Why the index/search approach**

- The search helper stores one vector per content item and queries by nearest neighbors.
- `min_similarity` filters weak matches so the app returns only the most relevant results.
- Limiting the semantic search set keeps the result merge small and predictable, while MongoDB still does the final document fetch.

**Where it is used**

```python
# backend/app/core/semantic_search.py
collection.upsert(
	ids=[content_id],
	documents=[text],
	embeddings=[embedding],
	metadatas=[_build_metadata(content)],
)
```

```python
# backend/app/api/v1/endpoints/content.py
semantic_ids = await semantic_search_content_ids(
	normalized_query,
	limit=chroma_limit,
	min_similarity=min_similarity,
)
```

```python
# backend/app/core/semantic_search.py
result = collection.query(query_embeddings=[embedding], n_results=limit)
```

## Current features

- JWT-based registration and login
- Profile view and logout
- Admin content management
- Content cards with a modern detail modal
- Filtering by type and text query
- Semantic search powered by local embeddings
- Docker-based local development environment

## Architecture

### Backend

- FastAPI 0.115.0
- Motor for MongoDB access
- Cassandra driver for event history
- Pydgraph for graph relationships
- ChromaDB for semantic search
- Python 3.12

### Frontend

- React 19 with TypeScript
- Vite
- Zustand for state
- Axios for API calls

### Infrastructure

- Docker and Docker Compose
- MongoDB 8.0
- Apache Cassandra 5.0
- Dgraph Zero + Alpha
- ChromaDB

## Quick start

```bash
git clone <repository-url>
cd Zeen
cp .env.example .env
docker-compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/api/v1/docs

## Running locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Important environment variables

- `MONGODB_USER`, `MONGODB_PASSWORD` - MongoDB credentials
- `CASSANDRA_HOSTS`, `CASSANDRA_PORT` - Cassandra connection settings
- `DGRAPH_URL` - Dgraph endpoint
- `CHROMADB_URL` - ChromaDB endpoint
- `SECRET_KEY` - JWT signing key
- `VITE_API_URL` - Frontend API base URL

## API endpoints

- `POST /api/v1/auth/register` - Register a user
- `POST /api/v1/auth/login` - Log in and get a token
- `GET /api/v1/auth/me` - Get current user data
- `GET /api/v1/content/` - List content with filters and query search
- `GET /api/v1/content/{content_id}` - Get a single content item
- `POST /api/v1/content/` - Create content as admin
- `PUT /api/v1/content/{content_id}` - Update content as admin
- `DELETE /api/v1/content/{content_id}` - Delete content as admin

## Development notes

- `test_all_endpoints.sh` is the main smoke test script for API routes.
- Keep user-facing copy in English unless the project explicitly needs another language.
- The app uses local embeddings for ChromaDB, so semantic search works without external APIs.

## Project structure

```text
Zeen/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   └── hooks/
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## Troubleshooting

- If containers do not start, check ports 27017, 9042, 8080, 8000, and 5173.
- Cassandra can take longer than the rest of the stack to become healthy.
- If the frontend shows stale data, refresh the browser or restart the frontend container.

## Team

- Diego A. Barraza C. - Lead Developer
- Diego Romo M. - Backend Architecture
- Juan P. Gutierrez G. - Frontend Development

ITESO - Universidad Jesuita de Guadalajara

Zeen - See it. Feel it. Keep it Zeen.