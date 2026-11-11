import sys
import unittest
from unittest.mock import Mock, patch

from backend.app.services.vector_service import (
    EMBEDDING_MODEL,
    VECTOR_DIMENSION,
    EmbeddingService,
    MilvusVectorSearchService,
    VectorSearchError,
    VectorSearchSettings,
    chunk_opening_rows,
    prepare_opening_documents,
    recreate_collection,
)


class VectorServiceTest(unittest.TestCase):
    def setUp(self):
        self.vector = [1.0] + [0.0] * (VECTOR_DIMENSION - 1)
        self.model = Mock()
        self.model.encode.return_value.tolist.return_value = [self.vector]
        self.constructor = Mock(return_value=self.model)
        self.modules = patch.dict(sys.modules, {
            "sentence_transformers": Mock(SentenceTransformer=self.constructor),
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_query_prefix_normalization_and_model_reuse(self):
        embedder = EmbeddingService()
        self.constructor.assert_not_called()
        self.assertEqual(embedder.embed_query("Defense sicilienne"), self.vector)
        embedder.embed_query("Sicilian Defense")
        self.constructor.assert_called_once_with(EMBEDDING_MODEL, device="cpu")
        self.model.encode.assert_called_with(
            ["query: Sicilian Defense"], batch_size=32, normalize_embeddings=True,
            show_progress_bar=False, convert_to_numpy=True,
        )

    def test_documents_preserve_order_and_use_passage_prefix(self):
        other = [0.0, 1.0] + [0.0] * (VECTOR_DIMENSION - 2)
        self.model.encode.return_value.tolist.return_value = [self.vector, other]
        self.assertEqual(EmbeddingService().embed_documents(["premier", "second"]), [self.vector, other])
        self.model.encode.assert_called_once_with(
            ["passage: premier", "passage: second"], batch_size=32,
            normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True,
        )

    def test_empty_documents_and_query_do_not_load_model(self):
        self.assertEqual(EmbeddingService().embed_documents([]), [])
        service = MilvusVectorSearchService("uri", "notes", 3)
        with patch("backend.app.services.vector_service.build_client") as client:
            self.assertEqual(service.search("  "), {"query": "  ", "results": []})
        client.assert_not_called()
        self.constructor.assert_not_called()

    def test_unsupported_model_is_rejected(self):
        with self.assertRaises(VectorSearchError):
            EmbeddingService("semantic-lite-multilingual-hash")

    def test_default_settings_use_e5_collection(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = VectorSearchSettings.from_env()
        self.assertEqual(settings.embedding_model, EMBEDDING_MODEL)
        self.assertEqual(settings.collection_name, "opening_notes_e5")

    def test_model_loading_and_encoding_failures_are_service_errors(self):
        self.constructor.side_effect = OSError("download failed")
        with self.assertRaises(VectorSearchError):
            EmbeddingService().embed_query("sicilienne")
        self.constructor.side_effect = None
        self.model.encode.side_effect = RuntimeError("encode failed")
        with self.assertRaises(VectorSearchError):
            EmbeddingService().embed_query("sicilienne")

    def test_invalid_embeddings_are_rejected(self):
        for output in ([], [[1.0]], [[float("nan")] * VECTOR_DIMENSION],
                       [[float("inf")] * VECTOR_DIMENSION], [[0.0] * VECTOR_DIMENSION]):
            with self.subTest(output_length=len(output)):
                self.model.encode.return_value.tolist.return_value = output
                with self.assertRaises(VectorSearchError):
                    EmbeddingService().embed_query("sicilienne")

    def test_prepare_opening_documents_adds_vectors(self):
        documents = prepare_opening_documents([{
            "id": "sicilian-defense", "opening": "Defense sicilienne", "eco": "B20-B99",
            "text": "1.e4 c5", "source": "test",
        }])
        self.assertEqual(documents[0]["id"], "sicilian-defense")
        self.assertEqual(documents[0]["vector"], self.vector)
        self.assertEqual(documents[0]["embedding_model"], EMBEDDING_MODEL)
        self.assertEqual(self.model.encode.call_args.args[0], ["passage: Defense sicilienne B20-B99 1.e4 c5"])

    def test_chunk_opening_rows_adds_chunk_metadata(self):
        chunks = chunk_opening_rows([{
            "id": "sicilian-defense", "opening": "Defense sicilienne", "eco": "B20-B99",
            "text": " ".join(["plan"] * 60), "source": "wikichess_seed",
        }], max_words=30)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1]["id"], "sicilian-defense-1")
        self.assertEqual(chunks[1]["chunk_index"], 1)

    def test_recreation_checks_vectors_before_touching_collection(self):
        client = Mock()
        for documents in ([], [{"vector": [1.0]}], [{"vector": [float("nan")] * VECTOR_DIMENSION}]):
            with self.subTest(documents=documents):
                with self.assertRaises((VectorSearchError, ValueError)):
                    recreate_collection(client, "notes", documents)
        self.assertEqual(client.mock_calls, [])

    def test_recreation_uses_e5_dimension_and_cosine(self):
        client = Mock()
        documents = [{"id": "one", "vector": self.vector}]
        self.assertEqual(recreate_collection(client, "notes_e5", documents), 1)
        self.assertEqual(client.create_collection.call_args.kwargs["dimension"], 384)
        self.assertEqual(client.create_collection.call_args.kwargs["metric_type"], "COSINE")
        client.insert.assert_called_once_with(collection_name="notes_e5", data=documents)

    def test_vector_search_formats_milvus_hits(self):
        client = Mock()
        client.has_collection.return_value = True
        client.search.return_value = [[{
            "distance": 0.91,
            "entity": {"opening": "Defense sicilienne", "eco": "B20-B99", "text": "1.e4 c5",
                       "source": "test", "embedding_model": EMBEDDING_MODEL},
        }]]
        with patch("backend.app.services.vector_service.build_client", return_value=client):
            result = MilvusVectorSearchService("uri", "notes", 3).search("sicilienne")
        self.assertEqual(result["query"], "sicilienne")
        self.assertEqual(result["results"][0]["opening"], "Defense sicilienne")
        self.assertEqual(result["results"][0]["embedding_model"], EMBEDDING_MODEL)
        self.assertEqual(client.search.call_args.kwargs["data"], [self.vector])
        self.assertEqual(self.model.encode.call_args.args[0], ["query: sicilienne"])

    def test_seed_embedding_failure_and_empty_corpus_never_touch_milvus(self):
        from backend.scripts import load_openings

        for outcome in (VectorSearchError("encoding failed"), []):
            with (
                self.subTest(outcome=outcome),
                patch.object(load_openings, "load_opening_chunks", return_value=[]),
                patch.object(load_openings, "prepare_opening_documents") as prepare,
                patch.object(load_openings, "build_client") as client,
                patch.object(load_openings, "recreate_collection") as recreate,
            ):
                if isinstance(outcome, Exception):
                    prepare.side_effect = outcome
                else:
                    prepare.return_value = outcome
                with self.assertRaises(VectorSearchError):
                    load_openings.main()
                client.assert_not_called()
                recreate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
