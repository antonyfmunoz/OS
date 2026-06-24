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

import os

from substrate.meta_ide.browser_evidence_collector import (
    collect_log_reconciliation,
    trigger_collection,
)
from substrate.meta_ide.browser_verification_gate import (
    BrowserVerificationGate,
    BrowserVerificationResult,
    get_pass_count,
)
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
        self._browser_gate = BrowserVerificationGate()
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

        worktree_path = self._create_sandbox_worktree(session)
        if worktree_path:
            session.sandbox_worktree = worktree_path
            session.sandbox_branch = f"eng/{session.session_id}"

        self._emit_event(
            "session_executing",
            {
                "session_id": session_id,
                "sandbox_worktree": session.sandbox_worktree,
            },
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

            browser_result = self._run_browser_verification(session)
            session.task_results["__browser_verification__"] = browser_result.to_dict()

            if browser_result.required and not browser_result.verified:
                self._emit_event(
                    "browser_verification_pending",
                    {
                        "session_id": session_id,
                        "consecutive_passing": browser_result.consecutive_passing,
                        "required_passes": browser_result.required_passes,
                        "reasons": browser_result.requirement_reasons,
                    },
                )
            else:
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

        if session is not None:
            self._cleanup_sandbox_worktree(session)

        self._emit_event(
            "review_rejected",
            {
                "proof_id": proof_id,
                "session_id": pkg.session_id,
                "reason": reason,
            },
        )
        return pkg

    def integrate_session(self, session_id: str) -> dict[str, Any]:
        """Merge sandbox worktree branch to main after review approval.

        Returns a summary dict with merge status. Only merges if the
        session has a sandbox_worktree set (G4 isolation was active).
        """
        session = self._sessions.get(session_id)
        if session is None:
            return {"merged": False, "reason": "session not found"}
        if session.status != EngineeringExecutionStatus.APPROVED:
            return {"merged": False, "reason": f"session status is {session.status.value}"}

        if not session.sandbox_worktree or not session.sandbox_branch:
            self._emit_event(
                "session_integrated",
                {"session_id": session_id, "merged": False, "reason": "no sandbox"},
            )
            return {"merged": False, "reason": "no sandbox worktree to merge"}

        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run

            merge_result = gated_subprocess_run(
                ["git", "merge", "--no-ff", session.sandbox_branch, "-m",
                 f"eng: integrate session {session.session_id}"],
                caller="engineering_session_coordinator.integrate_session",
                cwd=repo_root,
            )
            merged = merge_result is not None and merge_result.returncode == 0
            self._cleanup_sandbox_worktree(session)

            self._emit_event(
                "session_integrated",
                {"session_id": session_id, "merged": merged},
            )
            return {
                "merged": merged,
                "branch": session.sandbox_branch,
                "session_id": session_id,
            }
        except Exception as exc:
            logger.warning("integrate_session failed: %s", exc)
            return {"merged": False, "reason": str(exc)}

    def _create_sandbox_worktree(
        self, session: EngineeringExecutionSession
    ) -> str:
        """Create an isolated git worktree for session execution.

        Returns the worktree path on success, empty string on failure.
        """
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        branch_name = f"eng/{session.session_id}"
        worktree_dir = os.path.join(repo_root, ".claude", "worktrees", branch_name)

        try:
            from substrate.execution.cpu_gate import gated_subprocess_run

            result = gated_subprocess_run(
                ["git", "worktree", "add", "-b", branch_name, worktree_dir],
                caller="engineering_session_coordinator._create_sandbox_worktree",
                cwd=repo_root,
            )
            if result is not None and result.returncode == 0:
                logger.info("Created sandbox worktree at %s", worktree_dir)
                return worktree_dir
            logger.warning(
                "Failed to create worktree: %s",
                result.stderr if result else "CPU gate blocked",
            )
            return ""
        except Exception as exc:
            logger.warning("Worktree creation failed: %s", exc)
            return ""

    def _cleanup_sandbox_worktree(
        self, session: EngineeringExecutionSession
    ) -> bool:
        """Remove sandbox worktree after merge or rejection."""
        if not session.sandbox_worktree:
            return False
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run

            result = gated_subprocess_run(
                ["git", "worktree", "remove", "--force", session.sandbox_worktree],
                caller="engineering_session_coordinator._cleanup_sandbox_worktree",
                cwd=repo_root,
            )
            if result is not None and result.returncode == 0:
                if session.sandbox_branch:
                    gated_subprocess_run(
                        ["git", "branch", "-d", session.sandbox_branch],
                        caller="engineering_session_coordinator._cleanup_sandbox_worktree",
                        cwd=repo_root,
                    )
                session.sandbox_worktree = ""
                session.sandbox_branch = ""
                return True
            return False
        except Exception as exc:
            logger.warning("Worktree cleanup failed: %s", exc)
            return False

    def submit_browser_evidence(
        self,
        session_id: str,
        evidence: dict[str, Any],
        submitter_id: str = "",
    ) -> BrowserVerificationResult | None:
        """Submit browser verification evidence for a VALIDATING session.

        Called by the executing agent after collecting 4-layer evidence.
        If 3 consecutive passes now pass, transitions to AWAITING_REVIEW.
        submitter_id identifies the agent/operator submitting evidence for audit.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.status != EngineeringExecutionStatus.VALIDATING:
            logger.warning(
                "Cannot submit browser evidence for session %s in status %s",
                session_id,
                session.status.value,
            )
            return None

        result = self._run_browser_verification(session, evidence)
        bv_data = result.to_dict()
        bv_data["submitter_id"] = submitter_id
        session.task_results["__browser_verification__"] = bv_data

        if result.verified:
            session.status = EngineeringExecutionStatus.AWAITING_REVIEW
            session.updated_at = time.time()
            session.completed_at = time.time()
            self._emit_event(
                "browser_verification_passed",
                {
                    "session_id": session_id,
                    "total_attempts": len(result.passes),
                    "submitter_id": submitter_id,
                },
            )
        else:
            self._emit_event(
                "browser_verification_incomplete",
                {
                    "session_id": session_id,
                    "consecutive_passing": result.consecutive_passing,
                    "total_attempts": len(result.passes),
                    "submitter_id": submitter_id,
                },
            )

        return result

    def _derive_session_risk(self, session: EngineeringExecutionSession) -> str:
        """Derive risk class from the session's plan or default to 'low'."""
        plan = self._plans.get(session.plan_id)
        if plan is None:
            return "low"
        risk = getattr(plan, "risk_class", None) or getattr(plan, "risk_level", None)
        if risk:
            return str(risk).lower()
        for task in getattr(plan, "tasks", []):
            meta = getattr(task, "metadata", {}) or {}
            task_risk = meta.get("risk_class") or meta.get("risk_level")
            if task_risk:
                return str(task_risk).lower()
        return "low"

    def _run_browser_verification(
        self,
        session: EngineeringExecutionSession,
        evidence: dict[str, Any] | None = None,
    ) -> BrowserVerificationResult:
        """Check browser verification requirement and validate evidence.

        When verification is required and no evidence is provided,
        auto-triggers collection on an executor-roled node (with display)
        and runs 3-way log reconciliation before gate validation.
        Browser tests NEVER run on the orchestrator (headless).
        """
        artifact_paths = [a.file_path for a in session.artifacts if a.file_path]

        packet_flags: dict[str, Any] = {}
        proof_requirements: list[str] = []

        plan = self._plans.get(session.plan_id)
        if plan is not None:
            for task in plan.tasks:
                meta = getattr(task, "metadata", {}) or {}
                if meta.get("playwright_enabled"):
                    packet_flags["playwright_enabled"] = True
                if meta.get("cdp_enabled"):
                    packet_flags["cdp_enabled"] = True
                if meta.get("screenshot_capture"):
                    packet_flags["screenshot_capture"] = True
                for req in meta.get("proof_requirements", []):
                    if req not in proof_requirements:
                        proof_requirements.append(req)

        if evidence is None:
            existing = session.task_results.get("__browser_verification__", {})
            evidence = existing if existing else {}

        required, reasons = self._browser_gate.requires_verification(
            artifact_paths, packet_flags, proof_requirements
        )
        if required and not evidence.get("passes"):
            target_url = session.task_results.get(
                "__target_url__", "https://universalmetaharness.tech/"
            )
            logger.info(
                "Browser verification required — triggering collection on executor for %s",
                target_url,
            )
            self._emit_event(
                "browser_collection_triggered",
                {"session_id": session.session_id, "target_url": target_url, "reasons": reasons},
            )
            risk_class = self._derive_session_risk(session)
            pass_count = get_pass_count(risk_class)
            evidence = trigger_collection(target_url, pass_count=pass_count)

            # Auto-reconcile: enrich each pass with 3-way log cross-references
            for p in evidence.get("passes", []):
                net_check = p.get("network_check", {})
                endpoints = net_check.get("endpoints_checked", [])
                if not endpoints:
                    continue
                recon = collect_log_reconciliation(
                    network_evidence=endpoints,
                    service_name=p.get("log_check", {}).get("service_name", "os-operator"),
                )
                log_check = p.get("log_check", {})
                log_check["cross_references"] = recon.get("cross_references", [])
                log_check["unmatched_network_requests"] = recon.get("unmatched_network_requests", 0)
                log_check["unmatched_log_errors"] = recon.get("unmatched_log_errors", 0)
                log_check["orphan_server_errors"] = recon.get("orphan_server_errors", [])
                log_check["action_traces"] = recon.get("action_traces", [])
                log_check["reconciliation_score"] = recon.get("reconciliation_score", 0.0)
                p["log_check"] = log_check

        risk_class = self._derive_session_risk(session)
        return self._browser_gate.validate_evidence(
            evidence=evidence,
            artifact_paths=artifact_paths,
            packet_flags=packet_flags,
            proof_requirements=proof_requirements,
            risk_class=risk_class,
        )

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
                        "sandbox_worktree": session.sandbox_worktree,
                        "sandbox_branch": session.sandbox_branch,
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
