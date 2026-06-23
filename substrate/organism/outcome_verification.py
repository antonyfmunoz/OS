"""Outcome verification engine — replaces 'Task Complete' with 'Outcome Verified'.

Every task gains graduated verification through a data-driven VerificationPlan.
Composes ProofRuntime, OutcomeLearningLoop, and BrowserVerificationGate.

C26A: Reality Correspondence Certification — Phase 1.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────


class VerificationLevel(str, Enum):
    """Graduated verification depth — maps to projection certification L0-L5."""

    ARTIFACT_EXISTS = "artifact_exists"
    BUILD_PASSES = "build_passes"
    DEPLOY_HEALTHY = "deploy_healthy"
    UI_OPERATIONAL = "ui_operational"
    WORKFLOW_OPERATIONAL = "workflow_operational"


class OutcomeVerificationStatus(str, Enum):
    """Overall verification status for a work item."""

    UNVERIFIED = "unverified"
    PARTIAL = "partial"
    VERIFIED = "verified"
    FAILED = "failed"


class VerificationMethod(str, Enum):
    """How a verification step was performed."""

    DETERMINISTIC_CHECK = "deterministic_check"
    HTTP_PROBE = "http_probe"
    BUNDLE_INSPECTION = "bundle_inspection"
    BROWSER_CHECK = "browser_check"
    TEST_EXECUTION = "test_execution"
    MANUAL_CONFIRMATION = "manual_confirmation"
    FILE_EXISTENCE = "file_existence"
    PROCESS_CHECK = "process_check"


# ── Data types ───────────────────────────────────────────────────────────


@dataclass
class VerificationStepResult:
    """Result of a single verification step within a plan."""

    level: VerificationLevel
    method: VerificationMethod
    passed: bool
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "method": self.method.value,
            "passed": self.passed,
            "description": self.description,
            "evidence": self.evidence,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class VerificationPlanStep:
    """A single step in a verification plan — what to check and how."""

    level: VerificationLevel
    method: VerificationMethod
    description: str
    check_fn: Callable[[], VerificationStepResult] | None = None
    required: bool = True
    timeout_seconds: float = 30.0


@dataclass
class VerificationPlan:
    """Data-driven verification plan for a task type.

    Each plan defines ordered steps from lowest to highest verification level.
    Steps execute in order; a required step failure stops further verification.
    """

    plan_id: str = field(
        default_factory=lambda: f"vp-{uuid4().hex[:12]}"
    )
    task_type: str = ""
    steps: list[VerificationPlanStep] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def max_level(self) -> VerificationLevel | None:
        if not self.steps:
            return None
        return self.steps[-1].level


@dataclass
class OutcomeVerification:
    """Complete verification record for a work item."""

    verification_id: str = field(
        default_factory=lambda: f"ov-{uuid4().hex[:12]}"
    )
    work_id: str = ""
    task_type: str = ""
    plan: VerificationPlan | None = None
    results: list[VerificationStepResult] = field(default_factory=list)
    status: OutcomeVerificationStatus = OutcomeVerificationStatus.UNVERIFIED
    highest_level_passed: VerificationLevel | None = None
    confidence: float = 0.0
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    verified_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "work_id": self.work_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "highest_level_passed": (
                self.highest_level_passed.value
                if self.highest_level_passed
                else None
            ),
            "confidence": self.confidence,
            "results": [r.to_dict() for r in self.results],
            "evidence_summary": self.evidence_summary,
            "verified_at": (
                self.verified_at.isoformat() if self.verified_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }


# ── Verification Plan Registry ──────────────────────────────────────────


class VerificationPlanRegistry:
    """Data-driven registry of verification plans per task type.

    Plans are loaded from a JSON config file. Each entry maps a task_type
    to its verification steps (level + method + description + required).
    """

    def __init__(self, config_path: str | None = None) -> None:
        if config_path is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            config_path = os.path.join(
                root, "data", "umh", "verification_plans.json"
            )
        self._config_path = config_path
        self._plans: dict[str, list[dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path) as f:
                    self._plans = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Failed to load verification plans from %s: %s",
                    self._config_path,
                    exc,
                )

    def get_plan(self, task_type: str) -> VerificationPlan:
        """Get a verification plan for a task type.

        Returns a default minimal plan if no specific plan is registered.
        """
        steps_data = self._plans.get(task_type, self._plans.get("default", []))
        steps: list[VerificationPlanStep] = []
        for step_data in steps_data:
            try:
                steps.append(
                    VerificationPlanStep(
                        level=VerificationLevel(step_data["level"]),
                        method=VerificationMethod(step_data["method"]),
                        description=step_data.get("description", ""),
                        required=step_data.get("required", True),
                        timeout_seconds=step_data.get(
                            "timeout_seconds", 30.0
                        ),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning(
                    "Invalid verification step in plan for %s: %s",
                    task_type,
                    exc,
                )
        return VerificationPlan(task_type=task_type, steps=steps)

    def register_plan(
        self, task_type: str, steps: list[dict[str, Any]]
    ) -> None:
        self._plans[task_type] = steps

    @property
    def task_types(self) -> list[str]:
        return list(self._plans.keys())


# ── Outcome Verification Engine ──────────────────────────────────────────


class OutcomeVerificationEngine:
    """Executes verification plans and produces structured verification records.

    Composes:
    - VerificationPlanRegistry (which plan to run)
    - ProofRuntime (evidence capture, via proof_runtime kwarg)
    - OutcomeLearningLoop (feed verified outcomes, via learning_loop kwarg)
    """

    def __init__(
        self,
        registry: VerificationPlanRegistry | None = None,
        proof_runtime: Any | None = None,
        learning_loop: Any | None = None,
    ) -> None:
        self._registry = registry or VerificationPlanRegistry()
        self._proof_runtime = proof_runtime
        self._learning_loop = learning_loop
        self._verifications: dict[str, OutcomeVerification] = {}

    def verify(
        self,
        work_id: str,
        task_type: str,
        check_fns: dict[VerificationLevel, Callable[[], VerificationStepResult]]
        | None = None,
    ) -> OutcomeVerification:
        """Execute a verification plan for a work item.

        Args:
            work_id: The work item being verified.
            task_type: Task type to look up the verification plan.
            check_fns: Optional override check functions per level.
                       If not provided, plan steps must have check_fn set.

        Returns:
            OutcomeVerification with all results and computed status.
        """
        plan = self._registry.get_plan(task_type)
        check_fns = check_fns or {}

        verification = OutcomeVerification(
            work_id=work_id,
            task_type=task_type,
            plan=plan,
        )

        highest_passed: VerificationLevel | None = None
        all_required_passed = True
        any_passed = False

        for step in plan.steps:
            fn = check_fns.get(step.level, step.check_fn)
            if fn is None:
                result = VerificationStepResult(
                    level=step.level,
                    method=step.method,
                    passed=False,
                    description=step.description,
                    error="No check function provided",
                )
            else:
                try:
                    result = fn()
                except Exception as exc:
                    logger.debug(
                        "Verification step %s failed for %s: %s",
                        step.level.value,
                        work_id,
                        exc,
                    )
                    result = VerificationStepResult(
                        level=step.level,
                        method=step.method,
                        passed=False,
                        description=step.description,
                        error=str(exc),
                    )

            verification.results.append(result)

            if result.passed:
                highest_passed = step.level
                any_passed = True
            elif step.required:
                all_required_passed = False
                break

        verification.highest_level_passed = highest_passed

        if not any_passed:
            verification.status = OutcomeVerificationStatus.FAILED
            verification.confidence = 0.0
        elif all_required_passed and highest_passed == plan.max_level:
            verification.status = OutcomeVerificationStatus.VERIFIED
            verification.confidence = 1.0
            verification.verified_at = datetime.now(timezone.utc)
        elif any_passed:
            verification.status = OutcomeVerificationStatus.PARTIAL
            levels = list(VerificationLevel)
            if highest_passed and plan.max_level:
                passed_idx = levels.index(highest_passed)
                max_idx = levels.index(plan.max_level)
                verification.confidence = (
                    (passed_idx + 1) / (max_idx + 1)
                    if max_idx > 0
                    else 0.0
                )
        else:
            verification.status = OutcomeVerificationStatus.FAILED
            verification.confidence = 0.0

        verification.evidence_summary = self._build_evidence_summary(
            verification
        )

        self._verifications[work_id] = verification

        self._feed_learning_loop(verification)

        logger.info(
            "Verification %s for work_id=%s: status=%s confidence=%.2f highest=%s",
            verification.verification_id,
            work_id,
            verification.status.value,
            verification.confidence,
            highest_passed.value if highest_passed else "none",
        )

        return verification

    def get_verification(self, work_id: str) -> OutcomeVerification | None:
        return self._verifications.get(work_id)

    def make_verify_fn(
        self,
        work_id: str,
        task_type: str,
        check_fns: dict[VerificationLevel, Callable[[], VerificationStepResult]]
        | None = None,
    ) -> Callable[[], bool]:
        """Create a verify_fn compatible with VerificationStrategy.

        Returns a callable that runs verification and returns True only
        if status is VERIFIED (not PARTIAL, not FAILED).
        """

        def _verify() -> bool:
            result = self.verify(work_id, task_type, check_fns)
            return result.status == OutcomeVerificationStatus.VERIFIED

        return _verify

    def _build_evidence_summary(
        self, verification: OutcomeVerification
    ) -> dict[str, Any]:
        passed = [
            r.level.value for r in verification.results if r.passed
        ]
        failed = [
            r.level.value for r in verification.results if not r.passed
        ]
        errors = [
            {"level": r.level.value, "error": r.error}
            for r in verification.results
            if r.error
        ]
        return {
            "levels_passed": passed,
            "levels_failed": failed,
            "errors": errors,
            "total_steps": len(verification.results),
            "steps_passed": len(passed),
        }

    def _feed_learning_loop(
        self, verification: OutcomeVerification
    ) -> None:
        if self._learning_loop is None:
            return
        try:
            record_fn = getattr(
                self._learning_loop, "record_outcome", None
            )
            if record_fn is None:
                return
            from substrate.organism.outcome_learning import (
                OutcomeRecord,
                OutcomeStatus,
            )

            status_map = {
                OutcomeVerificationStatus.VERIFIED: OutcomeStatus.SUCCESS,
                OutcomeVerificationStatus.PARTIAL: OutcomeStatus.PARTIAL,
                OutcomeVerificationStatus.FAILED: OutcomeStatus.FAILURE,
                OutcomeVerificationStatus.UNVERIFIED: OutcomeStatus.SKIPPED,
            }
            record = OutcomeRecord(
                action_type=verification.task_type,
                plan_id=verification.work_id,
                step_id=verification.verification_id,
                description=f"Outcome verification: {verification.status.value}",
                status=status_map.get(
                    verification.status, OutcomeStatus.FAILURE
                ),
                expected_result="VERIFIED",
                actual_result=verification.status.value,
            )
            record_fn(record)
        except Exception as exc:
            logger.debug("Failed to feed learning loop: %s", exc)
