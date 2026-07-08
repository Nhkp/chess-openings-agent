from __future__ import annotations

import html
import os
from dataclasses import dataclass
from typing import Any, TypedDict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langgraph.graph import END, START, StateGraph


class VideoSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoSearchSettings:
    youtube_api_key: str | None
    max_results: int
    relevance_language: str

    @classmethod
    def from_env(cls) -> VideoSearchSettings:
        return cls(
            youtube_api_key=os.getenv("YOUTUBE_API_KEY") or None,
            max_results=int(os.getenv("YOUTUBE_MAX_RESULTS", "5")),
            relevance_language=os.getenv("YOUTUBE_RELEVANCE_LANGUAGE", "fr"),
        )


@dataclass(frozen=True)
class YouTubeVideoSearchService:
    api_key: str | None
    max_results: int
    relevance_language: str

    def search(self, opening: str) -> list[dict[str, Any]]:
        if not self.api_key:
            raise VideoSearchError("YouTube search requires YOUTUBE_API_KEY")

        query = self._query_for(opening)
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
            response = (
                youtube.search()
                .list(
                    part="snippet",
                    q=query,
                    type="video",
                    maxResults=self.max_results,
                    safeSearch="strict",
                    videoEmbeddable="true",
                    relevanceLanguage=self.relevance_language,
                )
                .execute()
            )
        except HttpError as exc:
            if getattr(exc.resp, "status", None) == 403:
                raise VideoSearchError("YouTube quota or access denied") from exc
            raise VideoSearchError("YouTube search failed") from exc
        except Exception as exc:
            raise VideoSearchError("YouTube search unavailable") from exc

        return [
            video
            for item in response.get("items", [])
            if (video := self._format_video(item, opening)) is not None
        ]

    @staticmethod
    def _query_for(opening: str) -> str:
        return f"{opening.strip()} chess opening tutorial explanation"

    @staticmethod
    def _format_video(item: dict[str, Any], opening: str) -> dict[str, Any] | None:
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id or not snippet:
            return None

        title = html.unescape(snippet.get("title", ""))
        description = html.unescape(snippet.get("description", ""))
        if not is_relevant(opening, title, description):
            return None

        thumbnails = snippet.get("thumbnails", {})
        thumbnail = thumbnails.get("medium") or thumbnails.get("default") or {}
        return {
            "video_id": video_id,
            "title": title,
            "description": description,
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail_url": thumbnail.get("url"),
        }


def is_relevant(opening: str, title: str, description: str) -> bool:
    haystack = f"{title} {description}".lower()
    opening_terms = [term for term in opening.lower().split() if len(term) > 2]
    chess_terms = ("chess", "echecs", "échecs", "opening", "ouverture")
    return any(term in haystack for term in opening_terms) or any(term in haystack for term in chess_terms)


class VideoWorkflowState(TypedDict):
    opening: str
    videos: list[dict[str, Any]]


@dataclass(frozen=True)
class OpeningVideoWorkflow:
    video_service: YouTubeVideoSearchService

    def __post_init__(self) -> None:
        graph = StateGraph(VideoWorkflowState)
        graph.add_node("search_videos", self._search_videos)
        graph.add_edge(START, "search_videos")
        graph.add_edge("search_videos", END)
        object.__setattr__(self, "_graph", graph.compile())

    def run(self, opening: str) -> dict[str, Any]:
        state = self._graph.invoke({"opening": opening, "videos": []})
        return {
            "opening": state["opening"],
            "videos": state["videos"],
            "count": len(state["videos"]),
        }

    def _search_videos(self, state: VideoWorkflowState) -> VideoWorkflowState:
        return {
            "opening": state["opening"],
            "videos": self.video_service.search(state["opening"]),
        }
