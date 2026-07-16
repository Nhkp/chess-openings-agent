from fastapi import FastAPI, HTTPException

from backend.app.services.chess_service import (
    InvalidFenError,
    LichessOpeningService,
    Settings,
    StockfishEvaluationService,
    UpstreamServiceError,
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


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/moves")
@app.get("/api/v1/moves/{fen:path}")
def moves(fen: str) -> dict:
    try:
        return opening_service.moves_for_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/evaluate")
@app.get("/api/v1/evaluate/{fen:path}")
def evaluate(fen: str) -> dict:
    try:
        return evaluation_service.evaluate_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/vector-search")
@app.get("/vector-search")
def vector_search(opening: str) -> dict:
    try:
        return vector_search_service.search(opening)
    except VectorSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/videos")
@app.get("/api/v1/videos/{opening}")
@app.get("/videos")
@app.get("/videos/{opening}")
def videos(opening: str) -> dict:
    try:
        return video_workflow.run(opening)
    except VideoSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
