"""C29 Harness Superiority — data model, task registry, result store.

Certification benchmark comparing Legacy workflow vs UMH workflow.
All types are deterministic dataclasses. Zero LLM calls anywhere.

The question under test: has UMH crossed the trust threshold where building
through UMH produces better outcomes than building outside UMH?
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BenchmarkCategory(str, Enum):
    BUG_FIX = "BUG_FIX"
    FEATURE = "FEATURE"
    REFACTOR = "REFACTOR"
    DEPLOY = "DEPLOY"
    RECOVERY = "RECOVERY"


class EvidenceClass(str, Enum):
    A_PRODUCTION = "A_PRODUCTION"
    B_CONTROLLED = "B_CONTROLLED"
    C_SYNTHETIC = "C_SYNTHETIC"


EVIDENCE_WEIGHTS = {
    EvidenceClass.A_PRODUCTION: 1.0,
    EvidenceClass.B_CONTROLLED: 0.625,
    EvidenceClass.C_SYNTHETIC: 0.125,
}


class EvidenceConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class Complexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Track(str, Enum):
    A_LEGACY = "A_LEGACY"
    B_UMH = "B_UMH"


class MVPVerdictLevel(str, Enum):
    NOT_READY = "NOT_READY"
    PARTIALLY_TRUSTED = "PARTIALLY_TRUSTED"
    PRIMARY_WORKSTATION = "PRIMARY_WORKSTATION"
    CERTIFIED_DAILY_DRIVER = "CERTIFIED_DAILY_DRIVER"


# ---------------------------------------------------------------------------
# Core task type
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkTask:
    task_id: str
    category: BenchmarkCategory
    project: str
    title: str
    description: str
    complexity: Complexity
    expected_deliverables: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "category": self.category.value,
            "project": self.project,
            "title": self.title,
            "description": self.description,
            "complexity": self.complexity.value,
            "expected_deliverables": list(self.expected_deliverables),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkTask":
        return cls(
            task_id=data["task_id"],
            category=BenchmarkCategory(data["category"]),
            project=data["project"],
            title=data["title"],
            description=data["description"],
            complexity=Complexity(data["complexity"]),
            expected_deliverables=list(data.get("expected_deliverables", [])),
            created_at=data.get("created_at", ""),
        )


# ---------------------------------------------------------------------------
# Existing sub-result types
# ---------------------------------------------------------------------------


@dataclass
class EscapeEvent:
    timestamp: str
    tool: str
    reason: str
    could_cockpit_handle: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EscapeEvent":
        return cls(
            timestamp=data["timestamp"],
            tool=data["tool"],
            reason=data["reason"],
            could_cockpit_handle=bool(data["could_cockpit_handle"]),
        )


@dataclass
class ContinuityResult:
    interruption_duration_seconds: float
    context_preserved: bool
    resume_time_seconds: float
    decisions_recalled: int
    decisions_total: int
    intent_preserved: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ContinuityResult":
        return cls(
            interruption_duration_seconds=float(data["interruption_duration_seconds"]),
            context_preserved=bool(data["context_preserved"]),
            resume_time_seconds=float(data["resume_time_seconds"]),
            decisions_recalled=int(data["decisions_recalled"]),
            decisions_total=int(data["decisions_total"]),
            intent_preserved=bool(data["intent_preserved"]),
        )


@dataclass
class GovernanceResult:
    approvals_required: int
    approvals_enforced: int
    proof_generated: bool
    verification_enforced: bool
    false_history_tested: bool
    false_history_blocked: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GovernanceResult":
        return cls(
            approvals_required=int(data["approvals_required"]),
            approvals_enforced=int(data["approvals_enforced"]),
            proof_generated=bool(data["proof_generated"]),
            verification_enforced=bool(data["verification_enforced"]),
            false_history_tested=bool(data["false_history_tested"]),
            false_history_blocked=bool(data["false_history_blocked"]),
        )


@dataclass
class AwarenessSnapshot:
    repos_visible: bool = False
    branches_visible: bool = False
    builds_visible: bool = False
    deployments_visible: bool = False
    containers_visible: bool = False
    previews_visible: bool = False
    sessions_visible: bool = False
    executions_visible: bool = False
    agents_visible: bool = False
    device_mesh_visible: bool = False
    awareness_score: float = 0.0

    def __post_init__(self) -> None:
        count = sum(
            1
            for v in (
                self.repos_visible,
                self.branches_visible,
                self.builds_visible,
                self.deployments_visible,
                self.containers_visible,
                self.previews_visible,
                self.sessions_visible,
                self.executions_visible,
                self.agents_visible,
                self.device_mesh_visible,
            )
            if v
        )
        self.awareness_score = count / 10

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AwarenessSnapshot":
        return cls(
            repos_visible=bool(data.get("repos_visible", False)),
            branches_visible=bool(data.get("branches_visible", False)),
            builds_visible=bool(data.get("builds_visible", False)),
            deployments_visible=bool(data.get("deployments_visible", False)),
            containers_visible=bool(data.get("containers_visible", False)),
            previews_visible=bool(data.get("previews_visible", False)),
            sessions_visible=bool(data.get("sessions_visible", False)),
            executions_visible=bool(data.get("executions_visible", False)),
            agents_visible=bool(data.get("agents_visible", False)),
            device_mesh_visible=bool(data.get("device_mesh_visible", False)),
        )


@dataclass
class BrowserEvidence:
    screenshots: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    console_log: list[str] = field(default_factory=list)
    network_errors: list[str] = field(default_factory=list)
    network_traces: list[str] = field(default_factory=list)
    execution_traces: list[str] = field(default_factory=list)
    proof_package_id: str = ""
    verification_result: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BrowserEvidence":
        return cls(
            screenshots=list(data.get("screenshots", [])),
            console_errors=list(data.get("console_errors", [])),
            console_log=list(data.get("console_log", [])),
            network_errors=list(data.get("network_errors", [])),
            network_traces=list(data.get("network_traces", [])),
            execution_traces=list(data.get("execution_traces", [])),
            proof_package_id=data.get("proof_package_id", ""),
            verification_result=data.get("verification_result", ""),
        )


@dataclass
class VoiceResult:
    commands_attempted: int
    commands_recognized: int
    intents_correct: int
    routes_correct: int
    recovery_after_failure: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceResult":
        return cls(
            commands_attempted=int(data["commands_attempted"]),
            commands_recognized=int(data["commands_recognized"]),
            intents_correct=int(data["intents_correct"]),
            routes_correct=int(data["routes_correct"]),
            recovery_after_failure=bool(data["recovery_after_failure"]),
        )


@dataclass
class PreviewResult:
    preview_loaded: bool
    mobile_viewport: bool
    tablet_viewport: bool
    desktop_viewport: bool
    expand_collapse: bool
    health_visible: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PreviewResult":
        return cls(
            preview_loaded=bool(data["preview_loaded"]),
            mobile_viewport=bool(data["mobile_viewport"]),
            tablet_viewport=bool(data["tablet_viewport"]),
            desktop_viewport=bool(data["desktop_viewport"]),
            expand_collapse=bool(data["expand_collapse"]),
            health_visible=bool(data["health_visible"]),
        )


# ---------------------------------------------------------------------------
# Gap result types
# ---------------------------------------------------------------------------


@dataclass
class CognitiveLoadResult:
    reconstruction_steps: int
    clarification_questions: int
    context_searches: int
    panel_hops: int
    memory_recovery_actions: int
    cognitive_load_score: float | None = None

    def __post_init__(self) -> None:
        if self.cognitive_load_score is None:
            total = (
                self.reconstruction_steps
                + self.clarification_questions
                + self.context_searches
                + self.panel_hops
                + self.memory_recovery_actions
            )
            self.cognitive_load_score = 1.0 - min(total / 20.0, 1.0)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CognitiveLoadResult":
        return cls(
            reconstruction_steps=int(data["reconstruction_steps"]),
            clarification_questions=int(data["clarification_questions"]),
            context_searches=int(data["context_searches"]),
            panel_hops=int(data["panel_hops"]),
            memory_recovery_actions=int(data["memory_recovery_actions"]),
            cognitive_load_score=data.get("cognitive_load_score"),
        )


@dataclass
class InterruptionResult:
    interruption_type: str
    interruption_from: str
    interruption_to: str
    away_duration_seconds: float
    resume_time_seconds: float
    context_accuracy: float
    decisions_recalled: int
    decisions_total: int
    work_recovery_complete: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InterruptionResult":
        return cls(
            interruption_type=data["interruption_type"],
            interruption_from=data["interruption_from"],
            interruption_to=data["interruption_to"],
            away_duration_seconds=float(data["away_duration_seconds"]),
            resume_time_seconds=float(data["resume_time_seconds"]),
            context_accuracy=float(data["context_accuracy"]),
            decisions_recalled=int(data["decisions_recalled"]),
            decisions_total=int(data["decisions_total"]),
            work_recovery_complete=bool(data["work_recovery_complete"]),
        )


@dataclass
class RealityDriftResult:
    drift_type: str
    drift_present: bool
    drift_detected: bool
    detection_time_seconds: float
    false_positive: bool
    detection_method: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RealityDriftResult":
        return cls(
            drift_type=data["drift_type"],
            drift_present=bool(data["drift_present"]),
            drift_detected=bool(data["drift_detected"]),
            detection_time_seconds=float(data["detection_time_seconds"]),
            false_positive=bool(data["false_positive"]),
            detection_method=data["detection_method"],
        )


@dataclass
class OperatorTrustResult:
    confidence_before: int
    confidence_after: int
    verification_needed: bool
    manual_double_checks: int
    trust_delta: int | None = None

    def __post_init__(self) -> None:
        if self.trust_delta is None:
            self.trust_delta = self.confidence_after - self.confidence_before

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OperatorTrustResult":
        return cls(
            confidence_before=int(data["confidence_before"]),
            confidence_after=int(data["confidence_after"]),
            verification_needed=bool(data["verification_needed"]),
            manual_double_checks=int(data["manual_double_checks"]),
            trust_delta=data.get("trust_delta"),
        )


@dataclass
class MetaIDEResult:
    workspace_aware: bool = False
    repo_aware: bool = False
    branch_aware: bool = False
    execution_aware: bool = False
    preview_aware: bool = False
    proof_aware: bool = False
    continuity_aware: bool = False
    meta_ide_score: float = 0.0

    def __post_init__(self) -> None:
        count = sum(
            1
            for v in (
                self.workspace_aware,
                self.repo_aware,
                self.branch_aware,
                self.execution_aware,
                self.preview_aware,
                self.proof_aware,
                self.continuity_aware,
            )
            if v
        )
        self.meta_ide_score = count / 7

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MetaIDEResult":
        return cls(
            workspace_aware=bool(data.get("workspace_aware", False)),
            repo_aware=bool(data.get("repo_aware", False)),
            branch_aware=bool(data.get("branch_aware", False)),
            execution_aware=bool(data.get("execution_aware", False)),
            preview_aware=bool(data.get("preview_aware", False)),
            proof_aware=bool(data.get("proof_aware", False)),
            continuity_aware=bool(data.get("continuity_aware", False)),
        )


@dataclass
class ResourceCost:
    tokens_used: int
    compute_seconds: float
    operator_minutes: float
    clicks: int
    panel_changes: int
    commands_issued: int
    cost_per_deliverable: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceCost":
        return cls(
            tokens_used=int(data["tokens_used"]),
            compute_seconds=float(data["compute_seconds"]),
            operator_minutes=float(data["operator_minutes"]),
            clicks=int(data["clicks"]),
            panel_changes=int(data["panel_changes"]),
            commands_issued=int(data["commands_issued"]),
            cost_per_deliverable=float(data["cost_per_deliverable"]),
        )


@dataclass
class WorkdayCoverage:
    coding: bool = False
    debugging: bool = False
    review: bool = False
    deployment: bool = False
    planning: bool = False
    continuity: bool = False
    documentation: bool = False
    approvals: bool = False
    knowledge_retrieval: bool = False
    runtime_inspection: bool = False
    coverage_score: float = 0.0

    def __post_init__(self) -> None:
        count = sum(
            1
            for v in (
                self.coding,
                self.debugging,
                self.review,
                self.deployment,
                self.planning,
                self.continuity,
                self.documentation,
                self.approvals,
                self.knowledge_retrieval,
                self.runtime_inspection,
            )
            if v
        )
        self.coverage_score = count / 10

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkdayCoverage":
        return cls(
            coding=bool(data.get("coding", False)),
            debugging=bool(data.get("debugging", False)),
            review=bool(data.get("review", False)),
            deployment=bool(data.get("deployment", False)),
            planning=bool(data.get("planning", False)),
            continuity=bool(data.get("continuity", False)),
            documentation=bool(data.get("documentation", False)),
            approvals=bool(data.get("approvals", False)),
            knowledge_retrieval=bool(data.get("knowledge_retrieval", False)),
            runtime_inspection=bool(data.get("runtime_inspection", False)),
        )


@dataclass
class LongitudinalCheckpoint:
    checkpoint_number: int
    runs_completed_at_checkpoint: int
    challenge_tasks: list[str] = field(default_factory=list)
    correct_answers: int = 0
    total_questions: int = 0
    track_a_recall_score: float = 0.0
    track_b_recall_score: float = 0.0
    time_to_answer_seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LongitudinalCheckpoint":
        return cls(
            checkpoint_number=int(data["checkpoint_number"]),
            runs_completed_at_checkpoint=int(data["runs_completed_at_checkpoint"]),
            challenge_tasks=list(data.get("challenge_tasks", [])),
            correct_answers=int(data.get("correct_answers", 0)),
            total_questions=int(data.get("total_questions", 0)),
            track_a_recall_score=float(data.get("track_a_recall_score", 0.0)),
            track_b_recall_score=float(data.get("track_b_recall_score", 0.0)),
            time_to_answer_seconds=float(data.get("time_to_answer_seconds", 0.0)),
        )


@dataclass
class MVPTrustVerdict:
    would_choose_first: str
    would_stay_in: str
    trusts_with_production: str
    recommends_replacing_legacy: str
    projection_acceleration_justified: str
    verdict: MVPVerdictLevel
    evidence_summary: str

    def to_dict(self) -> dict:
        return {
            "would_choose_first": self.would_choose_first,
            "would_stay_in": self.would_stay_in,
            "trusts_with_production": self.trusts_with_production,
            "recommends_replacing_legacy": self.recommends_replacing_legacy,
            "projection_acceleration_justified": self.projection_acceleration_justified,
            "verdict": self.verdict.value,
            "evidence_summary": self.evidence_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MVPTrustVerdict":
        return cls(
            would_choose_first=data["would_choose_first"],
            would_stay_in=data["would_stay_in"],
            trusts_with_production=data["trusts_with_production"],
            recommends_replacing_legacy=data["recommends_replacing_legacy"],
            projection_acceleration_justified=data["projection_acceleration_justified"],
            verdict=MVPVerdictLevel(data["verdict"]),
            evidence_summary=data["evidence_summary"],
        )


@dataclass
class MetricWithConfidence:
    name: str
    value: float
    confidence: EvidenceConfidence
    class_a_count: int
    class_b_count: int
    class_c_count: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence.value,
            "class_a_count": self.class_a_count,
            "class_b_count": self.class_b_count,
            "class_c_count": self.class_c_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricWithConfidence":
        return cls(
            name=data["name"],
            value=float(data["value"]),
            confidence=EvidenceConfidence(data["confidence"]),
            class_a_count=int(data["class_a_count"]),
            class_b_count=int(data["class_b_count"]),
            class_c_count=int(data["class_c_count"]),
        )


# ---------------------------------------------------------------------------
# Track result (the central record)
# ---------------------------------------------------------------------------


@dataclass
class TrackResult:
    task_id: str
    track: Track
    evidence_class: EvidenceClass
    started_at: str
    completed_at: str
    duration_seconds: float
    outcome: Outcome
    deliverables_met: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    verification_method: str = ""
    verification_passed: bool = False
    recovery_needed: bool = False
    recovery_successful: bool = False
    recovery_time_seconds: float = 0.0
    context_switches: int = 0
    manual_reconstructions: int = 0
    tools_used: list[str] = field(default_factory=list)
    escapes: list[EscapeEvent] = field(default_factory=list)
    continuity_test: ContinuityResult | None = None
    governance_test: GovernanceResult | None = None
    awareness_snapshot: AwarenessSnapshot | None = None
    cognitive_load: CognitiveLoadResult | None = None
    interruption_test: InterruptionResult | None = None
    reality_drift: RealityDriftResult | None = None
    operator_trust: OperatorTrustResult | None = None
    meta_ide_test: MetaIDEResult | None = None
    resource_cost: ResourceCost | None = None
    browser_evidence: BrowserEvidence | None = None
    voice_test: VoiceResult | None = None
    preview_test: PreviewResult | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "track": self.track.value,
            "evidence_class": self.evidence_class.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "outcome": self.outcome.value,
            "deliverables_met": list(self.deliverables_met),
            "quality_score": self.quality_score,
            "verification_method": self.verification_method,
            "verification_passed": self.verification_passed,
            "recovery_needed": self.recovery_needed,
            "recovery_successful": self.recovery_successful,
            "recovery_time_seconds": self.recovery_time_seconds,
            "context_switches": self.context_switches,
            "manual_reconstructions": self.manual_reconstructions,
            "tools_used": list(self.tools_used),
            "escapes": [e.to_dict() for e in self.escapes],
            "continuity_test": self.continuity_test.to_dict() if self.continuity_test else None,
            "governance_test": self.governance_test.to_dict() if self.governance_test else None,
            "awareness_snapshot": self.awareness_snapshot.to_dict() if self.awareness_snapshot else None,
            "cognitive_load": self.cognitive_load.to_dict() if self.cognitive_load else None,
            "interruption_test": self.interruption_test.to_dict() if self.interruption_test else None,
            "reality_drift": self.reality_drift.to_dict() if self.reality_drift else None,
            "operator_trust": self.operator_trust.to_dict() if self.operator_trust else None,
            "meta_ide_test": self.meta_ide_test.to_dict() if self.meta_ide_test else None,
            "resource_cost": self.resource_cost.to_dict() if self.resource_cost else None,
            "browser_evidence": self.browser_evidence.to_dict() if self.browser_evidence else None,
            "voice_test": self.voice_test.to_dict() if self.voice_test else None,
            "preview_test": self.preview_test.to_dict() if self.preview_test else None,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackResult":
        return cls(
            task_id=data["task_id"],
            track=Track(data["track"]),
            evidence_class=EvidenceClass(data["evidence_class"]),
            started_at=data["started_at"],
            completed_at=data["completed_at"],
            duration_seconds=float(data["duration_seconds"]),
            outcome=Outcome(data["outcome"]),
            deliverables_met=list(data.get("deliverables_met", [])),
            quality_score=float(data.get("quality_score", 0.0)),
            verification_method=data.get("verification_method", ""),
            verification_passed=bool(data.get("verification_passed", False)),
            recovery_needed=bool(data.get("recovery_needed", False)),
            recovery_successful=bool(data.get("recovery_successful", False)),
            recovery_time_seconds=float(data.get("recovery_time_seconds", 0.0)),
            context_switches=int(data.get("context_switches", 0)),
            manual_reconstructions=int(data.get("manual_reconstructions", 0)),
            tools_used=list(data.get("tools_used", [])),
            escapes=[EscapeEvent.from_dict(e) for e in data.get("escapes", [])],
            continuity_test=ContinuityResult.from_dict(data["continuity_test"])
            if data.get("continuity_test")
            else None,
            governance_test=GovernanceResult.from_dict(data["governance_test"])
            if data.get("governance_test")
            else None,
            awareness_snapshot=AwarenessSnapshot.from_dict(data["awareness_snapshot"])
            if data.get("awareness_snapshot")
            else None,
            cognitive_load=CognitiveLoadResult.from_dict(data["cognitive_load"])
            if data.get("cognitive_load")
            else None,
            interruption_test=InterruptionResult.from_dict(data["interruption_test"])
            if data.get("interruption_test")
            else None,
            reality_drift=RealityDriftResult.from_dict(data["reality_drift"])
            if data.get("reality_drift")
            else None,
            operator_trust=OperatorTrustResult.from_dict(data["operator_trust"])
            if data.get("operator_trust")
            else None,
            meta_ide_test=MetaIDEResult.from_dict(data["meta_ide_test"])
            if data.get("meta_ide_test")
            else None,
            resource_cost=ResourceCost.from_dict(data["resource_cost"])
            if data.get("resource_cost")
            else None,
            browser_evidence=BrowserEvidence.from_dict(data["browser_evidence"])
            if data.get("browser_evidence")
            else None,
            voice_test=VoiceResult.from_dict(data["voice_test"])
            if data.get("voice_test")
            else None,
            preview_test=PreviewResult.from_dict(data["preview_test"])
            if data.get("preview_test")
            else None,
            notes=data.get("notes", ""),
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _umh_root() -> Path:
    return Path(os.environ.get("UMH_ROOT", "/opt/OS"))


class TaskRegistry:
    """CRUD for BenchmarkTask against data/certification/c29/tasks.jsonl."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = (
            Path(path)
            if path
            else _umh_root() / "data" / "certification" / "c29" / "tasks.jsonl"
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[BenchmarkTask]:
        if not self._path.exists():
            return []
        tasks: list[BenchmarkTask] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                tasks.append(BenchmarkTask.from_dict(json.loads(line)))
        return tasks

    def register(self, task: BenchmarkTask) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(task.to_dict()) + "\n")

    def get(self, task_id: str) -> BenchmarkTask | None:
        for task in self._read():
            if task.task_id == task_id:
                return task
        return None

    def list_all(self) -> list[BenchmarkTask]:
        return self._read()

    def list_by_category(self, cat: BenchmarkCategory) -> list[BenchmarkTask]:
        return [t for t in self._read() if t.category == cat]

    def list_by_project(self, project: str) -> list[BenchmarkTask]:
        return [t for t in self._read() if t.project == project]

    def count(self) -> int:
        return len(self._read())


class ResultStore:
    """CRUD for TrackResult against data/certification/c29/results.jsonl."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = (
            Path(path)
            if path
            else _umh_root() / "data" / "certification" / "c29" / "results.jsonl"
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[TrackResult]:
        if not self._path.exists():
            return []
        results: list[TrackResult] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                results.append(TrackResult.from_dict(json.loads(line)))
        return results

    def record(self, result: TrackResult) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result.to_dict()) + "\n")

    def get_results(self, task_id: str) -> list[TrackResult]:
        return [r for r in self._read() if r.task_id == task_id]

    def get_track_results(self, task_id: str, track: Track) -> list[TrackResult]:
        return [r for r in self._read() if r.task_id == task_id and r.track == track]

    def list_all(self) -> list[TrackResult]:
        return self._read()

    def list_by_track(self, track: Track) -> list[TrackResult]:
        return [r for r in self._read() if r.track == track]

    def list_by_evidence_class(self, ec: EvidenceClass) -> list[TrackResult]:
        return [r for r in self._read() if r.evidence_class == ec]

    def count(self) -> int:
        return len(self._read())

    def evidence_distribution(self) -> dict[str, int]:
        dist = {ec.value: 0 for ec in EvidenceClass}
        for r in self._read():
            dist[r.evidence_class.value] += 1
        return dist


# ---------------------------------------------------------------------------
# C33 — Execution Harness Registry & Route Recommendations
# ---------------------------------------------------------------------------


class ExecutionHarness(str, Enum):
    """Known execution harnesses UMH can orchestrate or compare against."""
    CLAUDE_CODE = "claude_code"
    CODEX_CLI = "codex_cli"
    CURSOR = "cursor"
    GEMINI_CLI = "gemini_cli"
    OPENHANDS = "openhands"
    DEVIN = "devin"
    AMP = "amp"
    WINDSURF = "windsurf"
    PLAYWRIGHT = "playwright"
    COMPUTER_USE = "computer_use"
    UMH_NATIVE = "umh_native"


class ComparisonDimension(str, Enum):
    """Dimensions for comparing harnesses — C33 extends beyond speed/quality."""
    SPEED = "speed"
    QUALITY = "quality"
    GOVERNANCE = "governance"
    COMPOUNDING = "compounding"
    OPERATOR_EXPERIENCE = "operator_experience"
    ORCHESTRATION = "orchestration"
    COST = "cost"
    CONTEXT_RETENTION = "context_retention"
    RECOVERABILITY = "recoverability"
    RELIABILITY = "reliability"


class UMHRole(str, Enum):
    """How UMH relates to the execution for a given task type."""
    SKIP_GOVERNANCE = "skip_governance"
    GOVERN_VERIFY = "govern_verify"
    FULL_APPROVAL = "full_approval"
    NATIVE = "native"
    ORCHESTRATE_VERIFY = "orchestrate_verify"


@dataclass
class RouteRecommendation:
    """Deterministic recommendation for which harness to use for a task type."""
    task_type: str
    recommended_harness: str
    umh_role: str
    confidence: float
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RouteRecommendation":
        return cls(
            task_type=data["task_type"],
            recommended_harness=data["recommended_harness"],
            umh_role=data["umh_role"],
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
        )


@dataclass
class HarnessProfile:
    """Capability profile for a known execution harness."""
    harness: ExecutionHarness
    strengths: list[ComparisonDimension] = field(default_factory=list)
    weaknesses: list[ComparisonDimension] = field(default_factory=list)
    supports_governance: bool = False
    supports_compounding: bool = False
    supports_orchestration: bool = False
    cost_tier: str = "medium"

    def to_dict(self) -> dict:
        return {
            "harness": self.harness.value,
            "strengths": [s.value for s in self.strengths],
            "weaknesses": [w.value for w in self.weaknesses],
            "supports_governance": self.supports_governance,
            "supports_compounding": self.supports_compounding,
            "supports_orchestration": self.supports_orchestration,
            "cost_tier": self.cost_tier,
        }


HARNESS_PROFILES: dict[str, HarnessProfile] = {
    ExecutionHarness.CLAUDE_CODE.value: HarnessProfile(
        harness=ExecutionHarness.CLAUDE_CODE,
        strengths=[ComparisonDimension.SPEED, ComparisonDimension.QUALITY, ComparisonDimension.CONTEXT_RETENTION],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING],
        cost_tier="high",
    ),
    ExecutionHarness.CODEX_CLI.value: HarnessProfile(
        harness=ExecutionHarness.CODEX_CLI,
        strengths=[ComparisonDimension.SPEED],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING, ComparisonDimension.ORCHESTRATION],
        cost_tier="high",
    ),
    ExecutionHarness.CURSOR.value: HarnessProfile(
        harness=ExecutionHarness.CURSOR,
        strengths=[ComparisonDimension.OPERATOR_EXPERIENCE, ComparisonDimension.SPEED],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING, ComparisonDimension.ORCHESTRATION],
        cost_tier="medium",
    ),
    ExecutionHarness.GEMINI_CLI.value: HarnessProfile(
        harness=ExecutionHarness.GEMINI_CLI,
        strengths=[ComparisonDimension.SPEED, ComparisonDimension.COST],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING],
        cost_tier="low",
    ),
    ExecutionHarness.OPENHANDS.value: HarnessProfile(
        harness=ExecutionHarness.OPENHANDS,
        strengths=[ComparisonDimension.ORCHESTRATION],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.RELIABILITY],
        cost_tier="medium",
    ),
    ExecutionHarness.DEVIN.value: HarnessProfile(
        harness=ExecutionHarness.DEVIN,
        strengths=[ComparisonDimension.ORCHESTRATION, ComparisonDimension.CONTEXT_RETENTION],
        weaknesses=[ComparisonDimension.COST, ComparisonDimension.GOVERNANCE],
        cost_tier="high",
    ),
    ExecutionHarness.AMP.value: HarnessProfile(
        harness=ExecutionHarness.AMP,
        strengths=[ComparisonDimension.SPEED, ComparisonDimension.OPERATOR_EXPERIENCE],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING],
        cost_tier="medium",
    ),
    ExecutionHarness.WINDSURF.value: HarnessProfile(
        harness=ExecutionHarness.WINDSURF,
        strengths=[ComparisonDimension.OPERATOR_EXPERIENCE],
        weaknesses=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING, ComparisonDimension.ORCHESTRATION],
        cost_tier="medium",
    ),
    ExecutionHarness.PLAYWRIGHT.value: HarnessProfile(
        harness=ExecutionHarness.PLAYWRIGHT,
        strengths=[ComparisonDimension.RELIABILITY, ComparisonDimension.RECOVERABILITY],
        weaknesses=[ComparisonDimension.OPERATOR_EXPERIENCE],
        supports_orchestration=True,
        cost_tier="low",
    ),
    ExecutionHarness.UMH_NATIVE.value: HarnessProfile(
        harness=ExecutionHarness.UMH_NATIVE,
        strengths=[ComparisonDimension.GOVERNANCE, ComparisonDimension.COMPOUNDING, ComparisonDimension.ORCHESTRATION],
        weaknesses=[ComparisonDimension.SPEED],
        supports_governance=True,
        supports_compounding=True,
        supports_orchestration=True,
        cost_tier="high",
    ),
}


_ROUTE_TABLE: dict[str, RouteRecommendation] = {
    "simple_code": RouteRecommendation(
        task_type="simple_code",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.SKIP_GOVERNANCE.value,
        confidence=0.95,
        reasoning="Low-risk, reversible code change — governance overhead not justified",
    ),
    "complex_code": RouteRecommendation(
        task_type="complex_code",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.GOVERN_VERIFY.value,
        confidence=0.90,
        reasoning="Multi-file change with risk — govern execution, verify outcome",
    ),
    "schema_migration": RouteRecommendation(
        task_type="schema_migration",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.FULL_APPROVAL.value,
        confidence=0.95,
        reasoning="Irreversible database change — full approval gate required",
    ),
    "business_op": RouteRecommendation(
        task_type="business_op",
        recommended_harness=ExecutionHarness.UMH_NATIVE.value,
        umh_role=UMHRole.NATIVE.value,
        confidence=0.90,
        reasoning="External-facing operation — UMH governs end-to-end with proof",
    ),
    "browser_verify": RouteRecommendation(
        task_type="browser_verify",
        recommended_harness=ExecutionHarness.PLAYWRIGHT.value,
        umh_role=UMHRole.ORCHESTRATE_VERIFY.value,
        confidence=0.85,
        reasoning="Visual verification — Playwright for browser, UMH for proof capture",
    ),
    "refactor": RouteRecommendation(
        task_type="refactor",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.GOVERN_VERIFY.value,
        confidence=0.85,
        reasoning="Multi-file structural change — govern for consistency, verify tests",
    ),
    "adapter_integration": RouteRecommendation(
        task_type="adapter_integration",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.GOVERN_VERIFY.value,
        confidence=0.85,
        reasoning="New adapter wiring — govern for architecture compliance, verify integration",
    ),
    "bug_fix": RouteRecommendation(
        task_type="bug_fix",
        recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
        umh_role=UMHRole.GOVERN_VERIFY.value,
        confidence=0.85,
        reasoning="Bug fix — govern for regression check, verify fix holds",
    ),
}


def recommend_harness(
    task_type: str, complexity: str = "medium"
) -> RouteRecommendation:
    """Return a deterministic route recommendation for a task type.

    Falls back to governed Claude Code for unknown task types.
    Complexity adjusts UMH role: high complexity upgrades to full approval.
    """
    rec = _ROUTE_TABLE.get(task_type)
    if rec is None:
        rec = RouteRecommendation(
            task_type=task_type,
            recommended_harness=ExecutionHarness.CLAUDE_CODE.value,
            umh_role=UMHRole.GOVERN_VERIFY.value,
            confidence=0.5,
            reasoning=f"Unknown task type '{task_type}' — default to governed CC",
        )

    if complexity == "high" and rec.umh_role == UMHRole.SKIP_GOVERNANCE.value:
        return RouteRecommendation(
            task_type=rec.task_type,
            recommended_harness=rec.recommended_harness,
            umh_role=UMHRole.GOVERN_VERIFY.value,
            confidence=rec.confidence * 0.9,
            reasoning=rec.reasoning + " (upgraded: high complexity)",
        )

    return rec


def get_route_table() -> list[RouteRecommendation]:
    """Return the full route recommendation table."""
    return list(_ROUTE_TABLE.values())
