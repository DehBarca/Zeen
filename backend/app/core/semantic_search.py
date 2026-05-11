from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Mapping, Sequence

from sentence_transformers import SentenceTransformer

from app.core.database import get_chromadb_client


CONTENT_COLLECTION_NAME = "content_semantic_index"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _as_text_list(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values.strip()
    if isinstance(values, Sequence):
        return ", ".join(
            normalized
            for normalized in (_normalize_value(value) for value in values)
            if normalized
        )
    return _normalize_value(values)


def build_content_text(content: Mapping[str, Any]) -> str:
    content_type = content.get("content_type")
    if hasattr(content_type, "value"):
        content_type = content_type.value

    parts = [
        _normalize_value(content.get("title")),
        _normalize_value(content.get("description")),
        f"Type: {_normalize_value(content_type)}" if content_type else "",
        f"Release date: {_normalize_value(content.get('release_date'))}" if content.get("release_date") else "",
        f"Genres: {_as_text_list(content.get('genres'))}" if content.get("genres") else "",
        f"Cast: {_as_text_list(content.get('cast'))}" if content.get("cast") else "",
        f"Directors: {_as_text_list(content.get('directors'))}" if content.get("directors") else "",
    ]
    return " | ".join(part for part in parts if part)


def _build_metadata(content: Mapping[str, Any]) -> dict[str, Any]:
    content_type = content.get("content_type")
    if hasattr(content_type, "value"):
        content_type = content_type.value

    metadata: dict[str, Any] = {
        "title": _normalize_value(content.get("title")),
        "content_type": _normalize_value(content_type),
        "genres": _as_text_list(content.get("genres")),
        "cast": _as_text_list(content.get("cast")),
        "directors": _as_text_list(content.get("directors")),
    }
    release_date = content.get("release_date")
    if release_date is not None:
        metadata["release_date"] = _normalize_value(release_date)
    return {key: value for key, value in metadata.items() if value}


async def _get_collection():
    client = await get_chromadb_client()
    if client is None:
        return None
    return client.get_or_create_collection(name=CONTENT_COLLECTION_NAME)


def _embed_text_sync(text: str) -> list[float]:
    embedding = get_embedding_model().encode([text], normalize_embeddings=True)
    return embedding[0].tolist()


async def _embed_text(text: str) -> list[float]:
    return await asyncio.to_thread(_embed_text_sync, text)


async def upsert_content_embedding(content_id: str, content: Mapping[str, Any]) -> None:
    collection = await _get_collection()
    if collection is None:
        return

    text = build_content_text(content)
    if not text:
        return

    embedding = await _embed_text(text)
    collection.upsert(
        ids=[content_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[_build_metadata(content)],
    )


async def delete_content_embedding(content_id: str) -> None:
    collection = await _get_collection()
    if collection is None:
        return
    collection.delete(ids=[content_id])


async def semantic_search_content_ids(query: str, limit: int = 20) -> list[str]:
    collection = await _get_collection()
    if collection is None:
        return []

    normalized_query = query.strip()
    if not normalized_query:
        return []

    embedding = await _embed_text(normalized_query)
    result = collection.query(query_embeddings=[embedding], n_results=limit)
    ids = result.get("ids") or []
    if not ids:
        return []
    return [item for item in ids[0] if item]