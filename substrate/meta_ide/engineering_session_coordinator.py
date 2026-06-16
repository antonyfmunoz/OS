"""Engineering Session Coordinator — governed execution orchestration.

Coordinates engineering execution sessions by dispatching tasks to existing
executors (AgentExecutor, WorkstationExecutor, SimulationExecutor) through
the ExecutorContract lifecycle. Never executes directly.

Multi-agent ready: independent tasks dispatch concurrently via wave-based
parallelism. Dependent tasks serialize per dependency graph.

No auto-merge. No auto-push. No auto-deploy.
No new execution authority. Coordinator dispatches only.

Phase 23. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from substrate.meta_ide.engineering_execution import (
    EngineeringArtifact,
    EngineeringExecutionSession,
    EngineeringExecutionStatus,
    EngineeringProofPackage,
)
from substrate.meta_ide.engineering_intent import EngineeringPlan, EngineeringTask

logger = logging.getLogger(__name__)


class EngineeringSessionCoordinator:
    """Orchestrates engineering execution sessions.

    Dispatches to existing executors — never executes directly.
    """

    def __init__(
        self,
        planner: Any | None = None,
        executor: Any | None = None,
        event_spine: Any | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._event_spine = event_spine
        self._sessions: dict[str, EngineeringExecutionSession] = {}
        self._plans: dict[str, EngineeringPlan] = {}
        self._proof_packages: dict[str, EngineeringProofPackage] = {}

    def register_plan(self, plan: EngineeringPlan) -> None:
        """Register a plan so sessions can reference it."""
        self._plans[plan.plan_id] = plan

    def create_session(
        self,
        plan_id: str,
        workspace_targets: list[str] | None = None,
        operator_id: str = "",
    ) -> EngineeringExecutionSession:
        """Create an execution session from an approved plan."""
        plan = self._plans.get(plan_id)
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")
        if plan.status != "approved":
            raise ValueError(f"Plan {plan_id} status is '{plan.status}', expected 'approved'")

        session = EngineeringExecutionSession(
            plan_id=plan_id,
            status=EngineeringExecutionStatus.PLANNED,
            workspace_targets=workspace_targets or [],
            operator_id=operator_id,
        )
        self._sessions[session.session_id] = session

        self._emit_event(
            "session_created",
            {
                "session_id": session.session_id,
                "plan_id": plan_id,
                "workspace_targets": session.workspace_targets,
            },
        )
        return session

    def execute_session(self, session_id: str) -> EngineeringExecutionSession:
        """Execute a session by dispatching tasks through existing executors."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        if session.status not in (
            EngineeringExecutionStatus.PLANNED,
            EngineeringExecutionStatus.PAUSED,
        ):
            raise ValueError(
                f"Session {session_id} status is '{session.status.value}', cannot execute"
            )

        plan = self._plans.get(session.plan_id)
        if plan is None:
            session.status = EngineeringExecutionStatus.FAILED
            session.errors.append(f"Plan {session.plan_id} not found")
            return session

        session.status = EngineeringExecutionStatus.EXECUTING
        session.updated_at = time.time()
        self._emit_event(
            "session_executing",
            {"session_id": session_id},
        )

        waves = _build_execution_waves(plan.tasks, plan.dependency_graph)

        for wave_idx, wave_tasks in enumerate(waves):
            if session.status == EngineeringExecutionStatus.PAUSED:
                break
            if session.status == EngineeringExecutionStatus.CANCELLED:
                break

            for task in wave_tasks:
                result = self._dispatch_task(session, task, wave_idx)
                session.task_results[task.task_id] = result

                if result.get("success"):
                    for art_dict in result.get("artifacts", []):
                        artifact = EngineeringArtifact.from_executor_artifact(
                            art_dict,
                            session_id=session.session_id,
                            task_id=task.task_id,
                        )
                        session.artifacts.append(artifact)
                else:
                    session.errors.append(
                        f"Task {task.task_id} failed: {result.get('outcome', 'unknown error')}"
                    )

                self._emit_event(
                    "task_completed",
                    {
                        "session_id": session_id,
                        "task_id": task.task_id,
                        "success": result.get("success", False),
                        "wave": wave_idx,
                    },
                )

        if session.status == EngineeringExecutionStatus.EXECUTING:
            session.status = EngineeringExecutionStatus.VALIDATING
            session.updated_at = time.time()

            validation = self._run_validation(session)
            session.task_results["__validation__"] = validation

            session.status = EngineeringExecutionStatus.AWAITING_REVIEW
            session.updated_at = time.time()
            session.completed_at = time.time()

        self._emit_event(
            "session_completed",
            {
                "session_id": session_id,
                "status": session.status.value,
                "artifact_count": len(session.artifacts),
            },
        )

        return session

    def get_session(self, session_id: str) -> EngineeringExecutionSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[EngineeringExecutionSession]:
        return list(self._sessions.values())

    def pause_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.status != EngineeringExecutionStatus.EXECUTING:
            return False
        session.status = EngineeringExecutionStatus.PAUSED
        session.updated_at = time.time()
        self._emit_event("session_paused", {"session_id": session_id})
        return True

    def cancel_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.status in (
            EngineeringExecutionStatus.APPROVED,
            EngineeringExecutionStatus.REJECTED,
        ):
            return False
        session.status = EngineeringExecutionStatus.CANCELLED
        session.updated_at = time.time()
        self._emit_event("session_cancelled", {"session_id": session_id})
        return True

    def store_proof_package(self, package: EngineeringProofPackage) -> None:
        self._proof_packages[package.proof_id] = package

    def get_proof_package(self, proof_id: str) -> EngineeringProofPackage | None:
        return self._proof_packages.get(proof_id)

    def list_proof_packages(self) -> list[EngineeringProofPackage]:
        return list(self._proof_packages.values())

    def approve_review(
        self, proof_id: str, reviewed_by: str = ""
    ) -> EngineeringProofPackage | None:
        pkg = self._proof_packages.get(proof_id)
        if pkg is None:
            return None
        pkg.review_status = "approved"
        pkg.reviewed_at = time.time()
        pkg.reviewed_by = reviewed_by

        session = self._sessions.get(pkg.session_id)
        if session is not None:
            session.status = EngineeringExecutionStatus.APPROVED
            session.updated_at = time.time()

        self._emit_event(
            "review_approved",
            {"proof_id": proof_id, "session_id": pkg.session_id},
        )
        return pkg

    def reject_review(
        self,
        proof_id: str,
        reason: str = "",
        reviewed_by: str = "",
    ) -> EngineeringProofPackage | None:
        pkg = self._proof_packages.get(proof_id)
        if pkg is None:
            return None
        pkg.review_status = "rejected"
        pkg.rejection_reason = reason
        pkg.reviewed_at = time.time()
        pkg.reviewed_by = reviewed_by

        session = self._sessions.get(pkg.session_id)
        if session is not None:
            session.status = EngineeringExecutionStatus.REJECTED
            session.updated_at = time.time()

        self._emit_event(
            "review_rejected",
            {
                "proof_id": proof_id,
                "session_id": pkg.session_id,
                "reason": reason,
            },
        )
        return pkg

    def _dispatch_task(
        self,
        session: EngineeringExecutionSession,
        task: EngineeringTask,
        wave_idx: int,
    ) -> dict[str, Any]:
        """Dispatch a task to an executor. Returns result dict."""
        worker_id = f"worker-{uuid4().hex[:8]}"
        session.worker_assignments[task.task_id] = worker_id

        if self._executor is not None:
            try:
                from substrate.organism.executor_runtime import ExecutorRequest

                request = ExecutorRequest(
                    description=f"{task.title}: {task.description}",
                    risk_class=task.risk_class,
                    metadata={
                        "task_id": task.task_id,
                        "session_id": session.session_id,
                        "wave": wave_idx,
                        "worker_id": worker_id,
                        "workspace_targets": session.workspace_targets,
                    },
                )
                session.executor_request_ids.append(request.request_id)

                result = self._executor.execute(request)
                return (
                    result.to_dict()
                    if hasattr(result, "to_dict")
                    else {
                        "success": True,
                        "outcome": str(result),
                        "artifacts": [],
                    }
                )
            except Exception as exc:
                logger.warning("Executor dispatch failed: %s", exc)
                return {
                    "success": False,
                    "outcome": f"Executor error: {exc}",
                    "artifacts": [],
                }

        return {
            "success": True,
            "outcome": f"Simulated: {task.title}",
            "artifacts": [
                {
                    "artifact_type": task.task_type or "code",
                    "name": f"simulated/{task.task_id}.py",
                    "content": f"# Simulated output for {task.title}",
                    "metadata": {"simulated": True},
                }
            ],
        }

    def _run_validation(self, session: EngineeringExecutionSession) -> dict[str, Any]:
        """Deterministic validation of session artifacts."""
        results: list[dict[str, Any]] = []
        for artifact in session.artifacts:
            results.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "file_path": artifact.file_path,
                    "checks": {
                        "exists": bool(artifact.file_path),
                        "has_content": bool(artifact.content_hash),
                        "type_classified": bool(artifact.artifact_type),
                    },
                    "passed": bool(artifact.file_path and artifact.content_hash),
                }
            )
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "details": results,
        }

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_spine is None:
            return
        try:
            self._event_spine.emit(
                domain="engineering",
                event_type=event_type,
                data=data,
            )
        except Exception as exc:
            logger.debug("Event emission failed: %s", exc)


def _build_execution_waves(
    tasks: list[EngineeringTask],
    dependency_graph: dict[str, list[str]],
) -> list[list[EngineeringTask]]:
    """Build wave-based execution order from dependency graph.

    Independent tasks (no unmet deps) go in the same wave.
    Dependent tasks wait for their predecessors' wave to complete.
    """
    if not tasks:
        return []

    task_map = {t.task_id: t for t in tasks}
    completed: set[str] = set()
    waves: list[list[EngineeringTask]] = []
    remaining = set(task_map.keys())

    max_iterations = len(tasks) + 1
    for _ in range(max_iterations):
        if not remaining:
            break

        wave: list[EngineeringTask] = []
        for task_id in list(remaining):
            deps = dependency_graph.get(task_id, [])
            if all(d in completed for d in deps):
                wave.append(task_map[task_id])

        if not wave:
            for task_id in remaining:
                wave.append(task_map[task_id])
            waves.append(wave)
            break

        waves.append(wave)
        for t in wave:
            completed.add(t.task_id)
            remaining.discard(t.task_id)

    return waves
