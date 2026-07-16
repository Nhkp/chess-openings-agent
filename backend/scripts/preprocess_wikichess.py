import json
import re
from pathlib import Path
from typing import Any

from backend.app.services.vector_service import chunk_opening_rows, load_opening_rows


DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"
SOURCE_DIR = DATA_DIR / "wiki_sources"
OUTPUT_PATH = DATA_DIR / "opening_chunks.json"
SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def load_source_rows(source_dir: Path = SOURCE_DIR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(source_dir.glob("*.json")):
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    return rows or load_opening_rows()


def preprocess_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "text": clean_text(row["text"]),
            "source": row.get("source", "wikichess_seed"),
        }
        for row in rows
    ]


def main() -> None:
    chunks = chunk_opening_rows(preprocess_rows(load_source_rows()))
    OUTPUT_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(chunks)} chunks to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
