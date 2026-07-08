from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import chess
import chess.engine


class InvalidFenError(ValueError):
    pass


class UpstreamServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    lichess_explorer_url: str
    lichess_token: str | None
    lichess_timeout_seconds: float
    stockfish_path: str
    stockfish_depth: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            lichess_explorer_url=os.getenv(
                "LICHESS_EXPLORER_URL", "https://explorer.lichess.ovh/lichess"
            ),
            lichess_token=os.getenv("LICHESS_TOKEN") or None,
            lichess_timeout_seconds=float(os.getenv("LICHESS_TIMEOUT_SECONDS", "5")),
            stockfish_path=os.getenv("STOCKFISH_PATH", "stockfish"),
            stockfish_depth=int(os.getenv("STOCKFISH_DEPTH", "12")),
        )


def board_from_fen(raw_fen: str) -> chess.Board:
    fen = urllib.parse.unquote(raw_fen).replace("+", " ").strip()
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise InvalidFenError("Invalid FEN syntax") from exc

    if not board.is_valid():
        raise InvalidFenError("Invalid chess position")

    return board


@dataclass(frozen=True)
class LichessOpeningService:
    base_url: str
    timeout_seconds: float
    token: str | None = None

    def moves_for_fen(self, fen: str) -> dict[str, Any]:
        board = board_from_fen(fen)
        payload = self._fetch_position(board.fen())
        legal_moves = set(board.legal_moves)

        moves = []
        for move in payload.get("moves", []):
            uci = move.get("uci")
            if not uci:
                continue
            try:
                parsed_move = chess.Move.from_uci(uci)
            except ValueError:
                continue
            if parsed_move not in legal_moves:
                continue

            white = move.get("white", 0)
            draws = move.get("draws", 0)
            black = move.get("black", 0)
            moves.append(
                {
                    "uci": uci,
                    "san": move.get("san"),
                    "white": white,
                    "draws": draws,
                    "black": black,
                    "games": white + draws + black,
                }
            )

        return {"fen": board.fen(), "opening": payload.get("opening"), "moves": moves}

    def _fetch_position(self, fen: str) -> dict[str, Any]:
        query = urllib.parse.urlencode({"variant": "standard", "fen": fen})
        headers = {
            "Accept": "application/json",
            "User-Agent": "projet-13-ffe-poc/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(
            f"{self.base_url}?{query}",
            headers=headers,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise UpstreamServiceError("Lichess opening explorer requires LICHESS_TOKEN") from exc
            if exc.code == 429:
                raise UpstreamServiceError("Lichess rate limit reached") from exc
            raise UpstreamServiceError("Lichess opening explorer failed") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
            raise UpstreamServiceError("Lichess opening explorer unavailable") from exc


@dataclass(frozen=True)
class StockfishEvaluationService:
    stockfish_path: str
    depth: int

    def evaluate_fen(self, fen: str) -> dict[str, Any]:
        board = board_from_fen(fen)

        # ponytail: one engine process per request is enough for the POC; use a
        # managed engine pool if concurrent traffic starts to matter.
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except (FileNotFoundError, PermissionError, chess.engine.EngineError) as exc:
            raise UpstreamServiceError("Stockfish engine unavailable") from exc

        try:
            info = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError) as exc:
            raise UpstreamServiceError("Stockfish analysis failed") from exc
        finally:
            engine.quit()

        score = info["score"].pov(board.turn)
        best_move = None
        if info.get("pv"):
            best_move = info["pv"][0].uci()

        return {
            "fen": board.fen(),
            "depth": self.depth,
            "centipawns": score.score(mate_score=100000),
            "mate": score.mate(),
            "best_move": best_move,
        }
