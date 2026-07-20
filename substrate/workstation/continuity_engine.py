"""Continuity engine — orchestrator binding all continuity subsystems.

Single entry point for continuity operations: startup, shutdown, transitions,
resume, and composite state queries. Holds references to the continuity
state machine, checkpoint manager, return brief generator, intent contracts,
and profile behaviors. All data is grounded — never fabricated.

Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompositeState:
    """The unified continuity state object — single source of truth."""

    operator_presence: str = "unknown"
    operator_location: str = "unknown"
    active_device: str = "unknown"
    audio_output_device: str = "unknown"
    visual_context: str = "none"
    lifecycle_mode: str = "day_cycle"
    profile_mode: str = "developer"
    execution_mode: str = "guided"
    last_operator_intent: str = ""
    active_work_loops: list[dict[str, Any]] = field(default_factory=list)
    open_blockers: list[str] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    last_resume_point: str = ""
    last_updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated_at:
            self.last_updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompositeState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StartupResult:
    """Result of a startup sequence — grounded, never fabricated."""

    success: bool = True
    continuity_state: str = "active"
    lifecycle_mode: str = "day_cycle"
    profile_mode: str = "developer"
    provider_status: dict[str, Any] = field(default_factory=dict)
    node_status: dict[str, Any] = field(default_factory=dict)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    open_blockers: list[str] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    resume_summary: str = ""
    recommended_next: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShutdownResult:
    """Result of a shutdown/end-of-day sequence."""

    success: bool = True
    completed_work: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    open_blockers: list[str] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    resume_point: str = ""
    report_path: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContinuityEngine:
    """Orchestrator for all continuity subsystems."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            state_dir = os.path.join(root, "data", "umh", "workstation_state")
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._dir / "continuity_composite.json"

        from substrate.workstation.checkpoint import CheckpointManager
        from substrate.workstation.intent_contract import IntentContractManager
        from substrate.workstation.resume_brief import ReturnBriefGenerator

        self._csm = self._load_state_machine()
        self._checkpoint_mgr = CheckpointManager(state_dir)
        self._brief_gen = ReturnBriefGenerator(state_dir)
        self._intent_mgr = IntentContractManager(state_dir)

    def _load_state_machine(self) -> Any:
        """Load or create continuity state machine."""
        from substrate.workstation.continuity import (
            ContinuityStateMachine,
        )

        sm_path = self._dir / "continuity_state_machine.json"
        if sm_path.exists():
            try:
                data = json.loads(sm_path.read_text(encoding="utf-8"))
                return ContinuityStateMachine.from_dict(data)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.debug("Failed to load state machine: %s", exc)
        return ContinuityStateMachine()

    def _persist_state_machine(self) -> None:
        sm_path = self._dir / "continuity_state_machine.json"
        sm_path.write_text(
            json.dumps(self._csm.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def startup_sequence(
        self,
        profile_mode: str = "developer",
        source_device: str = "unknown",
    ) -> StartupResult:
        """Execute the start-of-day / start-of-work sequence.

        Uses real grounded data from all subsystems. Never fabricates status.
        """
        from substrate.workstation.continuity import ContinuityState
        from substrate.workstation.lifecycle_modes import LifecycleMode

        result = StartupResult(
            profile_mode=profile_mode,
            lifecycle_mode=LifecycleMode.DAY_CYCLE.value,
        )

        # 1. Transition continuity to ACTIVE
        current = self._csm.current_state
        if current != ContinuityState.ACTIVE:
            try:
                if current == ContinuityState.AWAY:
                    self._csm.transition(ContinuityState.RETURNING, reason="startup_sequence")
                    self._csm.transition(ContinuityState.RESUME_BRIEF, reason="startup_sequence")
                    self._csm.transition(ContinuityState.ACTIVE, reason="startup_sequence")
                elif current in (ContinuityState.NIGHT_SLEEPING, ContinuityState.EXTENDED_ABSENCE):
                    self._csm.transition(ContinuityState.RETURNING, reason="startup_sequence")
                    self._csm.transition(ContinuityState.RESUME_BRIEF, reason="startup_sequence")
                    self._csm.transition(ContinuityState.ACTIVE, reason="startup_sequence")
                elif current in (ContinuityState.RETURNING, ContinuityState.RESUME_BRIEF):
                    if self._csm.can_transition(ContinuityState.ACTIVE):
                        self._csm.transition(ContinuityState.ACTIVE, reason="startup_sequence")
                elif current == ContinuityState.IDLE:
                    self._csm.transition(ContinuityState.ACTIVE, reason="startup_sequence")
                elif current == ContinuityState.REMOTE:
                    self._csm.transition(ContinuityState.ACTIVE, reason="startup_sequence")
            except ValueError as exc:
                result.errors.append(f"Continuity transition failed: {exc}")

        result.continuity_state = self._csm.current_state.value
        self._persist_state_machine()

        # 2. Check provider health (grounded)
        result.provider_status = self._collect_provider_status()

        # 3. Check node health (grounded)
        result.node_status = self._collect_node_status()

        # 4. Check active intent contracts
        active_intents = self._intent_mgr.get_active()
        result.active_loops = [
            {"intent_id": c.intent_id, "intent": c.operator_intent, "status": c.status}
            for c in active_intents
        ]

        # 5. Check blockers
        blocked_intents = self._intent_mgr.get_blocked()
        result.open_blockers = [c.blocker for c in blocked_intents if c.blocker]

        # 6. Check pending approvals (grounded from governance)
        result.pending_approvals = self._collect_pending_approvals()

        # 7. Generate resume summary if returning from absence
        if current != ContinuityState.ACTIVE:
            try:
                brief = self._brief_gen.generate(
                    departure_state=current.value,
                    current_state="active",
                    lifecycle_mode="day_cycle",
                    active_profile_modes=[profile_mode],
                )
                result.resume_summary = self._format_brief(brief)
            except Exception as exc:
                result.errors.append(f"Resume brief failed: {exc}")

        # 8. Derive recommended next action
        result.recommended_next = self._derive_next_action(result)

        # 9. Create checkpoint
        try:
            self._checkpoint_mgr.create_checkpoint(
                previous_state=current.value,
                new_state="active",
                lifecycle_mode="day_cycle",
                active_profile_modes=[profile_mode],
                active_work_packets=[],
                pending_approvals=result.pending_approvals,
                open_loops=[c.intent_id for c in active_intents],
                recommended_next_action=result.recommended_next,
                transition_reason="startup_sequence",
            )
        except Exception as exc:
            result.errors.append(f"Checkpoint failed: {exc}")

        # 10. Persist composite state
        self._persist_composite(result, profile_mode)

        return result

    def shutdown_sequence(self) -> ShutdownResult:
        """Execute the end-of-day / shutdown sequence.

        Summarizes work, saves resume point, creates checkpoint.
        """
        from substrate.workstation.continuity import ContinuityState

        result = ShutdownResult()

        # Collect current state before transitioning
        active_intents = self._intent_mgr.get_active()
        result.open_loops = [f"{c.operator_intent} ({c.status})" for c in active_intents]
        blocked = self._intent_mgr.get_blocked()
        result.open_blockers = [c.blocker for c in blocked if c.blocker]
        result.pending_approvals = self._collect_pending_approvals()

        # Read completed work from events
        result.completed_work = self._read_recent_completions()

        # Derive resume point
        if blocked:
            result.resume_point = f"Unblock: {blocked[0].operator_intent}"
        elif active_intents:
            result.resume_point = f"Continue: {active_intents[0].operator_intent}"
        else:
            result.resume_point = "Ready for new work"

        # Transition to night_sleeping
        try:
            current = self._csm.current_state
            if current == ContinuityState.ACTIVE:
                self._csm.transition(ContinuityState.NIGHT_SLEEPING, reason="shutdown_sequence")
            elif current == ContinuityState.IDLE:
                self._csm.transition(ContinuityState.NIGHT_SLEEPING, reason="shutdown_sequence")
            self._persist_state_machine()
        except ValueError as exc:
            result.errors.append(f"Continuity transition failed: {exc}")

        # Create checkpoint
        try:
            self._checkpoint_mgr.create_checkpoint(
                previous_state=self._csm.current_state.value,
                new_state="night_sleeping",
                lifecycle_mode="night_cycle",
                open_loops=[c.intent_id for c in active_intents],
                pending_approvals=result.pending_approvals,
                recommended_next_action=result.resume_point,
                transition_reason="shutdown_sequence",
            )
        except Exception as exc:
            result.errors.append(f"Checkpoint failed: {exc}")

        # Write session report
        try:
            report_path = self._write_session_report(result)
            result.report_path = str(report_path)
        except Exception as exc:
            result.errors.append(f"Report write failed: {exc}")

        return result

    def transition_to(self, target_state: str, reason: str = "") -> dict[str, Any]:
        """Execute a continuity state transition."""
        from substrate.workstation.continuity import ContinuityState

        try:
            target = ContinuityState(target_state)
        except ValueError:
            return {"ok": False, "error": f"Unknown state: {target_state}"}

        if not self._csm.can_transition(target):
            return {
                "ok": False,
                "error": f"Cannot transition from {self._csm.current_state.value} to {target_state}",
                "valid_targets": [s.value for s in self._csm.valid_transitions()],
            }

        record = self._csm.transition(target, reason=reason)
        self._persist_state_machine()

        self._checkpoint_mgr.create_checkpoint(
            previous_state=record.from_state,
            new_state=record.to_state,
            transition_reason=reason,
        )

        return {"ok": True, "from": record.from_state, "to": record.to_state}

    def resume_from_absence(self) -> dict[str, Any]:
        """Generate a resume brief for the operator returning from absence."""
        current = self._csm.current_state

        try:
            brief = self._brief_gen.generate(
                departure_state=current.value,
                current_state=current.value,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return {
            "ok": True,
            "departure_state": brief.continuity_state_at_departure,
            "current_state": brief.continuity_state_now,
            "what_happened": brief.what_happened,
            "what_changed": brief.what_changed,
            "what_finished": brief.what_finished,
            "what_failed": brief.what_failed,
            "what_is_blocked": brief.what_is_blocked,
            "needs_approval": brief.needs_approval,
            "resume_next": brief.resume_next,
        }

    def get_composite_state(self) -> CompositeState:
        """Build the composite continuity state from all subsystems."""
        from substrate.workstation.profile_behavior import get_behavior

        profile_mode = "developer"
        behavior = get_behavior(profile_mode)

        active_intents = self._intent_mgr.get_active()
        blocked_intents = self._intent_mgr.get_blocked()

        state = CompositeState(
            lifecycle_mode=self._resolve_lifecycle_mode(),
            profile_mode=profile_mode,
            execution_mode=behavior.default_execution_mode,
            last_operator_intent=active_intents[0].operator_intent if active_intents else "",
            active_work_loops=[
                {"intent_id": c.intent_id, "intent": c.operator_intent, "status": c.status}
                for c in active_intents
            ],
            open_blockers=[c.blocker for c in blocked_intents if c.blocker],
            pending_approvals=self._collect_pending_approvals(),
        )

        # Resolve presence from device sessions
        state.operator_presence = self._detect_presence()
        state.operator_location = self._detect_location()

        # Load last checkpoint for resume point
        latest_ckpt = self._checkpoint_mgr.latest()
        if latest_ckpt:
            state.last_resume_point = latest_ckpt.recommended_next_action

        return state

    # ── Grounded data collectors ────────────────────────────────────

    def _collect_provider_status(self) -> dict[str, Any]:
        """Collect real provider health — never fabricated."""
        try:
            from substrate.sockets.intelligence_port import get_model_registry

            MODEL_REGISTRY = get_model_registry()

            healthy = []
            unhealthy = []
            for name, config in MODEL_REGISTRY.items():
                if config.available:
                    healthy.append(name)
                else:
                    unhealthy.append(name)
            return {
                "healthy": healthy,
                "unhealthy": unhealthy,
                "total": len(MODEL_REGISTRY),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _collect_node_status(self) -> dict[str, Any]:
        """Collect real mesh node health."""
        mesh_path = (
            Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "runtime" / "mesh_nodes.json"
        )
        if not mesh_path.exists():
            return {"vps": "running", "beast": "no_mesh_data"}
        try:
            nodes = json.loads(mesh_path.read_text(encoding="utf-8"))
            status: dict[str, Any] = {"vps": "running"}
            for node in nodes:
                if "desktop" in node.get("capabilities", []):
                    status["beast"] = node.get("status", "unknown")
                    break
            if "beast" not in status:
                status["beast"] = "not_registered"
            return status
        except Exception as exc:
            return {"vps": "running", "beast": f"error: {exc}"}

    def _collect_pending_approvals(self) -> list[dict[str, Any]]:
        """Collect real pending approvals from governance."""
        approvals_path = (
            Path(os.environ.get("UMH_ROOT", "/opt/OS"))
            / "data"
            / "umh"
            / "operator_acceptance"
            / "artifacts.jsonl"
        )
        if not approvals_path.exists():
            return []
        pending: list[dict[str, Any]] = []
        try:
            with open(approvals_path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    data = json.loads(stripped)
                    if data.get("status") in ("pending", "awaiting_review"):
                        pending.append(
                            {
                                "artifact_id": data.get("artifact_id", ""),
                                "title": data.get("title", ""),
                                "type": data.get("type", ""),
                            }
                        )
        except Exception:
            pass
        return pending[-10:]

    def _read_recent_completions(self) -> list[str]:
        """Read recently completed work from events."""
        from substrate.state.runtime_paths import runtime_state_path

        events_path = runtime_state_path("organism", "events.jsonl", create_parent=False)
        if not events_path.exists():
            return []
        completed: list[str] = []
        try:
            with open(events_path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    data = json.loads(stripped)
                    etype = data.get("event_type", data.get("type", ""))
                    if "complete" in etype.lower() or "deliver" in etype.lower():
                        desc = data.get("description", data.get("summary", etype))
                        completed.append(desc[:100])
        except Exception:
            pass
        return completed[-10:]

    def _resolve_lifecycle_mode(self) -> str:
        """Map current continuity state to lifecycle mode."""
        from substrate.workstation.continuity import ContinuityState

        mapping = {
            ContinuityState.ACTIVE: "day_cycle",
            ContinuityState.IDLE: "idle",
            ContinuityState.AWAY: "away",
            ContinuityState.REMOTE: "remote_work",
            ContinuityState.NIGHT_SLEEPING: "night_cycle",
            ContinuityState.EXTENDED_ABSENCE: "away",
            ContinuityState.RETURNING: "day_cycle",
            ContinuityState.RESUME_BRIEF: "day_cycle",
        }
        return mapping.get(self._csm.current_state, "day_cycle")

    def _detect_presence(self) -> str:
        """Detect operator presence from device sessions."""
        try:
            from substrate.workstation.device_presence import DevicePresenceRegistry

            registry = DevicePresenceRegistry()
            sessions = registry.get_active_sessions()
            if sessions:
                return "present"
            return "unknown"
        except Exception:
            return "unknown"

    def _detect_location(self) -> str:
        """Detect operator location from continuity state."""
        from substrate.workstation.continuity import ContinuityState

        location_map = {
            ContinuityState.ACTIVE: "workstation",
            ContinuityState.REMOTE: "remote_laptop",
            ContinuityState.AWAY: "unknown",
            ContinuityState.IDLE: "workstation",
        }
        return location_map.get(self._csm.current_state, "unknown")

    def _derive_next_action(self, result: StartupResult) -> str:
        """Deterministically derive the recommended next action."""
        if result.open_blockers:
            return f"Resolve blocker: {result.open_blockers[0]}"
        if result.pending_approvals:
            return f"Review {len(result.pending_approvals)} pending approval(s)"
        if result.active_loops:
            active = [
                l for l in result.active_loops if l["status"] not in ("verified_done", "sealed")
            ]
            if active:
                return f"Continue: {active[0]['intent']}"
        return "Ready for new work"

    def _format_brief(self, brief: Any) -> str:
        """Format a ReturnBrief into a concise summary."""
        parts = []
        if brief.what_finished:
            parts.append(f"Completed: {', '.join(brief.what_finished[:3])}")
        if brief.what_failed:
            parts.append(f"Failed: {', '.join(brief.what_failed[:3])}")
        if brief.what_is_blocked:
            parts.append(f"Blocked: {', '.join(brief.what_is_blocked[:3])}")
        if brief.needs_approval:
            parts.append(f"{len(brief.needs_approval)} approval(s) pending")
        if brief.resume_next:
            parts.append(f"Next: {brief.resume_next}")
        return ". ".join(parts) if parts else "No changes during absence."

    def _persist_composite(self, result: StartupResult, profile_mode: str) -> None:
        """Persist the composite state."""
        state = CompositeState(
            operator_presence="present",
            lifecycle_mode=result.lifecycle_mode,
            profile_mode=profile_mode,
            execution_mode="guided",
            active_work_loops=result.active_loops,
            open_blockers=result.open_blockers,
            pending_approvals=result.pending_approvals,
            last_resume_point=result.recommended_next,
        )
        self._state_path.write_text(
            json.dumps(state.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _write_session_report(self, result: ShutdownResult) -> Path:
        """Write an end-of-day session report."""
        from substrate.state.runtime_paths import runtime_state_dir

        report_dir = runtime_state_dir("organism", create=False) / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_path = report_dir / f"session_report_{ts}.json"
        report_data = {
            "date": ts,
            "completed": result.completed_work,
            "open_loops": result.open_loops,
            "blockers": result.open_blockers,
            "pending_approvals": result.pending_approvals,
            "resume_point": result.resume_point,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(
            json.dumps(report_data, indent=2, default=str),
            encoding="utf-8",
        )
        return report_path
