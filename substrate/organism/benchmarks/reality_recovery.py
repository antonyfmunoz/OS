"""Benchmark 1 — Reality Recovery.

50 objective questions about current system state with automated scoring.
Ground truth computed at runtime from actual system state — not hardcoded.
Output: accuracy percentage per category and overall.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)


def _org_state():
    from substrate.state.runtime_paths import runtime_state_dir

    return runtime_state_dir("organism", create=False)


_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class Question:
    """A single objective question with a verifiable answer."""

    question_id: str = ""
    category: str = ""
    question: str = ""
    ground_truth: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "category": self.category,
            "question": self.question,
            "ground_truth": self.ground_truth,
            "source": self.source,
        }


@dataclass
class ScoredAnswer:
    """A scored response to a question."""

    question_id: str = ""
    category: str = ""
    question: str = ""
    ground_truth: str = ""
    agent_answer: str = ""
    score: str = "unknown"  # "correct", "incorrect", "partial", "unknown"
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "category": self.category,
            "question": self.question,
            "ground_truth": self.ground_truth,
            "agent_answer": self.agent_answer,
            "score": self.score,
            "explanation": self.explanation,
        }


@dataclass
class RealityRecoveryResult:
    """Complete benchmark result."""

    total_questions: int = 0
    correct: int = 0
    incorrect: int = 0
    partial: int = 0
    unknown: int = 0
    accuracy: float = 0.0
    accuracy_by_category: dict[str, float] = field(default_factory=dict)
    scored_answers: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_questions": self.total_questions,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "partial": self.partial,
            "unknown": self.unknown,
            "accuracy": self.accuracy,
            "accuracy_by_category": self.accuracy_by_category,
        }


# ---------------------------------------------------------------------------
# Ground truth collectors
# ---------------------------------------------------------------------------


def _run_cmd(cmd: str, timeout: int = 15) -> str:
    """Run a shell command and return stdout, or empty string on failure."""
    result = gated_subprocess_run(
        cmd,
        caller="reality_recovery",
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result is None:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _read_json_file(path: str) -> dict[str, Any]:
    """Read a JSON file, return empty dict on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _count_lines(path: str) -> int:
    """Count lines in a JSONL file."""
    try:
        with open(path) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def _count_files(directory: str, pattern: str = "*.py") -> int:
    """Count files matching pattern in directory."""
    try:
        return len(list(Path(directory).rglob(pattern)))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Question bank generator
# ---------------------------------------------------------------------------


class RealityRecoveryBenchmark:
    """Generates 50 objective questions with runtime-computed ground truth."""

    def __init__(self, repo_root: str = "") -> None:
        self._root = repo_root or _REPO_ROOT

    def generate_questions(self) -> list[Question]:
        """Generate the full question bank with ground truth computed now."""
        questions: list[Question] = []
        questions.extend(self._container_questions())
        questions.extend(self._architecture_questions())
        questions.extend(self._organism_questions())
        questions.extend(self._deployment_questions())
        questions.extend(self._configuration_questions())
        return questions

    def _container_questions(self) -> list[Question]:
        """Questions about Docker container state."""
        qs: list[Question] = []

        # Container names
        container_output = _run_cmd("docker ps --format '{{.Names}}' 2>/dev/null | sort")
        containers = (
            [c.strip() for c in container_output.split("\n") if c.strip()]
            if container_output
            else []
        )

        qs.append(
            Question(
                question_id="container_count",
                category="containers",
                question="How many Docker containers are currently running?",
                ground_truth=str(len(containers)),
                source="docker ps",
            )
        )

        qs.append(
            Question(
                question_id="container_names",
                category="containers",
                question="What are the names of all running Docker containers (comma-separated, alphabetical)?",
                ground_truth=",".join(sorted(containers)),
                source="docker ps --format '{{.Names}}'",
            )
        )

        # Health status per container
        for name in containers[:4]:
            health = _run_cmd(
                f"docker inspect --format='{{{{.State.Health.Status}}}}' {name} 2>/dev/null"
            )
            if not health or health == "<no value>":
                health = "no-healthcheck"
            qs.append(
                Question(
                    question_id=f"container_health_{name}",
                    category="containers",
                    question=f"What is the health status of container '{name}'?",
                    ground_truth=health,
                    source=f"docker inspect {name}",
                )
            )

        # Container uptime
        for name in containers[:2]:
            status = _run_cmd(
                f"docker ps --filter 'name={name}' --format '{{{{.Status}}}}' 2>/dev/null"
            )
            qs.append(
                Question(
                    question_id=f"container_status_{name}",
                    category="containers",
                    question=f"What is the status of container '{name}'?",
                    ground_truth=status,
                    source=f"docker ps --filter 'name={name}'",
                )
            )

        return qs

    def _architecture_questions(self) -> list[Question]:
        """Questions about codebase architecture."""
        qs: list[Question] = []

        substrate_count = _count_files(os.path.join(self._root, "substrate"))
        qs.append(
            Question(
                question_id="substrate_py_count",
                category="architecture",
                question="How many .py files are in the substrate/ directory (recursive)?",
                ground_truth=str(substrate_count),
                source="find substrate/ -name '*.py' | wc -l",
            )
        )

        organism_count = _count_files(os.path.join(self._root, "substrate", "organism"))
        qs.append(
            Question(
                question_id="organism_py_count",
                category="architecture",
                question="How many .py files are in substrate/organism/ (recursive)?",
                ground_truth=str(organism_count),
                source="find substrate/organism/ -name '*.py' | wc -l",
            )
        )

        test_count = _count_files(os.path.join(self._root, "tests"))
        qs.append(
            Question(
                question_id="test_file_count",
                category="architecture",
                question="How many .py test files are in the tests/ directory?",
                ground_truth=str(test_count),
                source="find tests/ -name '*.py' | wc -l",
            )
        )

        adapters_count = _count_files(os.path.join(self._root, "adapters"))
        qs.append(
            Question(
                question_id="adapters_py_count",
                category="architecture",
                question="How many .py files are in the adapters/ directory (recursive)?",
                ground_truth=str(adapters_count),
                source="find adapters/ -name '*.py' | wc -l",
            )
        )

        transports_count = _count_files(os.path.join(self._root, "transports"))
        qs.append(
            Question(
                question_id="transports_py_count",
                category="architecture",
                question="How many .py files are in the transports/ directory (recursive)?",
                ground_truth=str(transports_count),
                source="find transports/ -name '*.py' | wc -l",
            )
        )

        # Route files
        cockpit_routes = _count_files(
            os.path.join(self._root, "transports", "api"), "cockpit_*_routes.py"
        )
        qs.append(
            Question(
                question_id="cockpit_route_files",
                category="architecture",
                question="How many cockpit_*_routes.py files exist in transports/api/?",
                ground_truth=str(cockpit_routes),
                source="find transports/api/ -name 'cockpit_*_routes.py' | wc -l",
            )
        )

        # Pre-commit hooks
        hooks = _count_files(os.path.join(self._root, "scripts"), "check_*.py")
        qs.append(
            Question(
                question_id="gate_script_count",
                category="architecture",
                question="How many check_*.py gate scripts exist in scripts/?",
                ground_truth=str(hooks),
                source="find scripts/ -name 'check_*.py' | wc -l",
            )
        )

        # Canonical types
        types_path = os.path.join(self._root, "substrate", "canonical_types.py")
        if os.path.exists(types_path):
            with open(types_path) as f:
                content = f.read()
            type_count = content.count('":')  # rough count of registered types
            qs.append(
                Question(
                    question_id="canonical_type_count_approx",
                    category="architecture",
                    question="Approximately how many types are registered in substrate/canonical_types.py (within 10)?",
                    ground_truth=str(type_count),
                    source="canonical_types.py entry count",
                )
            )

        # Meta IDE files
        meta_ide_count = _count_files(os.path.join(self._root, "substrate", "meta_ide"))
        qs.append(
            Question(
                question_id="meta_ide_py_count",
                category="architecture",
                question="How many .py files are in substrate/meta_ide/?",
                ground_truth=str(meta_ide_count),
                source="find substrate/meta_ide/ -name '*.py' | wc -l",
            )
        )

        return qs

    def _organism_questions(self) -> list[Question]:
        """Questions about organism runtime state."""
        qs: list[Question] = []

        daemon_path = str(_org_state() / "daemon_state.json")
        daemon_state = _read_json_file(daemon_path)

        qs.append(
            Question(
                question_id="daemon_started",
                category="organism",
                question="Is the organism daemon started (true/false)?",
                ground_truth=str(daemon_state.get("started", False)).lower(),
                source="daemon_state.json",
            )
        )

        qs.append(
            Question(
                question_id="daemon_tick_count",
                category="organism",
                question="How many ticks has the organism daemon completed?",
                ground_truth=str(daemon_state.get("tick_count", 0)),
                source="daemon_state.json",
            )
        )

        qs.append(
            Question(
                question_id="daemon_mode",
                category="organism",
                question="What mode is the organism daemon running in?",
                ground_truth=str(daemon_state.get("mode", "unknown")),
                source="daemon_state.json",
            )
        )

        # Workcell states
        workcells_dir = str(_org_state() / "workcells")
        if os.path.isdir(workcells_dir):
            for wc_name in sorted(os.listdir(workcells_dir)):
                hb_path = os.path.join(workcells_dir, wc_name, "heartbeat.json")
                if os.path.exists(hb_path):
                    hb = _read_json_file(hb_path)
                    qs.append(
                        Question(
                            question_id=f"workcell_{wc_name}_status",
                            category="organism",
                            question=f"What is the status of the '{wc_name}' workcell?",
                            ground_truth=str(hb.get("status", "unknown")),
                            source=f"workcells/{wc_name}/heartbeat.json",
                        )
                    )
                    qs.append(
                        Question(
                            question_id=f"workcell_{wc_name}_messages",
                            category="organism",
                            question=f"How many messages has the '{wc_name}' workcell processed?",
                            ground_truth=str(hb.get("messages_processed", 0)),
                            source=f"workcells/{wc_name}/heartbeat.json",
                        )
                    )

        # Execution journal
        journal_path = str(_org_state() / "execution_journal.jsonl")
        journal_lines = _count_lines(journal_path)
        qs.append(
            Question(
                question_id="execution_journal_entries",
                category="organism",
                question="How many entries are in the execution journal?",
                ground_truth=str(journal_lines),
                source="execution_journal.jsonl line count",
            )
        )

        # Events
        events_path = str(_org_state() / "events.jsonl")
        events_lines = _count_lines(events_path)
        qs.append(
            Question(
                question_id="organism_event_count",
                category="organism",
                question="How many events are in the organism event log?",
                ground_truth=str(events_lines),
                source="events.jsonl line count",
            )
        )

        return qs

    def _deployment_questions(self) -> list[Question]:
        """Questions about deployment state."""
        qs: list[Question] = []

        # Latest commit
        latest_commit = _run_cmd(f"git -C {self._root} log --oneline -1 2>/dev/null")
        if latest_commit:
            commit_hash = latest_commit.split()[0] if latest_commit else ""
            qs.append(
                Question(
                    question_id="latest_commit_hash",
                    category="deployment",
                    question="What is the short hash of the latest commit on the current branch?",
                    ground_truth=commit_hash,
                    source="git log --oneline -1",
                )
            )

        # Current branch
        branch = _run_cmd(f"git -C {self._root} branch --show-current 2>/dev/null")
        qs.append(
            Question(
                question_id="current_branch",
                category="deployment",
                question="What is the current git branch?",
                ground_truth=branch or "unknown",
                source="git branch --show-current",
            )
        )

        # Commits today
        commits_today = _run_cmd(
            f"git -C {self._root} log --oneline --since='midnight' 2>/dev/null | wc -l"
        )
        qs.append(
            Question(
                question_id="commits_today",
                category="deployment",
                question="How many commits were made today?",
                ground_truth=commits_today.strip() if commits_today else "0",
                source="git log --since='midnight' | wc -l",
            )
        )

        # Flyctl status (may not be available)
        fly_status = _run_cmd("flyctl status -a umh-cockpit --json 2>/dev/null", timeout=10)
        if fly_status:
            try:
                fly_data = json.loads(fly_status)
                version = str(fly_data.get("Version", "unknown"))
                qs.append(
                    Question(
                        question_id="cockpit_fly_version",
                        category="deployment",
                        question="What version is the cockpit deployed at on Fly.io?",
                        ground_truth=version,
                        source="flyctl status -a umh-cockpit",
                    )
                )
            except json.JSONDecodeError:
                pass

        return qs

    def _configuration_questions(self) -> list[Question]:
        """Questions about configuration state."""
        qs: list[Question] = []

        # Device registry
        registry_path = os.path.join(self._root, "infra", "device_registry.json")
        if os.path.exists(registry_path):
            try:
                with open(registry_path) as f:
                    devices = json.load(f)
                device_count = (
                    len(devices) if isinstance(devices, list) else len(devices.get("devices", []))
                )
                qs.append(
                    Question(
                        question_id="device_count",
                        category="configuration",
                        question="How many devices are registered in the device registry?",
                        ground_truth=str(device_count),
                        source="infra/device_registry.json",
                    )
                )
            except Exception:
                pass

        # Templates
        templates_path = str(_org_state() / "templates" / "templates.jsonl")
        template_count = _count_lines(templates_path)
        qs.append(
            Question(
                question_id="template_count",
                category="configuration",
                question="How many templates are in the organism template store?",
                ground_truth=str(template_count),
                source="templates/templates.jsonl line count",
            )
        )

        # Messages
        messages_path = str(_org_state() / "messages.jsonl")
        message_count = _count_lines(messages_path)
        qs.append(
            Question(
                question_id="organism_message_count",
                category="configuration",
                question="How many messages are in the organism message store?",
                ground_truth=str(message_count),
                source="messages.jsonl line count",
            )
        )

        # Reports
        reports_path = str(_org_state() / "reports.jsonl")
        report_count = _count_lines(reports_path)
        qs.append(
            Question(
                question_id="organism_report_count",
                category="configuration",
                question="How many reports are in the organism report store?",
                ground_truth=str(report_count),
                source="reports.jsonl line count",
            )
        )

        return qs

    # -- Scoring --

    def score_answers(
        self,
        questions: list[Question],
        answers: dict[str, str],
    ) -> RealityRecoveryResult:
        """Score agent answers against ground truth.

        Args:
            questions: The question bank with ground truth.
            answers: Dict mapping question_id → agent's answer string.

        Returns:
            RealityRecoveryResult with accuracy metrics.
        """
        scored: list[ScoredAnswer] = []
        correct = 0
        incorrect = 0
        partial = 0
        unknown = 0

        for q in questions:
            agent_answer = answers.get(q.question_id, "").strip()
            sa = ScoredAnswer(
                question_id=q.question_id,
                category=q.category,
                question=q.question,
                ground_truth=q.ground_truth,
                agent_answer=agent_answer,
            )

            if not agent_answer:
                sa.score = "unknown"
                sa.explanation = "No answer provided"
                unknown += 1
            elif self._exact_match(q.ground_truth, agent_answer):
                sa.score = "correct"
                sa.explanation = "Exact match"
                correct += 1
            elif self._partial_match(q.ground_truth, agent_answer, q.category):
                sa.score = "partial"
                sa.explanation = "Partial match"
                partial += 1
            else:
                sa.score = "incorrect"
                sa.explanation = f"Expected '{q.ground_truth}', got '{agent_answer}'"
                incorrect += 1

            scored.append(sa)

        total = len(questions)
        accuracy = (correct + 0.5 * partial) / total if total > 0 else 0.0

        # Per-category accuracy
        by_cat: dict[str, list[float]] = {}
        for sa in scored:
            score_val = 1.0 if sa.score == "correct" else (0.5 if sa.score == "partial" else 0.0)
            by_cat.setdefault(sa.category, []).append(score_val)
        accuracy_by_category = {
            cat: round(sum(vals) / len(vals), 4) for cat, vals in by_cat.items()
        }

        return RealityRecoveryResult(
            total_questions=total,
            correct=correct,
            incorrect=incorrect,
            partial=partial,
            unknown=unknown,
            accuracy=round(accuracy, 4),
            accuracy_by_category=accuracy_by_category,
            scored_answers=[sa.to_dict() for sa in scored],
        )

    @staticmethod
    def _exact_match(truth: str, answer: str) -> bool:
        return truth.lower().strip() == answer.lower().strip()

    @staticmethod
    def _partial_match(truth: str, answer: str, category: str) -> bool:
        """Check for partial matches — numeric ranges, substring containment."""
        t = truth.lower().strip()
        a = answer.lower().strip()

        # Numeric range match (within 10%)
        try:
            t_num = float(t)
            a_num = float(a)
            if t_num == 0:
                return a_num == 0
            return abs(t_num - a_num) / max(abs(t_num), 1) <= 0.1
        except (ValueError, TypeError):
            pass

        # Substring containment for longer answers
        if len(t) > 5 and t in a:
            return True
        if len(a) > 5 and a in t:
            return True

        return False
