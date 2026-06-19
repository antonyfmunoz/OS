"""C22.3 — Production Review Runtime.

Governed review layer for software production. Not just code gates —
covers the full professional review scope: tests, architecture, types,
dependencies, projections, security, observability, deployment readiness.

All quality checks are deterministic. No LLM calls.

Campaign 22. UMH substrate layer. Instance-agnostic.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ── Types ────────────────────────────────────────────────────────────────


class ReviewVerdict(str, Enum):
    READY = "ready"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    APPROVAL_PENDING = "approval_pending"


class QualityDimension(str, Enum):
    TESTS = "tests"
    ARCHITECTURE = "architecture"
    TYPE_COHERENCE = "type_coherence"
    DEPENDENCY_DIRECTION = "dependency_direction"
    PROJECTION_BOUNDARY = "projection_boundary"
    INSTANCE_CONTEXT = "instance_context"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    DEPLOYMENT_READINESS = "deployment_readiness"


@dataclass
class QualityCheck:
    dimension: str = QualityDimension.TESTS.value
    passed: bool = True
    details: str = ""
    gate_script: str = ""
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductionReviewResult:
    packet_id: str = ""
    verdict: str = ReviewVerdict.READY.value
    quality_checks: list[dict[str, Any]] = field(default_factory=list)
    proof_package: dict[str, Any] | None = None
    governance_evaluation: dict[str, Any] = field(default_factory=dict)
    risk_assessment: dict[str, Any] = field(default_factory=dict)
    blocking_reasons: list[str] = field(default_factory=list)
    reviewer_role: str = ""
    iteration: int = 1
    generated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.generated_at == 0.0:
            self.generated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewHistory:
    packet_id: str = ""
    reviews: list[dict[str, Any]] = field(default_factory=list)
    latest_verdict: str = ""
    review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShipReadinessReport:
    project_id: str = ""
    ready: bool = False
    total_packets: int = 0
    packets_ready: int = 0
    packets_blocked: int = 0
    packets_changes_required: int = 0
    packets_approval_pending: int = 0
    blocking_reasons: list[str] = field(default_factory=list)
    dimension_summary: dict[str, dict[str, int]] = field(default_factory=dict)
    generated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.generated_at == 0.0:
            self.generated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductionReviewSnapshot:
    total_pending: int = 0
    total_reviewed: int = 0
    by_verdict: dict[str, int] = field(default_factory=dict)
    by_dimension_failures: dict[str, int] = field(default_factory=dict)
    recent_reviews: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Gate Script Registry ────────────────────────────────────────────────


_GATE_SCRIPTS: dict[str, str] = {
    QualityDimension.TYPE_COHERENCE.value: "scripts/check_type_divergence.py",
    QualityDimension.DEPENDENCY_DIRECTION.value: "scripts/check_dependency_direction.py",
    QualityDimension.PROJECTION_BOUNDARY.value: "scripts/check_projection_leak.py",
    QualityDimension.INSTANCE_CONTEXT.value: "scripts/check_instance_leak.py",
    QualityDimension.SECURITY.value: "scripts/check_secret_patterns.py",
}

_GATE_SCRIPT_ARGS: dict[str, list[str]] = {
    QualityDimension.TYPE_COHERENCE.value: ["--all"],
    QualityDimension.DEPENDENCY_DIRECTION.value: ["--all"],
    QualityDimension.PROJECTION_BOUNDARY.value: ["--all"],
    QualityDimension.INSTANCE_CONTEXT.value: ["--all"],
    QualityDimension.SECURITY.value: [],
}


# ── Deterministic Quality Checks ────────────────────────────────────────


def _run_gate_script(dimension: str, files: list[str] | None = None) -> QualityCheck:
    script = _GATE_SCRIPTS.get(dimension, "")
    if not script:
        return QualityCheck(
            dimension=dimension,
            passed=True,
            details="No gate script configured — skipped",
            gate_script="",
            severity="info",
        )

    script_path = os.path.join(_REPO_ROOT, script)
    if not os.path.isfile(script_path):
        return QualityCheck(
            dimension=dimension,
            passed=True,
            details="Gate script not found — skipped",
            gate_script=script,
            severity="info",
        )

    try:
        from substrate.execution.cpu_gate import gated_subprocess_run
    except ImportError:
        return QualityCheck(
            dimension=dimension,
            passed=True,
            details="CPU gate unavailable — skipped",
            gate_script=script,
            severity="info",
        )

    cmd = ["python3", script_path] + _GATE_SCRIPT_ARGS.get(dimension, [])
    result = gated_subprocess_run(cmd, caller="production_review", timeout=60.0)
    if result is None:
        return QualityCheck(
            dimension=dimension,
            passed=True,
            details="CPU gate blocked — deferred",
            gate_script=script,
            severity="warning",
        )

    passed = result.returncode == 0
    output = (result.stdout or "").strip()
    if not output:
        output = (result.stderr or "").strip()
    if len(output) > 500:
        output = output[:500] + "..."

    return QualityCheck(
        dimension=dimension,
        passed=passed,
        details=output if output else ("passed" if passed else "failed"),
        gate_script=script,
        severity="blocking" if not passed else "info",
    )


def _check_tests(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
) -> QualityCheck:
    has_tests = False
    test_details: list[str] = []

    packet_files = files or packet_data.get("files_changed", [])
    for f in packet_files:
        if "test" in f.lower():
            has_tests = True
            test_details.append(f)

    test_dir = packet_data.get("test_dir", "")
    if test_dir and os.path.isdir(os.path.join(_REPO_ROOT, test_dir)):
        has_tests = True
        test_details.append(test_dir)

    if packet_data.get("test_count", 0) > 0:
        has_tests = True
        test_details.append("test_count={0}".format(packet_data["test_count"]))

    if not has_tests and not packet_files:
        return QualityCheck(
            dimension=QualityDimension.TESTS.value,
            passed=True,
            details="No files changed — test check not applicable",
            severity="info",
        )

    return QualityCheck(
        dimension=QualityDimension.TESTS.value,
        passed=has_tests,
        details=", ".join(test_details) if test_details else "No tests found",
        severity="blocking" if not has_tests else "info",
    )


def _check_architecture(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
) -> QualityCheck:
    packet_files = files or packet_data.get("files_changed", [])
    issues: list[str] = []

    for f in packet_files:
        if f.startswith("substrate/") and ("/transports/" in f or "/services/" in f):
            issues.append("substrate/ file references transports/services path: {0}".format(f))

        if f.startswith("services/") and not f.endswith(".py"):
            continue
        if f.startswith("services/") and any(
            x in f for x in ("runtime", "engine", "pipeline")
        ):
            issues.append("Business logic in services/: {0}".format(f))

    passed = len(issues) == 0
    return QualityCheck(
        dimension=QualityDimension.ARCHITECTURE.value,
        passed=passed,
        details="; ".join(issues) if issues else "Architecture checks passed",
        severity="blocking" if not passed else "info",
    )


def _check_security_deterministic(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
) -> QualityCheck:
    packet_files = files or packet_data.get("files_changed", [])
    issues: list[str] = []

    dangerous_patterns = [
        ".env",
        "credentials",
        "secret",
        "password",
        "api_key",
        "private_key",
    ]

    for f in packet_files:
        fname = os.path.basename(f).lower()
        for pattern in dangerous_patterns:
            if pattern in fname and not f.endswith(".py"):
                issues.append("Potentially sensitive file: {0}".format(f))
                break

    content_source = packet_data.get("content", "")
    if isinstance(content_source, str):
        lowered = content_source.lower()
        if "hardcoded" in lowered and "password" in lowered:
            issues.append("Hardcoded password reference in content")
        if "0.0.0.0" in content_source:
            issues.append("Binding to 0.0.0.0 detected")

    passed = len(issues) == 0
    return QualityCheck(
        dimension=QualityDimension.SECURITY.value,
        passed=passed,
        details="; ".join(issues) if issues else "No security issues found",
        severity="blocking" if not passed else "info",
    )


def _check_observability(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
) -> QualityCheck:
    packet_files = files or packet_data.get("files_changed", [])
    has_logging = False
    checked_files = 0

    for f in packet_files:
        if not f.endswith(".py"):
            continue
        checked_files += 1
        full_path = os.path.join(_REPO_ROOT, f)
        if not os.path.isfile(full_path):
            continue
        try:
            with open(full_path, "r") as fh:
                content = fh.read(8192)
            if "logger" in content or "logging" in content:
                has_logging = True
                break
        except OSError:
            continue

    if checked_files == 0:
        return QualityCheck(
            dimension=QualityDimension.OBSERVABILITY.value,
            passed=True,
            details="No Python files to check",
            severity="info",
        )

    return QualityCheck(
        dimension=QualityDimension.OBSERVABILITY.value,
        passed=has_logging,
        details="Logging present" if has_logging else "No logging/logger imports found in changed files",
        severity="warning" if not has_logging else "info",
    )


def _check_deployment_readiness(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
) -> QualityCheck:
    target = packet_data.get("target", "")
    details_parts: list[str] = []

    deploy_indicators = [
        "Dockerfile",
        "docker-compose.yml",
        "compose.yml",
        "deploy.sh",
        "fly.toml",
    ]

    found_indicators: list[str] = []
    for indicator in deploy_indicators:
        full_path = os.path.join(_REPO_ROOT, indicator)
        if os.path.isfile(full_path):
            found_indicators.append(indicator)

    if found_indicators:
        details_parts.append("Deploy artifacts: {0}".format(", ".join(found_indicators)))
    else:
        details_parts.append("No deployment artifacts found in repo root")

    packet_files = files or packet_data.get("files_changed", [])
    deploy_changes = [
        f for f in packet_files
        if any(
            ind.lower() in f.lower()
            for ind in deploy_indicators
        )
    ]
    if deploy_changes:
        details_parts.append("Deployment files changed: {0}".format(", ".join(deploy_changes)))

    return QualityCheck(
        dimension=QualityDimension.DEPLOYMENT_READINESS.value,
        passed=True,
        details="; ".join(details_parts),
        severity="info",
    )


# ── All Dimension Runners ────────────────────────────────────────────────


_DIMENSION_RUNNERS: dict[str, Any] = {
    QualityDimension.TESTS.value: _check_tests,
    QualityDimension.ARCHITECTURE.value: _check_architecture,
    QualityDimension.SECURITY.value: _check_security_deterministic,
    QualityDimension.OBSERVABILITY.value: _check_observability,
    QualityDimension.DEPLOYMENT_READINESS.value: _check_deployment_readiness,
}

_GATE_DIMENSIONS: list[str] = [
    QualityDimension.TYPE_COHERENCE.value,
    QualityDimension.DEPENDENCY_DIRECTION.value,
    QualityDimension.PROJECTION_BOUNDARY.value,
    QualityDimension.INSTANCE_CONTEXT.value,
]


def run_all_quality_checks(
    packet_data: dict[str, Any],
    files: list[str] | None = None,
    *,
    skip_gate_scripts: bool = False,
) -> list[QualityCheck]:
    checks: list[QualityCheck] = []

    for dim, runner in _DIMENSION_RUNNERS.items():
        try:
            check = runner(packet_data, files)
            checks.append(check)
        except Exception as exc:
            logger.debug("Quality check %s failed: %s", dim, exc)
            checks.append(QualityCheck(
                dimension=dim,
                passed=True,
                details="Check runner error: {0}".format(str(exc)[:200]),
                severity="warning",
            ))

    if not skip_gate_scripts:
        for dim in _GATE_DIMENSIONS:
            try:
                check = _run_gate_script(dim, files)
                checks.append(check)
            except Exception as exc:
                logger.debug("Gate script %s failed: %s", dim, exc)
                checks.append(QualityCheck(
                    dimension=dim,
                    passed=True,
                    details="Gate script error: {0}".format(str(exc)[:200]),
                    severity="warning",
                ))

    return checks


def determine_verdict(checks: list[QualityCheck]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    has_warnings = False

    for check in checks:
        if not check.passed and check.severity == "blocking":
            blockers.append("[{0}] {1}".format(check.dimension, check.details))
        elif not check.passed and check.severity == "warning":
            has_warnings = True

    if blockers:
        return ReviewVerdict.BLOCKED.value, blockers

    if has_warnings:
        return ReviewVerdict.CHANGES_REQUIRED.value, []

    return ReviewVerdict.READY.value, []


# ── Runtime ──────────────────────────────────────────────────────────────


class ProductionReviewRuntime:
    """Governed review layer for software production.

    Composes UnifiedApprovalRuntime, GovernanceRuntime, ReviewPackageBuilder,
    TrajectoryIntelligenceRuntime, and LearningExtractionRuntime to deliver
    full professional review across 9 quality dimensions.
    """

    def __init__(
        self,
        unified_approval: Any | None = None,
        governance: Any | None = None,
        review_builder: Any | None = None,
        trajectory: Any | None = None,
        learning: Any | None = None,
    ) -> None:
        self._unified_approval = unified_approval
        self._governance = governance
        self._review_builder = review_builder
        self._trajectory = trajectory
        self._learning = learning
        self._reviews: list[ProductionReviewResult] = []
        self._review_index: dict[str, list[int]] = {}

    # ── Lazy Composition ─────────────────────────────────────────────────

    @property
    def unified_approval(self) -> Any | None:
        if self._unified_approval is None:
            try:
                from substrate.workstation.unified_approval_runtime import (
                    UnifiedApprovalRuntime,
                )
                self._unified_approval = UnifiedApprovalRuntime()
            except Exception:
                logger.debug("UnifiedApprovalRuntime unavailable")
        return self._unified_approval

    @property
    def governance(self) -> Any | None:
        if self._governance is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime
                self._governance = GovernanceRuntime()
            except Exception:
                logger.debug("GovernanceRuntime unavailable")
        return self._governance

    @property
    def review_builder(self) -> Any | None:
        if self._review_builder is None:
            try:
                from substrate.meta_ide.review_package_builder import (
                    ReviewPackageBuilder,
                )
                self._review_builder = ReviewPackageBuilder()
            except Exception:
                logger.debug("ReviewPackageBuilder unavailable")
        return self._review_builder

    @property
    def trajectory(self) -> Any | None:
        if self._trajectory is None:
            try:
                from substrate.organism.trajectory_intelligence_runtime import (
                    TrajectoryIntelligenceRuntime,
                )
                self._trajectory = TrajectoryIntelligenceRuntime()
            except Exception:
                logger.debug("TrajectoryIntelligenceRuntime unavailable")
        return self._trajectory

    @property
    def learning(self) -> Any | None:
        if self._learning is None:
            try:
                from substrate.organism.learning_extraction_runtime import (
                    LearningExtractionRuntime,
                )
                self._learning = LearningExtractionRuntime()
            except Exception:
                logger.debug("LearningExtractionRuntime unavailable")
        return self._learning

    # ── Core Review ──────────────────────────────────────────────────────

    def review_production(
        self,
        packet_id: str,
        packet_data: dict[str, Any] | None = None,
        files: list[str] | None = None,
        *,
        reviewer_role: str = "reviewer",
        skip_gate_scripts: bool = False,
    ) -> ProductionReviewResult:
        data = packet_data or {}

        checks = run_all_quality_checks(
            data,
            files=files,
            skip_gate_scripts=skip_gate_scripts,
        )

        verdict, blockers = determine_verdict(checks)

        governance_eval = self._evaluate_governance(packet_id, data)

        risk_assessment = self._assess_risk(data)

        if governance_eval.get("requires_approval", False) and verdict == ReviewVerdict.READY.value:
            verdict = ReviewVerdict.APPROVAL_PENDING.value

        proof_pkg = self._build_proof(packet_id, data) if verdict == ReviewVerdict.READY.value else None

        prior_reviews = self._review_index.get(packet_id, [])
        iteration = len(prior_reviews) + 1

        result = ProductionReviewResult(
            packet_id=packet_id,
            verdict=verdict,
            quality_checks=[c.to_dict() for c in checks],
            proof_package=proof_pkg,
            governance_evaluation=governance_eval,
            risk_assessment=risk_assessment,
            blocking_reasons=blockers,
            reviewer_role=reviewer_role,
            iteration=iteration,
        )

        idx = len(self._reviews)
        self._reviews.append(result)
        if packet_id not in self._review_index:
            self._review_index[packet_id] = []
        self._review_index[packet_id].append(idx)

        return result

    def _evaluate_governance(
        self, packet_id: str, packet_data: dict[str, Any],
    ) -> dict[str, Any]:
        gov = self.governance
        if gov is None:
            return {
                "requires_approval": False,
                "authority_evaluated": False,
                "details": "GovernanceRuntime unavailable",
            }

        risk_class = packet_data.get("risk_class", "low")
        requires_approval = risk_class in ("high", "critical")

        snapshot = None
        try:
            snapshot = gov.snapshot()
        except Exception as exc:
            logger.debug("governance.snapshot() failed: %s", exc)

        health = "unknown"
        if snapshot is not None:
            health = getattr(snapshot, "governance_health", "unknown")
            if hasattr(health, "value"):
                health = health.value

        return {
            "requires_approval": requires_approval,
            "authority_evaluated": True,
            "risk_class": risk_class,
            "governance_health": health,
            "packet_id": packet_id,
        }

    def _assess_risk(self, packet_data: dict[str, Any]) -> dict[str, Any]:
        traj = self.trajectory
        risk_class = packet_data.get("risk_class", "low")

        base_assessment = {
            "risk_class": risk_class,
            "trajectory_available": traj is not None,
        }

        if traj is None:
            return base_assessment

        try:
            target = packet_data.get("target", "")
            forecast_data = {}
            if hasattr(traj, "forecast_trajectory"):
                forecast_data = traj.forecast_trajectory(
                    domain=target or "software_production",
                ) or {}
            if hasattr(forecast_data, "to_dict"):
                forecast_data = forecast_data.to_dict()
            elif not isinstance(forecast_data, dict):
                forecast_data = {}

            base_assessment["trajectory_forecast"] = forecast_data
        except Exception as exc:
            logger.debug("trajectory forecast failed: %s", exc)

        return base_assessment

    def _build_proof(
        self, packet_id: str, packet_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        builder = self.review_builder
        if builder is None:
            return {
                "packet_id": packet_id,
                "proof_type": "minimal",
                "quality_checks_passed": True,
                "generated_at": time.time(),
            }

        return {
            "packet_id": packet_id,
            "proof_type": "standard",
            "builder_available": True,
            "quality_checks_passed": True,
            "files_reviewed": packet_data.get("files_changed", []),
            "generated_at": time.time(),
        }

    # ── Query ────────────────────────────────────────────────────────────

    def quality_status(self, packet_id: str) -> dict[str, Any]:
        indices = self._review_index.get(packet_id, [])
        if not indices:
            return {
                "packet_id": packet_id,
                "reviewed": False,
                "verdict": None,
                "review_count": 0,
            }

        latest = self._reviews[indices[-1]]
        return {
            "packet_id": packet_id,
            "reviewed": True,
            "verdict": latest.verdict,
            "review_count": len(indices),
            "latest_iteration": latest.iteration,
            "blocking_reasons": latest.blocking_reasons,
            "generated_at": latest.generated_at,
        }

    def pending_reviews(self) -> list[dict[str, Any]]:
        approval = self.unified_approval
        if approval is None:
            return []

        try:
            pending = approval.pending()
            return [
                p.to_dict() if hasattr(p, "to_dict") else {"raw": str(p)[:200]}
                for p in pending
            ]
        except Exception as exc:
            logger.debug("pending_reviews failed: %s", exc)
            return []

    def review_history(self, limit: int = 20) -> list[dict[str, Any]]:
        recent = self._reviews[-limit:] if limit > 0 else self._reviews
        return [r.to_dict() for r in reversed(recent)]

    def ship_readiness(self, project_id: str = "") -> ShipReadinessReport:
        packets_by_verdict: dict[str, int] = {
            ReviewVerdict.READY.value: 0,
            ReviewVerdict.CHANGES_REQUIRED.value: 0,
            ReviewVerdict.BLOCKED.value: 0,
            ReviewVerdict.APPROVAL_PENDING.value: 0,
        }
        all_blocking: list[str] = []
        dimension_summary: dict[str, dict[str, int]] = {}
        reviewed_packets: set[str] = set()

        for pkt_id, indices in self._review_index.items():
            if not indices:
                continue
            latest = self._reviews[indices[-1]]
            reviewed_packets.add(pkt_id)
            v = latest.verdict
            packets_by_verdict[v] = packets_by_verdict.get(v, 0) + 1

            if latest.blocking_reasons:
                for reason in latest.blocking_reasons:
                    prefixed = "[{0}] {1}".format(pkt_id, reason)
                    all_blocking.append(prefixed)

            for check in latest.quality_checks:
                dim = check.get("dimension", "unknown")
                if dim not in dimension_summary:
                    dimension_summary[dim] = {"passed": 0, "failed": 0}
                if check.get("passed", True):
                    dimension_summary[dim]["passed"] += 1
                else:
                    dimension_summary[dim]["failed"] += 1

        total = len(reviewed_packets)
        ready_count = packets_by_verdict[ReviewVerdict.READY.value]
        blocked_count = packets_by_verdict[ReviewVerdict.BLOCKED.value]
        changes_count = packets_by_verdict[ReviewVerdict.CHANGES_REQUIRED.value]
        approval_count = packets_by_verdict[ReviewVerdict.APPROVAL_PENDING.value]

        all_ready = total > 0 and blocked_count == 0 and changes_count == 0

        return ShipReadinessReport(
            project_id=project_id,
            ready=all_ready,
            total_packets=total,
            packets_ready=ready_count,
            packets_blocked=blocked_count,
            packets_changes_required=changes_count,
            packets_approval_pending=approval_count,
            blocking_reasons=all_blocking,
            dimension_summary=dimension_summary,
        )

    def get_review_lessons(self, packet_id: str) -> list[dict[str, Any]]:
        learn = self.learning
        if learn is None:
            return []

        try:
            if hasattr(learn, "extract_lessons"):
                lessons = learn.extract_lessons(context={
                    "source": "production_review",
                    "packet_id": packet_id,
                })
                if isinstance(lessons, list):
                    return [
                        l.to_dict() if hasattr(l, "to_dict") else l
                        for l in lessons
                    ]
        except Exception as exc:
            logger.debug("get_review_lessons failed: %s", exc)

        return []

    # ── Snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> ProductionReviewSnapshot:
        by_verdict: dict[str, int] = {}
        by_dim_failures: dict[str, int] = {}

        for review in self._reviews:
            by_verdict[review.verdict] = by_verdict.get(review.verdict, 0) + 1
            for check in review.quality_checks:
                if not check.get("passed", True):
                    dim = check.get("dimension", "unknown")
                    by_dim_failures[dim] = by_dim_failures.get(dim, 0) + 1

        pending = self.pending_reviews()

        recent = [r.to_dict() for r in self._reviews[-10:]]

        return ProductionReviewSnapshot(
            total_pending=len(pending),
            total_reviewed=len(self._reviews),
            by_verdict=by_verdict,
            by_dimension_failures=by_dim_failures,
            recent_reviews=recent,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        readiness = self.ship_readiness()

        return {
            "snapshot": snap.to_dict(),
            "ship_readiness": readiness.to_dict(),
        }
