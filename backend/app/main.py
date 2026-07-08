from fastapi import FastAPI, HTTPException

from backend.app.services.chess_service import (
    InvalidFenError,
    LichessOpeningService,
    Settings,
    StockfishEvaluationService,
    UpstreamServiceError,
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


@app.get("/api/v1/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/moves/{fen:path}")
def moves(fen: str) -> dict:
    try:
        return opening_service.moves_for_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/evaluate/{fen:path}")
def evaluate(fen: str) -> dict:
    try:
        return evaluation_service.evaluate_fen(fen)
    except InvalidFenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
