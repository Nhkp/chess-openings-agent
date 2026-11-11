from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from pymilvus import MilvusClient
from pymilvus.exceptions import MilvusException


VECTOR_DIMENSION = 384
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "openings.json"
DEFAULT_CHUNKS_PATH = Path(__file__).resolve().parents[1] / "data" / "opening_chunks.json"


class VectorSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorSearchSettings:
    milvus_uri: str
    collection_name: str
    limit: int
    embedding_model: str = EMBEDDING_MODEL

    @classmethod
    def from_env(cls) -> VectorSearchSettings:
        return cls(
            milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
            collection_name=os.getenv("MILVUS_COLLECTION", "opening_notes_e5"),
            limit=int(os.getenv("VECTOR_SEARCH_LIMIT", "3")),
            embedding_model=os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL),
        )


@dataclass(frozen=True)
class EmbeddingService:
    model_name: str = EMBEDDING_MODEL

    def __post_init__(self) -> None:
        if self.model_name != EMBEDDING_MODEL:
            raise VectorSearchError(f"Unsupported EMBEDDING_MODEL: use {EMBEDDING_MODEL}")

    @cached_property
    def model(self) -> Any:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name, device="cpu")

    def embed_query(self, text: str) -> list[float]:
        return self._encode([f"query: {text}"])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([f"passage: {text}" for text in texts])

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self.model.encode(
                texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist()
            if len(vectors) != len(texts):
                raise ValueError("Unexpected embedding count")
            for vector in vectors:
                validate_vector(vector)
            return vectors
        except Exception as exc:
            raise VectorSearchError("Local embedding model unavailable or invalid output") from exc


def validate_vector(vector: list[float]) -> None:
    if len(vector) != VECTOR_DIMENSION or not all(math.isfinite(value) for value in vector):
        raise ValueError("Expected a finite 384-dimensional embedding")
    if not any(vector):
        raise ValueError("Embedding must be nonzero")


def load_opening_rows(path: Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_opening_chunks(path: Path = DEFAULT_CHUNKS_PATH) -> list[dict[str, Any]]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return chunk_opening_rows(load_opening_rows())


def chunk_opening_rows(rows: list[dict[str, Any]], max_words: int = 45) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for row in rows:
        words = row["text"].split()
        for index, start in enumerate(range(0, len(words), max_words)):
            text = " ".join(words[start : start + max_words])
            chunks.append(
                {
                    "id": f"{row['id']}-{index}",
                    "opening": row["opening"],
                    "eco": row["eco"],
                    "source": row["source"],
                    "chunk_index": index,
                    "text": text,
                }
            )
    return chunks


def prepare_opening_documents(
    rows: list[dict[str, Any]],
    embedding_service: EmbeddingService | None = None,
) -> list[dict[str, Any]]:
    embedder = embedding_service or EmbeddingService()
    vectors = embedder.embed_documents([f"{row['opening']} {row['eco']} {row['text']}" for row in rows])
    return [
        {
            "id": row["id"],
            "vector": vector,
            "opening": row["opening"],
            "eco": row["eco"],
            "text": row["text"],
            "source": row["source"],
            "chunk_index": row.get("chunk_index", 0),
            "embedding_model": embedder.model_name,
        }
        for row, vector in zip(rows, vectors, strict=True)
    ]


def build_client(uri: str) -> MilvusClient:
    return MilvusClient(uri=uri)


def recreate_collection(
    client: MilvusClient,
    collection_name: str,
    documents: list[dict[str, Any]],
) -> int:
    if not documents:
        raise VectorSearchError("Cannot recreate collection with an empty corpus")
    for document in documents:
        validate_vector(document["vector"])
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        dimension=VECTOR_DIMENSION,
        primary_field_name="id",
        id_type="string",
        vector_field_name="vector",
        metric_type="COSINE",
        max_length=128,
    )
    client.insert(collection_name=collection_name, data=documents)
    client.load_collection(collection_name=collection_name)
    return len(documents)


@dataclass(frozen=True)
class MilvusVectorSearchService:
    uri: str
    collection_name: str
    limit: int
    embedding_service: EmbeddingService = field(default_factory=EmbeddingService)

    def search(self, opening: str) -> dict[str, Any]:
        query = opening.strip()
        if not query:
            return {"query": opening, "results": []}

        try:
            client = build_client(self.uri)
            if not client.has_collection(self.collection_name):
                raise VectorSearchError("Milvus opening collection is not loaded")
            results = client.search(
                collection_name=self.collection_name,
                data=[self.embedding_service.embed_query(query)],
                limit=self.limit,
                output_fields=["opening", "eco", "text", "source", "chunk_index", "embedding_model"],
            )
        except MilvusException as exc:
            raise VectorSearchError("Milvus vector search unavailable") from exc

        return {
            "query": query,
            "results": [self._format_hit(hit) for hit in results[0]],
        }

    @staticmethod
    def _format_hit(hit: dict[str, Any]) -> dict[str, Any]:
        entity = hit.get("entity", {})
        return {
            "opening": entity.get("opening"),
            "eco": entity.get("eco"),
            "text": entity.get("text"),
            "source": entity.get("source"),
            "chunk_index": entity.get("chunk_index", 0),
            "embedding_model": entity.get("embedding_model"),
            "score": hit.get("distance"),
        }
