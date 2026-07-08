import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from backend.app.services.chess_service import InvalidFenError, UpstreamServiceError
from backend.app.services.vector_service import VectorSearchError
from backend.app.services.video_service import VideoSearchError


class MainRouteTest(unittest.TestCase):
    def test_healthcheck(self):
        from backend.app.main import healthcheck

        self.assertEqual(healthcheck(), {"status": "ok"})

    def test_moves_maps_invalid_fen_to_422(self):
        from backend.app import main

        with patch.object(main, "opening_service", Mock(moves_for_fen=Mock(side_effect=InvalidFenError("bad fen")))):
            with self.assertRaises(HTTPException) as raised:
                main.moves("bad")

        self.assertEqual(raised.exception.status_code, 422)

    def test_moves_maps_upstream_error_to_503(self):
        from backend.app import main

        with patch.object(main, "opening_service", Mock(moves_for_fen=Mock(side_effect=UpstreamServiceError("lichess")))):
            with self.assertRaises(HTTPException) as raised:
                main.moves("fen")

        self.assertEqual(raised.exception.status_code, 503)

    def test_evaluate_returns_service_payload(self):
        from backend.app import main

        payload = {"best_move": "e2e4"}
        with patch.object(main, "evaluation_service", Mock(evaluate_fen=Mock(return_value=payload))):
            self.assertEqual(main.evaluate("fen"), payload)

    def test_vector_search_maps_service_error(self):
        from backend.app import main

        with patch.object(main, "vector_search_service", Mock(search=Mock(side_effect=VectorSearchError("milvus")))):
            with self.assertRaises(HTTPException) as raised:
                main.vector_search("sicilienne")

        self.assertEqual(raised.exception.status_code, 503)

    def test_videos_returns_workflow_payload(self):
        from backend.app import main

        payload = {"videos": []}
        with patch.object(main, "video_workflow", Mock(run=Mock(return_value=payload))):
            self.assertEqual(main.videos("sicilienne"), payload)

    def test_videos_maps_workflow_error(self):
        from backend.app import main

        with patch.object(main, "video_workflow", Mock(run=Mock(side_effect=VideoSearchError("youtube")))):
            with self.assertRaises(HTTPException) as raised:
                main.videos("sicilienne")

        self.assertEqual(raised.exception.status_code, 503)


class SeederTest(unittest.TestCase):
    def test_loader_retries_until_milvus_is_ready(self):
        from backend.scripts import load_openings

        with (
            patch.object(load_openings.VectorSearchSettings, "from_env", return_value=Mock(milvus_uri="uri", collection_name="notes")),
            patch.object(load_openings, "load_opening_rows", return_value=[]),
            patch.object(load_openings, "prepare_opening_documents", return_value=[{"id": "one"}]),
            patch.object(load_openings, "build_client", return_value=Mock()),
            patch.object(load_openings, "recreate_collection", side_effect=[RuntimeError("wait"), 1]) as recreate,
            patch.object(load_openings.time, "sleep") as sleep,
            patch("builtins.print") as print_,
        ):
            load_openings.main()

        self.assertEqual(recreate.call_count, 2)
        sleep.assert_called_once_with(2)
        print_.assert_called_once_with("Loaded 1 opening notes into notes")


if __name__ == "__main__":
    unittest.main()
