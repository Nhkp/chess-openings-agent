import time

from backend.app.services.vector_service import (
    VectorSearchSettings,
    build_client,
    load_opening_rows,
    prepare_opening_documents,
    recreate_collection,
)


def main() -> None:
    settings = VectorSearchSettings.from_env()
    documents = prepare_opening_documents(load_opening_rows())

    last_error: Exception | None = None
    for _ in range(30):
        try:
            count = recreate_collection(
                client=build_client(settings.milvus_uri),
                collection_name=settings.collection_name,
                documents=documents,
            )
            break
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    else:
        raise RuntimeError("Milvus did not become ready for opening seed") from last_error

    print(f"Loaded {count} opening notes into {settings.collection_name}")


if __name__ == "__main__":
    main()
