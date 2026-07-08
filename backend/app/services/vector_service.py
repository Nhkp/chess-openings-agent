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


class VectorSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorSearchSettings:
    milvus_uri: str
    collection_name: str
    limit: int

    @classmethod
    def from_env(cls) -> VectorSearchSettings:
        return cls(
            milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
            collection_name=os.getenv("MILVUS_COLLECTION", "opening_notes"),
            limit=int(os.getenv("VECTOR_SEARCH_LIMIT", "3")),
        )


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


def prepare_opening_documents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "vector": embed_text(f"{row['opening']} {row['eco']} {row['text']}"),
            "opening": row["opening"],
            "eco": row["eco"],
            "text": row["text"],
            "source": row["source"],
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
                output_fields=["opening", "eco", "text", "source"],
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
            "score": hit.get("distance"),
        }
