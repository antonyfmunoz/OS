"""External benchmark adapter layer — industry-standard benchmarks through UMH.

Campaign 23B. Tier 1: External Benchmarks.
Adapters for SWE-bench, Terminal-Bench, WebArena, GAIA, BrowseComp.
Initial implementation uses synthetic test mode; full dataset integration
is a follow-up step. The adapters establish the measurement contract.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkTask:
    task_id: str = ""
    benchmark_name: str = ""
    description: str = ""
    repo_path: str = ""
    expected_outcome: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    task_id: str = ""
    benchmark_name: str = ""
    success: bool = False
    partial_score: float = 0.0
    duration_seconds: float = 0.0
    tokens_consumed: int = 0
    cost_usd: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExternalBenchmarkResult:
    benchmark_name: str = ""
    tasks_attempted: int = 0
    tasks_resolved: int = 0
    resolution_rate: float = 0.0
    avg_duration: float = 0.0
    avg_tokens: float = 0.0
    avg_cost: float = 0.0
    partial_score_avg: float = 0.0
    results: list[TaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["results"] = [r.to_dict() for r in self.results]
        return d


class ExternalBenchmarkAdapter:
    """Base class for industry-standard benchmark adapters."""

    benchmark_name: str = ""

    def __init__(self, test_mode: bool = True) -> None:
        self._test_mode = test_mode

    def load_tasks(self, dataset_path: str = "") -> list[BenchmarkTask]:
        if self._test_mode:
            return self._synthetic_tasks()
        return self._load_from_dataset(dataset_path)

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        raise NotImplementedError

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        raise NotImplementedError

    def run_task(self, task: BenchmarkTask) -> TaskResult:
        if self._test_mode:
            return self._simulate_task(task)
        return self._execute_task(task)

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        raise NotImplementedError

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        raise NotImplementedError

    def score_results(self, results: list[TaskResult]) -> ExternalBenchmarkResult:
        if not results:
            return ExternalBenchmarkResult(benchmark_name=self.benchmark_name)
        resolved = sum(1 for r in results if r.success)
        count = len(results)
        return ExternalBenchmarkResult(
            benchmark_name=self.benchmark_name,
            tasks_attempted=count,
            tasks_resolved=resolved,
            resolution_rate=resolved / count,
            avg_duration=sum(r.duration_seconds for r in results) / count,
            avg_tokens=sum(r.tokens_consumed for r in results) / count,
            avg_cost=sum(r.cost_usd for r in results) / count,
            partial_score_avg=sum(r.partial_score for r in results) / count,
            results=list(results),
        )

    def run_all(self, dataset_path: str = "") -> ExternalBenchmarkResult:
        tasks = self.load_tasks(dataset_path)
        results = [self.run_task(t) for t in tasks]
        return self.score_results(results)


class SWEBenchAdapter(ExternalBenchmarkAdapter):
    """SWE-bench: GitHub issue resolution (Python repos)."""

    benchmark_name = "swe_bench"

    _SYNTHETIC = [
        ("django__django-16379", "Fix QuerySet.bulk_create() ignoring update_fields", True, 0.95, 45.0, 12000, 0.18),
        ("sympy__sympy-24152", "Fix simplify() returning wrong result for trig", True, 0.80, 62.0, 18000, 0.27),
        ("scikit-learn__sklearn-25570", "Fix HistGradientBoosting NaN handling", False, 0.30, 90.0, 25000, 0.38),
        ("matplotlib__matplotlib-25311", "Fix colorbar tick label formatting", True, 1.0, 30.0, 8000, 0.12),
        ("requests__requests-6028", "Fix session cookie jar merge", False, 0.20, 55.0, 15000, 0.23),
    ]

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id=tid,
                benchmark_name=self.benchmark_name,
                description=desc,
                repo_path=tid.rsplit("-", 1)[0].replace("__", "/"),
                expected_outcome="patch matches ground truth",
            )
            for tid, desc, *_ in self._SYNTHETIC
        ]

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        for tid, _, success, partial, dur, tok, cost in self._SYNTHETIC:
            if tid == task.task_id:
                return TaskResult(
                    task_id=tid,
                    benchmark_name=self.benchmark_name,
                    success=success,
                    partial_score=partial,
                    duration_seconds=dur,
                    tokens_consumed=tok,
                    cost_usd=cost,
                )
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        logger.info("SWE-bench dataset loading not yet implemented: %s", path)
        return []

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        logger.info("SWE-bench live execution not yet implemented: %s", task.task_id)
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)


class TerminalBenchAdapter(ExternalBenchmarkAdapter):
    """Terminal-Bench: CLI/terminal task completion."""

    benchmark_name = "terminal_bench"

    _SYNTHETIC = [
        ("tb-git-rebase", "Rebase feature branch onto main resolving conflicts", True, 0.90, 15.0, 3000, 0.05),
        ("tb-npm-audit", "Run npm audit and fix all high-severity vulnerabilities", True, 1.0, 20.0, 4000, 0.06),
        ("tb-docker-compose", "Write docker-compose.yml for 3-service stack", True, 0.85, 25.0, 5000, 0.08),
        ("tb-find-replace", "Find and replace across 50 files matching pattern", False, 0.40, 10.0, 2000, 0.03),
        ("tb-systemd-service", "Create and enable systemd service unit file", True, 0.95, 12.0, 2500, 0.04),
    ]

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id=tid,
                benchmark_name=self.benchmark_name,
                description=desc,
            )
            for tid, desc, *_ in self._SYNTHETIC
        ]

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        for tid, _, success, partial, dur, tok, cost in self._SYNTHETIC:
            if tid == task.task_id:
                return TaskResult(
                    task_id=tid,
                    benchmark_name=self.benchmark_name,
                    success=success,
                    partial_score=partial,
                    duration_seconds=dur,
                    tokens_consumed=tok,
                    cost_usd=cost,
                )
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        logger.info("Terminal-Bench dataset loading not yet implemented: %s", path)
        return []

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        logger.info("Terminal-Bench live execution not yet implemented: %s", task.task_id)
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)


class WebArenaAdapter(ExternalBenchmarkAdapter):
    """WebArena: browser-based task completion."""

    benchmark_name = "webarena"

    _SYNTHETIC = [
        ("wa-shop-search", "Search for product and add to cart", True, 0.85, 30.0, 8000, 0.12),
        ("wa-forum-post", "Navigate forum and create new discussion post", False, 0.35, 45.0, 12000, 0.18),
        ("wa-gitlab-issue", "Create GitLab issue with labels and assignee", True, 0.90, 25.0, 6000, 0.09),
        ("wa-map-directions", "Get directions between two locations on map", True, 0.75, 35.0, 9000, 0.14),
        ("wa-cms-edit", "Edit CMS page content and publish", False, 0.25, 50.0, 14000, 0.21),
    ]

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id=tid,
                benchmark_name=self.benchmark_name,
                description=desc,
            )
            for tid, desc, *_ in self._SYNTHETIC
        ]

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        for tid, _, success, partial, dur, tok, cost in self._SYNTHETIC:
            if tid == task.task_id:
                return TaskResult(
                    task_id=tid,
                    benchmark_name=self.benchmark_name,
                    success=success,
                    partial_score=partial,
                    duration_seconds=dur,
                    tokens_consumed=tok,
                    cost_usd=cost,
                )
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        logger.info("WebArena dataset loading not yet implemented: %s", path)
        return []

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        logger.info("WebArena live execution not yet implemented: %s", task.task_id)
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)


class GAIAAdapter(ExternalBenchmarkAdapter):
    """GAIA: real-world multi-step task completion."""

    benchmark_name = "gaia"

    _SYNTHETIC = [
        ("gaia-research", "Find the founding year of three companies and compute average", True, 1.0, 60.0, 20000, 0.30),
        ("gaia-code-debug", "Debug Python script and fix all failing tests", True, 0.80, 75.0, 22000, 0.33),
        ("gaia-data-analysis", "Analyze CSV dataset and produce summary statistics", False, 0.45, 90.0, 28000, 0.42),
        ("gaia-api-integration", "Write script that calls two APIs and merges results", True, 0.70, 80.0, 24000, 0.36),
        ("gaia-document-qa", "Extract specific information from a 50-page PDF", False, 0.30, 100.0, 30000, 0.45),
    ]

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id=tid,
                benchmark_name=self.benchmark_name,
                description=desc,
            )
            for tid, desc, *_ in self._SYNTHETIC
        ]

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        for tid, _, success, partial, dur, tok, cost in self._SYNTHETIC:
            if tid == task.task_id:
                return TaskResult(
                    task_id=tid,
                    benchmark_name=self.benchmark_name,
                    success=success,
                    partial_score=partial,
                    duration_seconds=dur,
                    tokens_consumed=tok,
                    cost_usd=cost,
                )
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        logger.info("GAIA dataset loading not yet implemented: %s", path)
        return []

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        logger.info("GAIA live execution not yet implemented: %s", task.task_id)
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)


class BrowseCompAdapter(ExternalBenchmarkAdapter):
    """BrowseComp: information retrieval tasks."""

    benchmark_name = "browsecomp"

    _SYNTHETIC = [
        ("bc-factcheck", "Verify claim about historical event using multiple sources", True, 0.90, 40.0, 10000, 0.15),
        ("bc-price-compare", "Find lowest price for specific product across 5 stores", False, 0.35, 55.0, 16000, 0.24),
        ("bc-news-synthesis", "Summarize coverage of event from 3 news sources", True, 0.80, 45.0, 13000, 0.20),
        ("bc-academic-search", "Find papers citing specific study published after 2023", True, 0.70, 50.0, 14000, 0.21),
        ("bc-legal-lookup", "Find relevant statute for specific legal question", False, 0.25, 65.0, 18000, 0.27),
    ]

    def _synthetic_tasks(self) -> list[BenchmarkTask]:
        return [
            BenchmarkTask(
                task_id=tid,
                benchmark_name=self.benchmark_name,
                description=desc,
            )
            for tid, desc, *_ in self._SYNTHETIC
        ]

    def _simulate_task(self, task: BenchmarkTask) -> TaskResult:
        for tid, _, success, partial, dur, tok, cost in self._SYNTHETIC:
            if tid == task.task_id:
                return TaskResult(
                    task_id=tid,
                    benchmark_name=self.benchmark_name,
                    success=success,
                    partial_score=partial,
                    duration_seconds=dur,
                    tokens_consumed=tok,
                    cost_usd=cost,
                )
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)

    def _load_from_dataset(self, path: str) -> list[BenchmarkTask]:
        logger.info("BrowseComp dataset loading not yet implemented: %s", path)
        return []

    def _execute_task(self, task: BenchmarkTask) -> TaskResult:
        logger.info("BrowseComp live execution not yet implemented: %s", task.task_id)
        return TaskResult(task_id=task.task_id, benchmark_name=self.benchmark_name)


ADAPTER_REGISTRY: dict[str, type[ExternalBenchmarkAdapter]] = {
    "swe_bench": SWEBenchAdapter,
    "terminal_bench": TerminalBenchAdapter,
    "webarena": WebArenaAdapter,
    "gaia": GAIAAdapter,
    "browsecomp": BrowseCompAdapter,
}


def get_adapter(benchmark_name: str, test_mode: bool = True) -> ExternalBenchmarkAdapter | None:
    cls = ADAPTER_REGISTRY.get(benchmark_name)
    if cls is None:
        logger.warning("Unknown benchmark adapter: %s", benchmark_name)
        return None
    return cls(test_mode=test_mode)
