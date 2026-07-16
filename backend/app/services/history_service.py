from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class HistoryStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistorySettings:
    mongodb_uri: str
    database_name: str
    collection_name: str

    @classmethod
    def from_env(cls) -> HistorySettings:
        return cls(
            mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            database_name=os.getenv("MONGODB_DATABASE", "opening_agent"),
            collection_name=os.getenv("MONGODB_EVENTS_COLLECTION", "agent_events"),
        )


def build_mongo_client(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=1000)


@dataclass
class MongoEventLogger:
    uri: str
    database_name: str
    collection_name: str
    client: Any | None = None
    _client: Any | None = field(default=None, init=False, repr=False)

    @property
    def collection(self) -> Any:
        client = self.client
        if client is None:
            if self._client is None:
                self._client = build_mongo_client(self.uri)
            client = self._client
        return client[self.database_name][self.collection_name]

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        document = {
            "event_type": event_type,
            "payload": payload,
            "created_at": datetime.now(UTC),
        }
        try:
            self.collection.insert_one(document)
        except PyMongoError:
            return

    def recent(self, limit: int) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        try:
            documents = self.collection.find({}, {"_id": 0}).sort("created_at", -1).limit(safe_limit)
            return [self._serialize(document) for document in documents]
        except PyMongoError as exc:
            raise HistoryStoreError("MongoDB history unavailable") from exc

    def health(self) -> str:
        try:
            self.collection.database.client.admin.command("ping")
        except PyMongoError:
            return "unavailable"
        return "ok"

    @staticmethod
    def _serialize(document: dict[str, Any]) -> dict[str, Any]:
        created_at = document.get("created_at")
        if isinstance(created_at, datetime):
            document = {**document, "created_at": created_at.isoformat()}
        return document
