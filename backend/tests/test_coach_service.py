import unittest
from unittest.mock import Mock

import chess

from backend.app.services.chess_service import UpstreamServiceError
from backend.app.services.coach_service import ChessCoachWorkflow
from backend.app.services.video_service import VideoSearchError


class CoachServiceTest(unittest.TestCase):
    def test_coach_workflow_selects_tools_and_returns_recommendation(self):
        opening_service = Mock()
        opening_service.moves_for_fen.return_value = {
            "opening": {"name": "Defense sicilienne"},
            "moves": [{"uci": "c7c5", "san": "c5"}],
        }
        evaluation_service = Mock()
        evaluation_service.evaluate_fen.return_value = {
            "fen": chess.STARTING_FEN,
            "depth": 12,
            "centipawns": 20,
            "mate": None,
            "best_move": "e2e4",
        }
        vector_service = Mock()
        vector_service.search.return_value = {
            "results": [{"text": "La Defense sicilienne commence par 1.e4 c5."}]
        }
        video_workflow = Mock()
        video_workflow.run.return_value = {"videos": [{"title": "Sicilian"}]}

        result = ChessCoachWorkflow(opening_service, evaluation_service, vector_service, video_workflow).run(
            chess.STARTING_FEN,
            "Defense sicilienne",
        )

        self.assertIn("stockfish", result["selected_tools"])
        self.assertIn("lichess", result["selected_tools"])
        self.assertIn("milvus", result["selected_tools"])
        self.assertIn("youtube", result["selected_tools"])
        self.assertEqual(result["evaluation"]["best_move"], "e2e4")
        self.assertEqual(result["theory_moves"][0]["san"], "c5")
        self.assertIn("Stockfish propose e2e4", result["recommendation"])

    def test_coach_workflow_keeps_partial_results_when_optional_tools_fail(self):
        opening_service = Mock()
        opening_service.moves_for_fen.side_effect = UpstreamServiceError("lichess")
        evaluation_service = Mock()
        evaluation_service.evaluate_fen.return_value = {
            "fen": chess.STARTING_FEN,
            "depth": 12,
            "centipawns": 20,
            "mate": None,
            "best_move": "e2e4",
        }
        vector_service = Mock()
        vector_service.search.return_value = {"results": []}
        video_workflow = Mock()
        video_workflow.run.side_effect = VideoSearchError("youtube")

        result = ChessCoachWorkflow(opening_service, evaluation_service, vector_service, video_workflow).run(
            chess.STARTING_FEN,
            "Defense sicilienne",
        )

        self.assertEqual(result["evaluation"]["best_move"], "e2e4")
        self.assertGreaterEqual(len(result["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
