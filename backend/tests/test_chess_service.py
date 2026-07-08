import json
import unittest
from unittest.mock import patch

import chess

from backend.app.services.chess_service import (
    InvalidFenError,
    LichessOpeningService,
    board_from_fen,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


class ChessServiceTest(unittest.TestCase):
    def test_board_from_fen_accepts_url_encoded_fen(self):
        board = board_from_fen(
            "rnbqkbnr%2Fpppppppp%2F8%2F8%2F8%2F8%2FPPPPPPPP%2FRNBQKBNR%20w%20KQkq%20-%200%201"
        )

        self.assertEqual(board.fen(), chess.STARTING_FEN)

    def test_board_from_fen_rejects_invalid_position(self):
        with self.assertRaises(InvalidFenError):
            board_from_fen("8/8/8/8/8/8/8/8 w - - 0 1")

    def test_lichess_moves_are_reduced_to_legal_theory_moves(self):
        service = LichessOpeningService("https://example.test/lichess", 1, "token")
        payload = {
            "opening": {"eco": "B00", "name": "King's Pawn Game"},
            "moves": [
                {"uci": "e2e4", "san": "e4", "white": 10, "draws": 2, "black": 8},
                {"uci": "e7e5", "san": "e5", "white": 1, "draws": 0, "black": 0},
            ],
        }

        with patch(
            "backend.app.services.chess_service.urllib.request.urlopen",
            return_value=FakeResponse(payload),
        ):
            result = service.moves_for_fen(chess.STARTING_FEN)

        self.assertEqual(result["opening"], payload["opening"])
        self.assertEqual(result["moves"], [{"uci": "e2e4", "san": "e4", "white": 10, "draws": 2, "black": 8, "games": 20}])

    def test_lichess_token_is_sent_as_bearer_auth(self):
        service = LichessOpeningService("https://example.test/lichess", 1, "secret-token")

        with patch(
            "backend.app.services.chess_service.urllib.request.urlopen",
            return_value=FakeResponse({"moves": []}),
        ) as urlopen:
            service.moves_for_fen(chess.STARTING_FEN)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer secret-token")


if __name__ == "__main__":
    unittest.main()
