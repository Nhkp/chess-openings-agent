import unittest
from unittest.mock import Mock, patch

from backend.app.services.vector_service import (
    VECTOR_DIMENSION,
    MilvusVectorSearchService,
    embed_text,
    prepare_opening_documents,
)


class VectorServiceTest(unittest.TestCase):
    def test_embed_text_returns_stable_normalized_vector(self):
        first = embed_text("Defense sicilienne")
        second = embed_text("Defense sicilienne")

        self.assertEqual(first, second)
        self.assertEqual(len(first), VECTOR_DIMENSION)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_prepare_opening_documents_adds_vectors(self):
        documents = prepare_opening_documents(
            [
                {
                    "id": "sicilian-defense",
                    "opening": "Defense sicilienne",
                    "eco": "B20-B99",
                    "text": "1.e4 c5",
                    "source": "test",
                }
            ]
        )

        self.assertEqual(documents[0]["id"], "sicilian-defense")
        self.assertEqual(len(documents[0]["vector"]), VECTOR_DIMENSION)

    def test_vector_search_formats_milvus_hits(self):
        client = Mock()
        client.has_collection.return_value = True
        client.search.return_value = [
            [
                {
                    "distance": 0.91,
                    "entity": {
                        "opening": "Defense sicilienne",
                        "eco": "B20-B99",
                        "text": "1.e4 c5",
                        "source": "test",
                    },
                }
            ]
        ]

        with patch("backend.app.services.vector_service.build_client", return_value=client):
            result = MilvusVectorSearchService("http://milvus:19530", "opening_notes", 3).search("sicilienne")

        self.assertEqual(result["query"], "sicilienne")
        self.assertEqual(result["results"][0]["opening"], "Defense sicilienne")


if __name__ == "__main__":
    unittest.main()
