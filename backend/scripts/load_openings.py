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
    count = recreate_collection(
        client=build_client(settings.milvus_uri),
        collection_name=settings.collection_name,
        documents=documents,
    )
    print(f"Loaded {count} opening notes into {settings.collection_name}")


if __name__ == "__main__":
    main()
