"""Real CPU model check, run explicitly: uv run python -m backend.scripts.check_embeddings."""
import math

from backend.app.services.vector_service import (
    VECTOR_DIMENSION,
    EmbeddingService,
    load_opening_chunks,
    prepare_opening_documents,
)


def main() -> None:
    embedder = EmbeddingService()
    documents = prepare_opening_documents(load_opening_chunks(), embedder)
    assert documents, "Opening corpus is empty"
    for document in documents:
        assert len(document["vector"]) == VECTOR_DIMENSION
        assert math.isclose(sum(value * value for value in document["vector"]), 1.0, abs_tol=1e-5)
    for query, expected in (
        ("défense sicilienne", "Defense sicilienne"),
        ("Sicilian Defense", "Defense sicilienne"),
        ("ouverture espagnole", "Partie espagnole"),
    ):
        vector = embedder.embed_query(query)
        assert math.isclose(sum(value * value for value in vector), 1.0, abs_tol=1e-5)
        ranked = sorted(documents, key=lambda doc: sum(a * b for a, b in zip(vector, doc["vector"], strict=True)), reverse=True)
        openings = [doc["opening"] for doc in ranked[:3]]
        assert expected in openings, f"{query}: expected {expected} in {openings}"
        print(f"{query}: {openings}")
    print("E5 CPU check passed: normalized 384-dimensional vectors and multilingual retrieval")


if __name__ == "__main__":
    main()
