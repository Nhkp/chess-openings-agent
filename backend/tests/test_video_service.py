import unittest
from unittest.mock import Mock, patch

from backend.app.services.video_service import (
    OpeningVideoWorkflow,
    VideoSearchError,
    YouTubeVideoSearchService,
    is_relevant,
)


class VideoServiceTest(unittest.TestCase):
    def test_missing_youtube_key_fails_loudly(self):
        with self.assertRaises(VideoSearchError):
            YouTubeVideoSearchService(None, 5, "fr").search("Defense sicilienne")

    def test_relevance_accepts_opening_or_chess_terms(self):
        self.assertTrue(is_relevant("Defense sicilienne", "Sicilienne Najdorf", ""))
        self.assertTrue(is_relevant("Defense sicilienne", "Chess opening lesson", ""))
        self.assertFalse(is_relevant("Defense sicilienne", "Cooking lesson", ""))

    def test_youtube_search_formats_video_metadata(self):
        youtube = Mock()
        youtube.search.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "Defense sicilienne expliquee",
                        "description": "Une ouverture dynamique.",
                        "channelTitle": "Chess Coach",
                        "publishedAt": "2026-01-02T00:00:00Z",
                        "thumbnails": {"medium": {"url": "https://img.example/thumb.jpg"}},
                    },
                },
                {"id": {"videoId": "skip"}, "snippet": {"title": "Cooking lesson"}},
            ]
        }

        with patch("backend.app.services.video_service.build", return_value=youtube) as build:
            videos = YouTubeVideoSearchService("key", 5, "fr").search("Defense sicilienne")

        build.assert_called_once_with("youtube", "v3", developerKey="key", cache_discovery=False)
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(videos[0]["embed_url"], "https://www.youtube.com/embed/abc123")

    def test_video_workflow_returns_search_results(self):
        service = Mock()
        service.search.return_value = [{"title": "Defense sicilienne"}]

        result = OpeningVideoWorkflow(service).run("Defense sicilienne")

        service.search.assert_called_once_with("Defense sicilienne")
        self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
