"""Review Package Builder — deterministic proof assembly.

Assembles EngineeringProofPackage from execution session artifacts.
Computes operator_recommendation via deterministic rules (no LLM).

Phase 23. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.meta_ide.engineering_execution import (
    EngineeringArtifact,
    EngineeringExecutionSession,
    EngineeringExecutionStatus,
    EngineeringProofPackage,
    OperatorRecommendation,
)

logger = logging.getLogger(__name__)

_HIGH_RISK_TASK_TYPES = frozenset(
    {
        "deployment",
        "migration",
        "schema_change",
        "security",
        "infrastructure",
    }
)


class ReviewPackageBuilder:
    """Assembles proof packages from execution sessions."""

    def build_package(self, session: EngineeringExecutionSession) -> EngineeringProofPackage:
        """Build a complete proof package from session artifacts."""
        diff_summary = self._build_diff_summary(session)
        validation_results = self._collect_validation_results(session)
        risk_summary = self._build_risk_summary(session)
        browser_verification = self._collect_browser_verification(session)

        package = EngineeringProofPackage(
            session_id=session.session_id,
            plan_id=session.plan_id,
            artifacts=list(session.artifacts),
            validation_results=validation_results,
            risk_summary=risk_summary,
            diff_summary=diff_summary,
            trace_ids=list(session.execution_trace_ids),
            browser_verification=browser_verification,
        )

        recommendation, reasoning = self.compute_recommendation(package, session)
        package.operator_recommendation = recommendation
        package.recommendation_reasoning = reasoning

        return package

    def compute_recommendation(
        self,
        package: EngineeringProofPackage,
        session: EngineeringExecutionSession | None = None,
    ) -> tuple[OperatorRecommendation, list[str]]:
        """Deterministic pre-score based on evidence."""
        reasoning: list[str] = []

        has_errors = bool(session and session.errors)
        has_failed_tasks = False
        has_warnings = False
        has_high_risk = False
        all_validations_pass = True

        if session is not None:
            for task_id, result in session.task_results.items():
                if task_id.startswith("__") and task_id.endswith("__"):
                    if task_id == "__validation__" and result.get("failed", 0) > 0:
                        all_validations_pass = False
                        reasoning.append(f"Validation: {result['failed']} checks failed")
                    continue
                if not result.get("success", False):
                    has_failed_tasks = True
                    reasoning.append(f"Task {task_id} failed: {result.get('outcome', 'unknown')}")

        for risk in package.risk_summary:
            level = risk.get("level", "low")
            if level in ("high", "critical"):
                has_high_risk = True
                reasoning.append(f"High-risk operation: {risk.get('description', 'unknown')}")

        if not package.artifacts:
            reasoning.append("No artifacts produced")
            has_warnings = True

        for vr in package.validation_results:
            if not vr.get("passed", True):
                all_validations_pass = False
                reasoning.append(f"Validation failed: {vr.get('artifact_id', 'unknown')}")

        browser_v = package.browser_verification
        browser_verification_failed = (
            browser_v.get("required", False) and not browser_v.get("verified", False)
        )
        if browser_verification_failed:
            passing = browser_v.get("consecutive_passing", 0)
            required = browser_v.get("required_passes", 3)
            reasoning.append(
                f"Browser verification incomplete: {passing}/{required} consecutive passes"
            )

        if has_errors or has_failed_tasks:
            reasoning.insert(0, "REJECT: errors or failed tasks detected")
            return OperatorRecommendation.REJECT, reasoning

        if browser_verification_failed:
            reasoning.insert(0, "NEEDS_REVIEW: browser verification not yet passed")
            return OperatorRecommendation.NEEDS_REVIEW, reasoning

        if not all_validations_pass:
            reasoning.insert(0, "NEEDS_REVIEW: validation failures detected")
            return OperatorRecommendation.NEEDS_REVIEW, reasoning

        if has_high_risk:
            reasoning.insert(0, "APPROVE_WITH_NOTES: high-risk operations detected")
            return OperatorRecommendation.APPROVE_WITH_NOTES, reasoning

        if has_warnings:
            reasoning.insert(0, "APPROVE_WITH_NOTES: minor warnings present")
            return OperatorRecommendation.APPROVE_WITH_NOTES, reasoning

        reasoning.insert(
            0,
            "APPROVE: all tasks succeeded, validations passed, no high-risk ops",
        )
        return OperatorRecommendation.APPROVE, reasoning

    def _build_diff_summary(self, session: EngineeringExecutionSession) -> dict[str, Any]:
        """Aggregate diff summary from all artifacts."""
        files_changed: list[str] = []
        by_type: dict[str, int] = {}

        for artifact in session.artifacts:
            if artifact.file_path:
                files_changed.append(artifact.file_path)
            art_type = (
                artifact.artifact_type.value
                if hasattr(artifact.artifact_type, "value")
                else str(artifact.artifact_type)
            )
            by_type[art_type] = by_type.get(art_type, 0) + 1

        return {
            "total_files": len(files_changed),
            "files": files_changed,
            "by_type": by_type,
        }

    def _collect_validation_results(
        self, session: EngineeringExecutionSession
    ) -> list[dict[str, Any]]:
        """Collect validation results from session task_results."""
        validation = session.task_results.get("__validation__")
        if validation is None:
            return []
        return validation.get("details", [])

    def _collect_browser_verification(
        self, session: EngineeringExecutionSession
    ) -> dict[str, Any]:
        """Collect browser verification evidence from session."""
        bv = session.task_results.get("__browser_verification__")
        if bv is None:
            return {}
        return bv

    def _build_risk_summary(self, session: EngineeringExecutionSession) -> list[dict[str, Any]]:
        """Build risk summary from task results and artifacts."""
        risks: list[dict[str, Any]] = []

        for task_id, result in session.task_results.items():
            if task_id.startswith("__") and task_id.endswith("__"):
                continue

            task_meta = result.get("metadata", {})
            if not result.get("success", False):
                risks.append(
                    {
                        "task_id": task_id,
                        "level": "high",
                        "description": f"Task failed: {result.get('outcome', 'unknown')}",
                    }
                )

        for artifact in session.artifacts:
            meta = artifact.metadata or {}
            if meta.get("risk_class") in ("high", "critical"):
                risks.append(
                    {
                        "artifact_id": artifact.artifact_id,
                        "level": meta["risk_class"],
                        "description": f"High-risk artifact: {artifact.file_path}",
                    }
                )

        return risks
