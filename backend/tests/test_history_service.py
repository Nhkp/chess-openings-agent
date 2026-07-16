import unittest
from datetime import UTC, datetime

from pymongo.errors import PyMongoError

from backend.app.services.history_service import HistoryStoreError, MongoEventLogger


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.sort_args = None
        self.limit_value = None

    def sort(self, *args):
        self.sort_args = args
        return self

    def limit(self, value):
        self.limit_value = value
        return self.documents[:value]


class FakeCollection:
    def __init__(self, documents=None, fail=False):
        self.documents = documents or []
        self.fail = fail
        self.inserted = []

    def insert_one(self, document):
        if self.fail:
            raise PyMongoError("down")
        self.inserted.append(document)

    def find(self, *_):
        if self.fail:
            raise PyMongoError("down")
        return FakeCursor(self.documents)


class FakeDatabase:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, _):
        return self.collection


class FakeClient:
    def __init__(self, collection):
        self.database = FakeDatabase(collection)

    def __getitem__(self, _):
        return self.database


class HistoryServiceTest(unittest.TestCase):
    def test_event_logger_writes_documents(self):
        collection = FakeCollection()
        logger = MongoEventLogger("mongodb://test", "db", "events", FakeClient(collection))

        logger.log("moves", {"fen": "start"})

        self.assertEqual(collection.inserted[0]["event_type"], "moves")
        self.assertEqual(collection.inserted[0]["payload"], {"fen": "start"})
        self.assertIsInstance(collection.inserted[0]["created_at"], datetime)

    def test_event_logger_ignores_write_failures(self):
        logger = MongoEventLogger("mongodb://test", "db", "events", FakeClient(FakeCollection(fail=True)))

        logger.log("moves", {"fen": "start"})

    def test_recent_serializes_documents_and_clamps_limit(self):
        created_at = datetime(2026, 7, 16, tzinfo=UTC)
        collection = FakeCollection([{"event_type": "moves", "created_at": created_at}])
        logger = MongoEventLogger("mongodb://test", "db", "events", FakeClient(collection))

        self.assertEqual(
            logger.recent(200),
            [{"event_type": "moves", "created_at": "2026-07-16T00:00:00+00:00"}],
        )

    def test_recent_raises_when_mongodb_is_unavailable(self):
        logger = MongoEventLogger("mongodb://test", "db", "events", FakeClient(FakeCollection(fail=True)))

        with self.assertRaises(HistoryStoreError):
            logger.recent(20)


if __name__ == "__main__":
    unittest.main()
