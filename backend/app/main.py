from fastapi import FastAPI, HTTPException

from backend.app.services.chess_service import (
    InvalidFenError,
    LichessOpeningService,
    Settings,
    StockfishEvaluationService,
    UpstreamServiceError,
)
from backend.app.services.history_service import (
    HistorySettings,
    HistoryStoreError,
    MongoEventLogger,
)
from backend.app.services.vector_service import (
    MilvusVectorSearchService,
    VectorSearchError,
    VectorSearchSettings,
)
from backend.app.services.video_service import (
    OpeningVideoWorkflow,
    VideoSearchError,
    VideoSearchSettings,
    YouTubeVideoSearchService,
)


app = FastAPI(title="FFE Chess Openings Agent", version="0.1.0")
settings = Settings.from_env()
opening_service = LichessOpeningService(
    base_url=settings.lichess_explorer_url,
    timeout_seconds=settings.lichess_timeout_seconds,
    token=settings.lichess_token,
)
evaluation_service = StockfishEvaluationService(
    stockfish_path=settings.stockfish_path,
    depth=settings.stockfish_depth,
)
vector_settings = VectorSearchSettings.from_env()
vector_search_service = MilvusVectorSearchService(
    uri=vector_settings.milvus_uri,
    collection_name=vector_settings.collection_name,
    limit=vector_settings.limit,
)
video_settings = VideoSearchSettings.from_env()
video_workflow = OpeningVideoWorkflow(
    YouTubeVideoSearchService(
        api_key=video_settings.youtube_api_key,
        max_results=video_settings.max_results,
        relevance_language=video_settings.relevance_language,
    )
)
history_settings = HistorySettings.from_env()
history_logger = MongoEventLogger(
    uri=history_settings.mongodb_uri,
    database_name=history_settings.database_name,
    collection_name=history_settings.collection_name,
)


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "mongodb": history_logger.health()}


@app.get("/api/v1/moves")
@app.get("/api/v1/moves/{fen:path}")
def moves(fen: str) -> dict:
    try:
        result = opening_service.moves_for_fen(fen)
        history_logger.log("moves", {"fen": result.get("fen"), "move_count": len(result.get("moves", []))})
        return result
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/evaluate")
@app.get("/api/v1/evaluate/{fen:path}")
def evaluate(fen: str) -> dict:
    try:
        result = evaluation_service.evaluate_fen(fen)
        history_logger.log(
            "evaluate",
            {
                "fen": result.get("fen"),
                "depth": result.get("depth"),
                "best_move": result.get("best_move"),
                "centipawns": result.get("centipawns"),
                "mate": result.get("mate"),
            },
        )
        return result
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/vector-search")
@app.get("/vector-search")
def vector_search(opening: str) -> dict:
    try:
        result = vector_search_service.search(opening)
        history_logger.log("vector_search", {"opening": result["query"], "result_count": len(result["results"])})
        return result
    except VectorSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/videos")
@app.get("/api/v1/videos/{opening}")
@app.get("/videos")
@app.get("/videos/{opening}")
def videos(opening: str) -> dict:
    try:
        result = video_workflow.run(opening)
        history_logger.log("videos", {"opening": result.get("opening"), "video_count": result.get("count", 0)})
        return result
    except VideoSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/history")
def history(limit: int = 20) -> dict:
    try:
        events = history_logger.recent(limit)
    except HistoryStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"events": events, "count": len(events)}
