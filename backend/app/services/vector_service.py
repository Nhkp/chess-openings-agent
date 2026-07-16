from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymilvus import MilvusClient
from pymilvus.exceptions import MilvusException


VECTOR_DIMENSION = 64
TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]+")
DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "openings.json"
DEFAULT_CHUNKS_PATH = Path(__file__).resolve().parents[1] / "data" / "opening_chunks.json"


class VectorSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorSearchSettings:
    milvus_uri: str
    collection_name: str
    limit: int
    embedding_model: str = "semantic-lite-multilingual-hash"

    @classmethod
    def from_env(cls) -> VectorSearchSettings:
        return cls(
            milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
            collection_name=os.getenv("MILVUS_COLLECTION", "opening_notes"),
            limit=int(os.getenv("VECTOR_SEARCH_LIMIT", "3")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "semantic-lite-multilingual-hash"),
        )


@dataclass(frozen=True)
class EmbeddingService:
    model_name: str = "semantic-lite-multilingual-hash"

    def embed(self, text: str) -> list[float]:
        return embed_text(text)


def embed_text(text: str) -> list[float]:
    # ponytail: hashed lexical embeddings keep the POC light; replace this with
    # sentence-transformers when semantic quality matters more than image size.
    vector = [0.0] * VECTOR_DIMENSION
    for token in TOKEN_RE.findall(text.lower()):
        digest = hashlib.blake2b(token.encode(), digest_size=4).digest()
        index = int.from_bytes(digest, "big") % VECTOR_DIMENSION
        vector[index] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


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
    return [
        {
            "id": row["id"],
            "vector": embedder.embed(f"{row['opening']} {row['eco']} {row['text']}"),
            "opening": row["opening"],
            "eco": row["eco"],
            "text": row["text"],
            "source": row["source"],
            "chunk_index": row.get("chunk_index", 0),
            "embedding_model": embedder.model_name,
        }
        for row in rows
    ]


def build_client(uri: str) -> MilvusClient:
    return MilvusClient(uri=uri)


def recreate_collection(
    client: MilvusClient,
    collection_name: str,
    documents: list[dict[str, Any]],
) -> int:
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
                data=[embed_text(query)],
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
