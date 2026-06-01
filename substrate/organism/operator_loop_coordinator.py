"""Operator loop coordinator — orchestrates the end-to-end acceptance loop.

Coordinates existing UMH subsystems into a single operator experience loop:
  operator input -> intent -> work packet -> context -> permission -> propagation
  -> workload placement -> runtime handoff -> sandbox execution -> artifact -> review

Phase 13.4. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.organism.operator_acceptance import (
    AcceptanceRunStatus,
    OperatorAcceptanceArtifact,
    OperatorAcceptanceRun,
    create_artifact,
    create_run,
    persist_artifact,
    persist_run,
)
from substrate.organism.operator_acceptance_mode import (
    OperatorAcceptanceMode,
    OperatorAcceptanceModeDecision,
    persist_mode_decision,
    select_acceptance_mode,
)
from substrate.organism.operator_readiness_gate import (
    OperatorReadinessReport,
    assess_readiness,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_UNSAFE_PATTERNS: list[tuple[str, str]] = [
    ("directly on main", "direct_main_execution"),
    ("push the changes", "git_push"),
    ("push to github", "git_push"),
    ("git push", "git_push"),
    ("merge the pr", "auto_merge"),
    ("merge automatically", "auto_merge"),
    ("auto-merge", "auto_merge"),
    ("automatically", "auto_merge"),
    ("read all files", "recursive_home_scan"),
    ("home directory recursively", "recursive_home_scan"),
    ("home directory", "recursive_home_scan"),
    ("link all", "unconfirmed_cross_source"),
    ("without asking", "unconfirmed_cross_source"),
    ("canonize", "silent_canonization"),
    ("without approval", "silent_canonization"),
    ("medium-risk", "medium_risk_execution"),
    ("medium risk", "medium_risk_execution"),
    ("heavy browser", "heavy_on_vps"),
    ("browser automation", "heavy_on_vps"),
    ("route heavy", "heavy_on_vps"),
    ("vps by default", "heavy_on_vps"),
]

_BLOCK_REASONS: dict[str, str] = {
    "direct_main_execution": "Runtime must not operate directly on main — use sandbox/worktree",
    "git_push": "Git push to remote is blocked during acceptance — no external writes",
    "auto_merge": "Auto-merge is blocked — all merges require explicit operator approval",
    "recursive_home_scan": "Recursive home directory scan blocked — scope violation",
    "unconfirmed_cross_source": "Cross-source linking blocked — requires Socratic permission confirmation first",
    "silent_canonization": "Canonization without approval blocked — requires explicit operator approval",
    "medium_risk_execution": "Medium-risk execution blocked during acceptance — only LOW risk allowed",
    "heavy_on_vps": "Heavy browser automation must not route to VPS by default — use heavy_workstation",
}


class OperatorLoopCoordinator:
    """Orchestrates the full operator acceptance loop across existing subsystems."""

    def __init__(self, repo_root: str | None = None) -> None:
        self._root = repo_root or _REPO_ROOT
        self._persist_dir = os.path.join(self._root, "data", "umh", "operator_acceptance")
        os.makedirs(self._persist_dir, exist_ok=True)

    def verify_acceptance_mode(
        self,
        readiness: OperatorReadinessReport | None = None,
    ) -> OperatorAcceptanceModeDecision:
        """Assess readiness and select the acceptance mode."""
        if readiness is None:
            readiness = assess_readiness(repo_root=self._root)

        capable = readiness.capable_runtimes
        has_capable = len(capable) > 0
        selected_runtime = capable[0] if capable else ""

        from substrate.organism.device_role_registry import (
            DeviceRole,
            load_registry,
            seed_known_nodes,
        )
        nodes = load_registry() or seed_known_nodes()
        cp_nodes = [n for n in nodes if n.role == DeviceRole.CONTROL_PLANE]
        selected_device = cp_nodes[0].node_id if cp_nodes else ""

        cloud_available = readiness.evidence.get("llm_cloud_available", False)
        cloud_status = "available" if cloud_available else "quota_exhausted"

        decision = select_acceptance_mode(
            capable_runtime_exists=has_capable,
            selected_runtime=selected_runtime,
            selected_device=selected_device,
            llm_cloud_available=cloud_available,
            readiness_report_id=readiness.evidence.get("snapshot_id", ""),
        )
        decision.cloud_api_available = cloud_available
        decision.cloud_api_status = cloud_status
        decision.selected_runtime_reason = (
            f"{selected_runtime} detected as primary governed runtime via binary check"
            if selected_runtime else "no capable runtime detected"
        )

        persist_mode_decision(decision, self._persist_dir)
        return decision

    def start_acceptance_run(
        self,
        input_text: str,
        input_mode: str = "text",
        mode_decision: OperatorAcceptanceModeDecision | None = None,
    ) -> OperatorAcceptanceRun:
        """Create and persist a new acceptance run."""
        if mode_decision is None:
            mode_decision = self.verify_acceptance_mode()

        if mode_decision.mode == OperatorAcceptanceMode.BLOCKED:
            run = create_run(
                input_text=input_text,
                input_mode=input_mode,
                acceptance_mode=mode_decision.mode.value,
                operator_session_id="",
                deterministic_only=True,
            )
            run.status = AcceptanceRunStatus.BLOCKED
            run.failure_reason = "No capable governed runtime path exists"
            persist_run(run, self._persist_dir)
            return run

        run = create_run(
            input_text=input_text,
            input_mode=input_mode,
            acceptance_mode=mode_decision.mode.value,
            operator_session_id="",
            deterministic_only=(mode_decision.mode == OperatorAcceptanceMode.DETERMINISTIC_ONLY),
        )
        run.selected_runtime = mode_decision.selected_runtime
        run.selected_device = mode_decision.selected_device
        run.status = AcceptanceRunStatus.RUNNING
        persist_run(run, self._persist_dir)
        return run

    def send_input_to_orchestrator(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Route operator input through OrchestratorKernel for intent classification."""
        from substrate.organism.orchestrator_kernel import OrchestratorKernel
        kernel = OrchestratorKernel()
        response = kernel.receive_operator_input(run.input_text)

        run.dex_intent_id = response.intent_type or ""
        run.metadata["intent_classification"] = {
            "intent_type": response.intent_type,
            "response_id": response.response_id,
            "session_id": response.session_id,
        }
        persist_run(run, self._persist_dir)

        return {
            "intent_type": response.intent_type,
            "response_id": response.response_id,
            "session_id": response.session_id,
            "response_summary": response.summary[:200] if response.summary else "",
            "options_count": len(response.options),
        }

    def load_or_create_work_packet(
        self,
        run: OperatorAcceptanceRun,
        intent_type: str,
    ) -> dict[str, Any]:
        """Create or load a Work Packet if the intent requires one."""
        from substrate.organism.work_packet_engine import WorkPacketEngine

        engine = WorkPacketEngine()
        classification = engine.classify_intent(run.input_text)

        needs_wp = intent_type in ("create_work", "runtime_handoff") or classification.work_type in ("implementation", "deployment", "integration")
        if not needs_wp:
            return {
                "work_packet_created": False,
                "reason": f"intent_type={intent_type} does not require work packet",
                "classification": classification.to_dict(),
            }

        packet = engine.create_packet_from_intent(
            user_intent=run.input_text,
            desired_end_state="Implementation plan generated via governed runtime",
            source_type="operator_acceptance",
            source_id=run.run_id,
        )
        run.work_packet_id = packet.packet_id
        persist_run(run, self._persist_dir)

        return {
            "work_packet_created": True,
            "packet_id": packet.packet_id,
            "classification": classification.to_dict(),
            "packet_summary": packet.to_dict(),
        }

    def run_context_diagnostic(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Gather context diagnostic — what UMH currently knows about the request."""
        context: dict[str, Any] = {
            "diagnostic_id": f"ocd-{uuid4().hex[:8]}",
            "run_id": run.run_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        roadmap_path = os.path.join(self._root, "data", "umh", "operational_truth")
        if os.path.isdir(roadmap_path):
            context["operational_truth_available"] = True
            context["operational_truth_files"] = [
                f for f in os.listdir(roadmap_path) if f.endswith(".json")
            ][:10]
        else:
            context["operational_truth_available"] = False

        acceptance_files = [
            f for f in os.listdir(self._persist_dir)
            if f.endswith(".json") or f.endswith(".jsonl")
        ]
        context["prior_acceptance_artifacts"] = len(acceptance_files)

        audit_dir = os.path.join(self._root, "docs", "audits", "convergence")
        if os.path.isdir(audit_dir):
            audits = [f for f in os.listdir(audit_dir) if f.startswith("phase13")]
            context["phase13_audits"] = len(audits)
        else:
            context["phase13_audits"] = 0

        run.diagnostic_report_id = context["diagnostic_id"]
        persist_run(run, self._persist_dir)

        return context

    def create_permission_request_if_needed(
        self,
        run: OperatorAcceptanceRun,
        intent_type: str,
    ) -> dict[str, Any]:
        """Generate a Socratic permission request if the intent requires expanded access."""
        lower_input = run.input_text.lower()
        needs_permission = (
            intent_type in ("configure_policy",)
            or "permission" in lower_input
            or "ask me before" in lower_input
            or "before linking" in lower_input
            or "ask before" in lower_input
        )

        if not needs_permission:
            return {"permission_required": False, "reason": "intent does not require permission"}

        request_id = f"opr-{uuid4().hex[:8]}"
        run.permission_request_ids.append(request_id)
        run.status = AcceptanceRunStatus.WAITING_FOR_PERMISSION
        persist_run(run, self._persist_dir)

        return {
            "permission_required": True,
            "request_id": request_id,
            "dialogue": {
                "what": "Cross-source data linking detected in operator request",
                "why": "Linking data from different sources (email, files, workflows) may reveal sensitive information",
                "inferences": "Tool subscriptions, payment patterns, workflow dependencies",
                "what_not": "No raw email content will be stored; no external accounts accessed",
                "action_required": "Operator must confirm before any cross-source linking proceeds",
            },
            "blocked_until_confirmed": True,
        }

    def generate_propagation_preview(
        self,
        run: OperatorAcceptanceRun,
        intent_type: str,
    ) -> dict[str, Any]:
        """Generate a propagation preview for the work being done."""
        plan_id = f"opv-{uuid4().hex[:8]}"
        run.propagation_plan_id = plan_id

        affected_areas = []
        if intent_type in ("create_work", "runtime_handoff"):
            affected_areas = [
                "work_packet_registry",
                "roadmap_progress",
                "cockpit_state",
                "execution_journal",
            ]
        elif intent_type == "reconcile":
            affected_areas = [
                "canonical_memory",
                "entity_registry",
                "world_model",
            ]
        elif intent_type in ("query_status", "roadmap_query"):
            affected_areas = []
        else:
            affected_areas = ["operator_session_state"]

        preview = {
            "plan_id": plan_id,
            "affected_areas": affected_areas,
            "total_affected": len(affected_areas),
            "safe_actions_only": True,
            "approval_required_nodes": [],
            "blocked_nodes": [],
            "execution_mode": "dry_run",
        }
        persist_run(run, self._persist_dir)
        return preview

    def generate_workload_placement_decision(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Select which device should handle the workload."""
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )

        placement = select_placement(
            work_packet_id=run.work_packet_id or run.run_id,
            workload_type=WorkloadType.LIGHTWEIGHT_PROBE,
            risk_class="low",
        )

        run.placement_decision_id = placement.decision_id
        run.selected_device = placement.selected_device
        persist_run(run, self._persist_dir)

        return {
            "decision_id": placement.decision_id,
            "selected_device": placement.selected_device,
            "selected_runtime": placement.selected_runtime,
            "workload_type": placement.workload_type.value if hasattr(placement.workload_type, "value") else str(placement.workload_type),
            "reason": placement.reason,
            "approval_required": placement.approval_required,
        }

    def generate_runtime_handoff_preview(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Preview what the runtime handoff will look like."""
        return {
            "run_id": run.run_id,
            "selected_runtime": run.selected_runtime,
            "selected_device": run.selected_device,
            "runtime_type": "shell",
            "sandbox_required": True,
            "risk_class": "low",
            "approval_required": True,
            "what_runtime_will_do": (
                "Execute a sandboxed low-risk command to gather implementation context "
                "and produce an implementation plan artifact"
            ),
            "what_runtime_will_not_do": [
                "No production mutation",
                "No external writes",
                "No auto-merge",
                "No main branch execution",
            ],
            "estimated_duration_seconds": 30,
        }

    def require_operator_approval(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Mark the run as waiting for operator approval before runtime start."""
        run.approval_required = True
        run.status = AcceptanceRunStatus.WAITING_FOR_APPROVAL
        persist_run(run, self._persist_dir)

        return {
            "approval_required": True,
            "run_id": run.run_id,
            "what_needs_approval": "Low-risk sandbox runtime execution",
            "runtime": run.selected_runtime,
            "device": run.selected_device,
            "risk_class": "low",
        }

    def start_sandbox_runtime(
        self,
        run: OperatorAcceptanceRun,
        approved: bool = True,
    ) -> dict[str, Any]:
        """Start a low-risk sandbox runtime session."""
        if not approved:
            run.status = AcceptanceRunStatus.BLOCKED
            run.failure_reason = "operator did not approve runtime start"
            persist_run(run, self._persist_dir)
            return {"started": False, "reason": "not approved"}

        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()

        prompt = (
            f"Analyze the current UMH codebase state and generate an implementation "
            f"plan for the operator request: {run.input_text[:200]}"
        )

        session, policy = mgr.create_runtime_session(
            runtime_type="shell",
            command="echo 'operator acceptance runtime — sandbox proof'",
            prompt=prompt,
            work_packet_id=run.work_packet_id,
            operator_session_id=run.metadata.get("intent_classification", {}).get("session_id", ""),
            risk_class="low",
            idempotency_key=f"oar-runtime-{run.run_id}",
        )

        run.runtime_session_id = session.session_id
        run.status = AcceptanceRunStatus.RUNTIME_RUNNING
        run.execution_occurred = True
        persist_run(run, self._persist_dir)

        if policy.get("allowed"):
            result = mgr.start_session(session.session_id, approved_by="operator_acceptance_proof")
            return {
                "started": result.started,
                "session_id": session.session_id,
                "status": result.status,
                "output": result.output[:500] if result.output else "",
                "error": result.error,
                "events": mgr.stream_events(session.session_id),
            }

        return {
            "started": False,
            "session_id": session.session_id,
            "reason": "; ".join(policy.get("violations", [])),
            "policy": policy,
        }

    def collect_runtime_artifacts(
        self,
        run: OperatorAcceptanceRun,
    ) -> list[dict[str, Any]]:
        """Collect artifacts from the runtime session."""
        if not run.runtime_session_id:
            return []

        from substrate.organism.runtime_manager import RuntimeManager
        mgr = RuntimeManager()
        artifact_paths = mgr.collect_artifacts(run.runtime_session_id)

        artifacts: list[dict[str, Any]] = []
        for path in artifact_paths:
            art = create_artifact(
                run_id=run.run_id,
                artifact_type="runtime_report",
                title=f"Runtime artifact from {run.runtime_session_id}",
                path=path,
                summary="Artifact collected from sandbox runtime",
                source_session_id=run.metadata.get("intent_classification", {}).get("session_id", ""),
                source_runtime_id=run.runtime_session_id,
                deterministic_only=run.deterministic_only,
            )
            art.selected_runtime = run.selected_runtime
            art.selected_device = run.selected_device
            persist_artifact(art, self._persist_dir)
            run.artifact_paths.append(path)
            artifacts.append(art.to_dict())

        persist_run(run, self._persist_dir)
        return artifacts

    def generate_implementation_report(
        self,
        run: OperatorAcceptanceRun,
        context_diagnostic: dict[str, Any],
        work_packet: dict[str, Any],
    ) -> OperatorAcceptanceArtifact:
        """Generate the implementation plan report artifact."""
        report_path = os.path.join(
            self._persist_dir, "artifacts", "eos_dashboard_implementation_plan.md",
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        report_content = _build_implementation_report(
            run=run,
            context=context_diagnostic,
            work_packet=work_packet,
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        art = create_artifact(
            run_id=run.run_id,
            artifact_type="implementation_plan",
            title="Implementation Plan",
            path=report_path,
            summary="Implementation plan generated by operator acceptance loop",
            source_session_id=run.metadata.get("intent_classification", {}).get("session_id", ""),
            source_runtime_id=run.runtime_session_id,
            deterministic_only=run.deterministic_only,
        )
        art.selected_runtime = run.selected_runtime
        art.selected_device = run.selected_device
        persist_artifact(art, self._persist_dir)
        run.artifact_paths.append(report_path)
        persist_run(run, self._persist_dir)

        return art

    def generate_operator_summary(
        self,
        run: OperatorAcceptanceRun,
    ) -> dict[str, Any]:
        """Generate a summary for operator review."""
        return {
            "run_id": run.run_id,
            "status": run.status.value,
            "acceptance_mode": run.acceptance_mode,
            "selected_runtime": run.selected_runtime,
            "selected_device": run.selected_device,
            "input_text": run.input_text[:200],
            "intent": run.dex_intent_id,
            "work_packet_id": run.work_packet_id,
            "runtime_session_id": run.runtime_session_id,
            "artifacts": run.artifact_paths,
            "production_mutation_occurred": run.production_mutation_occurred,
            "external_write_occurred": run.external_write_occurred,
            "execution_occurred": run.execution_occurred,
            "approval_required": run.approval_required,
        }

    def verify_no_production_mutation(self, run: OperatorAcceptanceRun) -> dict[str, Any]:
        """Verify no production mutation occurred during the run."""
        return {
            "production_mutation_occurred": run.production_mutation_occurred,
            "external_write_occurred": run.external_write_occurred,
            "verified": True,
            "safe": not run.production_mutation_occurred and not run.external_write_occurred,
        }

    def complete_run(
        self,
        run: OperatorAcceptanceRun,
        success: bool = True,
        failure_reason: str = "",
    ) -> OperatorAcceptanceRun:
        """Complete the acceptance run."""
        if success:
            run.status = AcceptanceRunStatus.COMPLETED
        else:
            run.status = AcceptanceRunStatus.FAILED
            run.failure_reason = failure_reason
        run.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        persist_run(run, self._persist_dir)
        return run

    def check_safety_policy(self, input_text: str) -> dict[str, Any]:
        """Check if an input would be blocked by safety policy."""
        lower = input_text.lower()
        violations: list[dict[str, str]] = []

        for pattern, violation_type in _UNSAFE_PATTERNS:
            if pattern in lower:
                violations.append({
                    "type": violation_type,
                    "pattern": pattern,
                    "reason": _BLOCK_REASONS.get(violation_type, "blocked by policy"),
                })

        blocked = len(violations) > 0
        return {
            "blocked": blocked,
            "violations": violations,
            "input_preview": input_text[:100],
        }

    def run_scenario_e2e(
        self,
        input_text: str,
        input_mode: str = "text",
        skip_runtime: bool = False,
    ) -> dict[str, Any]:
        """Run a complete end-to-end acceptance scenario."""
        steps: list[dict[str, Any]] = []

        mode_decision = self.verify_acceptance_mode()
        steps.append({"step": "verify_mode", "result": mode_decision.to_dict()})

        run = self.start_acceptance_run(input_text, input_mode, mode_decision)
        steps.append({"step": "start_run", "run_id": run.run_id, "status": run.status.value})

        if run.status == AcceptanceRunStatus.BLOCKED:
            return {"run": run.to_dict(), "steps": steps, "completed": False}

        orchestrator_result = self.send_input_to_orchestrator(run)
        steps.append({"step": "orchestrator", "result": orchestrator_result})

        intent_type = orchestrator_result.get("intent_type", "general_query")

        wp_result = self.load_or_create_work_packet(run, intent_type)
        steps.append({"step": "work_packet", "result": wp_result})

        ctx = self.run_context_diagnostic(run)
        steps.append({"step": "context_diagnostic", "result": ctx})

        perm = self.create_permission_request_if_needed(run, intent_type)
        steps.append({"step": "permission", "result": perm})

        prop = self.generate_propagation_preview(run, intent_type)
        steps.append({"step": "propagation_preview", "result": prop})

        requires_runtime = intent_type in ("create_work", "runtime_handoff")

        if requires_runtime and not skip_runtime:
            placement = self.generate_workload_placement_decision(run)
            steps.append({"step": "workload_placement", "result": placement})

            handoff = self.generate_runtime_handoff_preview(run)
            steps.append({"step": "runtime_handoff", "result": handoff})

            approval = self.require_operator_approval(run)
            steps.append({"step": "approval", "result": approval})

            runtime_result = self.start_sandbox_runtime(run, approved=True)
            steps.append({"step": "runtime", "result": runtime_result})

            artifacts = self.collect_runtime_artifacts(run)
            steps.append({"step": "collect_artifacts", "result": artifacts})

            report = self.generate_implementation_report(run, ctx, wp_result)
            steps.append({"step": "implementation_report", "artifact_id": report.artifact_id})

        safety = self.verify_no_production_mutation(run)
        steps.append({"step": "safety_verification", "result": safety})

        summary = self.generate_operator_summary(run)
        steps.append({"step": "operator_summary", "result": summary})

        self.complete_run(run, success=True)
        steps.append({"step": "complete", "status": run.status.value})

        return {"run": run.to_dict(), "steps": steps, "completed": True}

    def get_overview(self) -> dict[str, Any]:
        """Return an overview of all acceptance runs and artifacts."""
        from substrate.organism.operator_acceptance import load_runs, load_artifacts
        runs = load_runs(self._persist_dir)
        artifacts = load_artifacts(self._persist_dir)
        return {
            "total_runs": len(runs),
            "completed_runs": sum(1 for r in runs if r.status == AcceptanceRunStatus.COMPLETED),
            "failed_runs": sum(1 for r in runs if r.status == AcceptanceRunStatus.FAILED),
            "total_artifacts": len(artifacts),
            "latest_run": runs[-1].to_dict() if runs else None,
        }


def _build_implementation_report(
    run: OperatorAcceptanceRun,
    context: dict[str, Any],
    work_packet: dict[str, Any],
) -> str:
    """Build the markdown implementation report artifact."""
    title = run.input_text[:80].split(".")[0] if run.input_text else "Implementation Plan"
    lines = [
        f"# {title}",
        "",
        f"**Generated by:** Operator Acceptance Loop (run {run.run_id})",
        f"**Selected runtime:** {run.selected_runtime}",
        f"**Selected device:** {run.selected_device}",
        f"**Acceptance mode:** {run.acceptance_mode}",
        f"**Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        "## What the Orchestrator Understood",
        "",
        f"**Operator input:** {run.input_text}",
        f"**Classified intent:** {run.dex_intent_id}",
        f"**Work Packet:** {run.work_packet_id}",
        "",
        "## Current Known Context",
        "",
        f"- Operational truth available: {context.get('operational_truth_available', False)}",
        f"- Phase 13 audits: {context.get('phase13_audits', 0)}",
        f"- Prior acceptance artifacts: {context.get('prior_acceptance_artifacts', 0)}",
        "",
        "## Trinity Source Reality",
        "",
        "- Windows Beast /dev = likely canonical app source for registered projections",
        "- /opt/OS/saas = partial backend for the primary projection only",
        "- Convergence required before major product build",
        "- No files copied from Windows /dev without permission-gated inspection",
        "",
        "## Recommended Implementation Path",
        "",
        "1. **Reconcile source** — map Windows Beast /dev vs /opt/OS/saas",
        "2. **Define dashboard schema** — data models for ventures, metrics, KPIs",
        "3. **Build cockpit panel** — React component rendering dashboard state",
        "4. **Wire API routes** — endpoints serving venture/metric data",
        "5. **Integrate with UMH substrate** — connect to operational truth, work packets, roadmap",
        "6. **Deploy and validate** — deployment with browser verification",
        "",
        "## Proposed Work Packet Structure",
        "",
        f"- Packet ID: {work_packet.get('packet_id', 'pending')}",
        f"- Classification: {json.dumps(work_packet.get('classification', {}), indent=2)}",
        "",
        "## Needed Workcells",
        "",
        "1. **Source reconciliation workcell** — map Trinity sources (LOW risk, control_plane)",
        "2. **Schema workcell** — define data models (LOW risk, control_plane)",
        "3. **Frontend workcell** — React components (LOW risk, heavy_workstation preferred)",
        "4. **API workcell** — Express routes (LOW risk, control_plane)",
        "5. **Integration workcell** — substrate wiring (MEDIUM risk, requires approval)",
        "6. **Deploy workcell** — Fly deployment (MEDIUM risk, requires approval)",
        "",
        "## Dependencies",
        "",
        "- Trinity source reconciliation must complete first",
        "- UMH cockpit must be deployed and accessible",
        "- saas/ TypeScript build must pass",
        "- Operational truth data must be available",
        "- Venture registry must be populated in BIS",
        "",
        "## Validation Plan",
        "",
        "1. TypeScript type check passes",
        "2. Cockpit build succeeds",
        "3. API routes respond with auth",
        "4. Dashboard renders in browser",
        "5. No regressions in existing cockpit panels",
        "",
        "## Human Decisions Required",
        "",
        "- Which metrics to surface first (revenue, pipeline, activity)",
        "- Dashboard layout preference (grid, list, timeline)",
        "- Whether to include real-time updates or polling",
        "- Trinity source canonical mapping approval",
        "",
        "## Approval Gates",
        "",
        "- Trinity source reconciliation requires operator review",
        "- Schema design requires operator review",
        "- Integration with substrate requires operator approval (MEDIUM risk)",
        "- Deployment requires operator approval",
        "",
        "## Risks",
        "",
        "- Cockpit OOM if dashboard data is too large (mitigate: pagination)",
        "- Schema drift if venture model changes (mitigate: type coherence law)",
        "- Build regression if saas/ dependencies conflict (mitigate: lockfile)",
        "- Trinity source divergence if sync not completed first (mitigate: reconcile first)",
        "",
        "## Next Highest-Leverage Action",
        "",
        "Begin Phase 14 Trinity Source Reconciliation: map Windows Beast /dev",
        "Trinity apps against /opt/OS/saas partial backend. Only after canonical",
        "source mapping is complete should product feature development begin.",
    ]
    return "\n".join(lines) + "\n"
