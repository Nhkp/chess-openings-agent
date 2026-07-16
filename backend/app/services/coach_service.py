from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.services.chess_service import (
    InvalidFenError,
    LichessOpeningService,
    StockfishEvaluationService,
    UpstreamServiceError,
    board_from_fen,
)
from backend.app.services.vector_service import MilvusVectorSearchService, VectorSearchError
from backend.app.services.video_service import OpeningVideoWorkflow, VideoSearchError


class CoachWorkflowState(TypedDict):
    fen: str
    opening_query: str
    selected_tools: list[str]
    legal_moves: list[str]
    normalized_fen: NotRequired[str]
    opening_name: NotRequired[str]
    evaluation: NotRequired[dict[str, Any] | None]
    theory_moves: NotRequired[list[dict[str, Any]]]
    context: NotRequired[list[dict[str, Any]]]
    videos: NotRequired[list[dict[str, Any]]]
    warnings: NotRequired[list[str]]
    recommendation: NotRequired[str]


@dataclass(frozen=True)
class ChessCoachWorkflow:
    opening_service: LichessOpeningService
    evaluation_service: StockfishEvaluationService
    vector_search_service: MilvusVectorSearchService
    video_workflow: OpeningVideoWorkflow

    def __post_init__(self) -> None:
        graph = StateGraph(CoachWorkflowState)
        graph.add_node("inspect_position", self._inspect_position)
        graph.add_node("select_tools", self._select_tools)
        graph.add_node("load_theory", self._load_theory)
        graph.add_node("evaluate_position", self._evaluate_position)
        graph.add_node("load_context", self._load_context)
        graph.add_node("load_videos", self._load_videos)
        graph.add_node("synthesize", self._synthesize)
        graph.add_edge(START, "inspect_position")
        graph.add_edge("inspect_position", "select_tools")
        graph.add_edge("select_tools", "load_theory")
        graph.add_edge("load_theory", "evaluate_position")
        graph.add_edge("evaluate_position", "load_context")
        graph.add_edge("load_context", "load_videos")
        graph.add_edge("load_videos", "synthesize")
        graph.add_edge("synthesize", END)
        object.__setattr__(self, "_graph", graph.compile())

    def run(self, fen: str, opening: str = "") -> dict[str, Any]:
        state = self._graph.invoke(
            {
                "fen": fen,
                "opening_query": opening.strip(),
                "selected_tools": [],
                "legal_moves": [],
                "warnings": [],
                "evaluation": None,
                "theory_moves": [],
                "context": [],
                "videos": [],
            }
        )
        return {
            "fen": state["normalized_fen"],
            "opening": state.get("opening_name") or state["opening_query"],
            "selected_tools": state["selected_tools"],
            "legal_moves": state["legal_moves"],
            "evaluation": state.get("evaluation"),
            "theory_moves": state.get("theory_moves", []),
            "context": state.get("context", []),
            "videos": state.get("videos", []),
            "warnings": state.get("warnings", []),
            "recommendation": state.get("recommendation", ""),
        }

    def _inspect_position(self, state: CoachWorkflowState) -> CoachWorkflowState:
        board = board_from_fen(state["fen"])
        return {
            **state,
            "normalized_fen": board.fen(),
            "legal_moves": [move.uci() for move in board.legal_moves],
        }

    def _select_tools(self, state: CoachWorkflowState) -> CoachWorkflowState:
        selected = ["stockfish", "lichess"]
        if state["opening_query"]:
            selected.extend(["milvus", "youtube"])
        return {**state, "selected_tools": selected}

    def _load_theory(self, state: CoachWorkflowState) -> CoachWorkflowState:
        try:
            result = self.opening_service.moves_for_fen(state["normalized_fen"])
        except (InvalidFenError, UpstreamServiceError) as exc:
            return self._warn(state, f"Lichess indisponible: {exc}")

        opening = state["opening_query"]
        if not opening and result.get("opening"):
            opening = result["opening"].get("name") or ""
        selected_tools = state["selected_tools"]
        if opening and "milvus" not in selected_tools:
            selected_tools = [*selected_tools, "milvus", "youtube"]
        return {
            **state,
            "opening_query": opening,
            "opening_name": opening,
            "theory_moves": result.get("moves", []),
            "selected_tools": selected_tools,
        }

    def _evaluate_position(self, state: CoachWorkflowState) -> CoachWorkflowState:
        try:
            return {**state, "evaluation": self.evaluation_service.evaluate_fen(state["normalized_fen"])}
        except (InvalidFenError, UpstreamServiceError) as exc:
            return self._warn(state, f"Stockfish indisponible: {exc}")

    def _load_context(self, state: CoachWorkflowState) -> CoachWorkflowState:
        if "milvus" not in state["selected_tools"] or not state["opening_query"]:
            return state
        try:
            result = self.vector_search_service.search(state["opening_query"])
        except VectorSearchError as exc:
            return self._warn(state, f"Milvus indisponible: {exc}")
        return {**state, "context": result.get("results", [])}

    def _load_videos(self, state: CoachWorkflowState) -> CoachWorkflowState:
        if "youtube" not in state["selected_tools"] or not state["opening_query"]:
            return state
        try:
            result = self.video_workflow.run(state["opening_query"])
        except VideoSearchError as exc:
            return self._warn(state, f"YouTube indisponible: {exc}")
        return {**state, "videos": result.get("videos", [])}

    def _synthesize(self, state: CoachWorkflowState) -> CoachWorkflowState:
        evaluation = state.get("evaluation") or {}
        best_move = evaluation.get("best_move")
        theory = state.get("theory_moves", [])
        context = state.get("context", [])
        first_theory = None
        if theory:
            first_theory = theory[0].get("san") or theory[0].get("uci")
        first_context = context[0].get("text") if context else ""

        parts = ["L'agent a analyse la position avec " + ", ".join(state["selected_tools"]) + "."]
        if best_move:
            parts.append(f"Stockfish propose {best_move} comme meilleur coup.")
        if first_theory:
            parts.append(f"La base Lichess indique {first_theory} comme coup theorique prioritaire.")
        if first_context:
            parts.append(first_context)
        if not best_move and not first_theory:
            parts.append("Aucune recommandation forcee: developpez les pieces et securisez le roi.")

        return {**state, "recommendation": " ".join(parts)}

    @staticmethod
    def _warn(state: CoachWorkflowState, warning: str) -> CoachWorkflowState:
        return {**state, "warnings": [*state.get("warnings", []), warning]}
