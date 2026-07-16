import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scripts import preprocess_wikichess


class PreprocessWikichessTest(unittest.TestCase):
    def test_preprocess_rows_cleans_text_and_adds_default_source(self):
        rows = preprocess_wikichess.preprocess_rows(
            [
                {
                    "id": "sicilian",
                    "opening": "Defense sicilienne",
                    "eco": "B20",
                    "text": "  1.e4   c5\njeu asymetrique  ",
                }
            ]
        )

        self.assertEqual(rows[0]["text"], "1.e4 c5 jeu asymetrique")
        self.assertEqual(rows[0]["source"], "wikichess_seed")

    def test_load_source_rows_reads_json_sources_before_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            (source_dir / "source.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "french",
                            "opening": "Defense francaise",
                            "eco": "C00",
                            "text": "1.e4 e6",
                            "source": "wikichess",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            rows = preprocess_wikichess.load_source_rows(source_dir)

        self.assertEqual(rows[0]["opening"], "Defense francaise")

    def test_load_source_rows_falls_back_to_openings_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(preprocess_wikichess, "load_opening_rows", return_value=[{"id": "seed"}]):
                rows = preprocess_wikichess.load_source_rows(Path(directory))

        self.assertEqual(rows, [{"id": "seed"}])


if __name__ == "__main__":
    unittest.main()
