"""Audit — Context Capacity.

Campaign 23B — Category C Audit.
Tier 3: organism audit (inspects system state, generates a report — no task execution).

Measures how much of the codebase the organism can hold in working context:
graph coverage, summary coverage, cross-file dependency edges, and history depth.
All metrics deterministic. No LLM calls.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextCapacityReport:
    """Result of a context-capacity audit."""

    repo_file_count: int = 0
    graph_node_count: int = 0
    graph_coverage_pct: float = 0.0
    summary_coverage_pct: float = 0.0
    cross_file_edges: int = 0
    history_depth: int = 0
    overall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextCapacityAudit:
    """Audits the organism's pre-computed context layers (graph + summaries)."""

    def __init__(self, test_mode: bool = False) -> None:
        self._test_mode = test_mode

    def run(
        self,
        repo_root: str = "",
        graph_data: dict[str, Any] | None = None,
        summary_data: dict[str, Any] | None = None,
    ) -> ContextCapacityReport:
        """Run the context-capacity audit.

        When ``graph_data`` / ``summary_data`` are supplied (or ``test_mode`` is
        set), those structures are used directly. Otherwise the audit reads the
        graph and summary artifacts from the filesystem under ``repo_root``.
        """
        if not self._test_mode and graph_data is None and summary_data is None:
            graph_data, summary_data, repo_files = self._load_from_filesystem(repo_root)
        else:
            graph_data = graph_data or {}
            summary_data = summary_data or {}
            repo_files = None

        repo_file_count = self._repo_file_count(graph_data, summary_data, repo_files)
        graph_node_count = self._node_count(graph_data)
        cross_file_edges = self._edge_count(graph_data)
        history_depth = self._history_depth(graph_data)
        summarized = self._summarized_count(summary_data)

        graph_coverage = self._ratio(graph_node_count, repo_file_count)
        summary_coverage = self._ratio(summarized, repo_file_count)

        coverage_metrics = [graph_coverage, summary_coverage]
        overall = round(sum(coverage_metrics) / len(coverage_metrics), 4) if coverage_metrics else 0.0

        return ContextCapacityReport(
            repo_file_count=repo_file_count,
            graph_node_count=graph_node_count,
            graph_coverage_pct=graph_coverage,
            summary_coverage_pct=summary_coverage,
            cross_file_edges=cross_file_edges,
            history_depth=history_depth,
            overall_score=overall,
        )

    # ------------------------------------------------------------------
    # Metric extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(min(1.0, numerator / denominator), 4)

    @staticmethod
    def _repo_file_count(
        graph_data: dict[str, Any],
        summary_data: dict[str, Any],
        repo_files: int | None,
    ) -> int:
        if repo_files is not None:
            return repo_files
        if "repo_file_count" in graph_data:
            return int(graph_data["repo_file_count"])
        if "repo_file_count" in summary_data:
            return int(summary_data["repo_file_count"])
        # Fall back to the largest known population.
        nodes = ContextCapacityAudit._node_count(graph_data)
        summarized = ContextCapacityAudit._summarized_count(summary_data)
        return max(nodes, summarized)

    @staticmethod
    def _node_count(graph_data: dict[str, Any]) -> int:
        if "node_count" in graph_data:
            return int(graph_data["node_count"])
        nodes = graph_data.get("nodes")
        if isinstance(nodes, (list, dict)):
            return len(nodes)
        return 0

    @staticmethod
    def _edge_count(graph_data: dict[str, Any]) -> int:
        if "edge_count" in graph_data:
            return int(graph_data["edge_count"])
        edges = graph_data.get("edges")
        if isinstance(edges, (list, dict)):
            return len(edges)
        return 0

    @staticmethod
    def _history_depth(graph_data: dict[str, Any]) -> int:
        if "history_depth" in graph_data:
            return int(graph_data["history_depth"])
        if "commits" in graph_data:
            commits = graph_data["commits"]
            if isinstance(commits, (list, dict)):
                return len(commits)
            return int(commits)
        return 0

    @staticmethod
    def _summarized_count(summary_data: dict[str, Any]) -> int:
        if "summarized_count" in summary_data:
            return int(summary_data["summarized_count"])
        summaries = summary_data.get("summaries", summary_data)
        if isinstance(summaries, dict):
            # Exclude bookkeeping keys.
            return sum(1 for k in summaries if k not in {"repo_file_count", "summarized_count"})
        if isinstance(summaries, list):
            return len(summaries)
        return 0

    # ------------------------------------------------------------------
    # Filesystem loading
    # ------------------------------------------------------------------

    def _load_from_filesystem(
        self, repo_root: str
    ) -> tuple[dict[str, Any], dict[str, Any], int | None]:
        root = repo_root or os.environ.get("UMH_ROOT", "/opt/OS")
        graph_data: dict[str, Any] = {}
        summary_data: dict[str, Any] = {}

        graph_path = os.path.join(root, "data", "codebase_graph.json")
        summary_path = os.path.join(root, "data", "node_summaries.json")

        try:
            if os.path.exists(graph_path):
                with open(graph_path, encoding="utf-8") as fh:
                    graph_data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.debug("context_capacity: failed to load graph: %s", exc)

        try:
            if os.path.exists(summary_path):
                with open(summary_path, encoding="utf-8") as fh:
                    summary_data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.debug("context_capacity: failed to load summaries: %s", exc)

        return graph_data, summary_data, None
