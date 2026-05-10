"""Phase 77 boot sequence MVP — loads context only, no execution.

The boot sequence creates/loads the workstation state needed for
a session.  It does NOT execute adapters, run shell commands,
or make network calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class BootStep:
    name: str
    status: str = "pending"
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class BootResult:
    boot_id: str = ""
    mode: str = ""
    user_id: str = ""
    workstation_id: str = ""
    steps: list[BootStep] = field(default_factory=list)
    loaded_profile: dict[str, Any] = field(default_factory=dict)
    loaded_session: dict[str, Any] = field(default_factory=dict)
    loaded_devices: list[dict[str, Any]] = field(default_factory=list)
    loaded_environments: list[dict[str, Any]] = field(default_factory=list)
    resume_summary: dict[str, Any] = field(default_factory=dict)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    execution_preference: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boot_id": self.boot_id,
            "mode": self.mode,
            "user_id": self.user_id,
            "workstation_id": self.workstation_id,
            "steps": [s.to_dict() for s in self.steps],
            "loaded_profile": self.loaded_profile,
            "loaded_session": self.loaded_session,
            "loaded_devices": self.loaded_devices,
            "loaded_environments": self.loaded_environments,
            "resume_summary": self.resume_summary,
            "pending_approvals": self.pending_approvals,
            "execution_preference": self.execution_preference,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


def _run_step(step: BootStep, fn: Any) -> None:
    try:
        result = fn()
        step.status = "completed"
        step.output = result if isinstance(result, dict) else {}
    except Exception as e:
        step.status = "failed"
        step.error = str(e)


def run_boot_sequence(
    user_id: str,
    mode: str | None = None,
    store: Any | None = None,
    trace_store: Any | None = None,
    approval_store: Any | None = None,
) -> BootResult:
    """Execute the 10-step boot sequence. Loads context only — no execution."""
    import uuid

    boot_id = f"boot_{uuid.uuid4().hex[:12]}"
    result = BootResult(
        boot_id=boot_id,
        user_id=user_id,
        started_at=_iso_now(),
        status="running",
    )

    # Step 1: Load/create profile
    step1 = BootStep(name="load_profile")
    result.steps.append(step1)

    from umh.workstation.operator_profile import load_or_create_profile

    def _load_profile():
        profile = load_or_create_profile(user_id, store=store)
        result.loaded_profile = profile.to_dict()
        result.workstation_id = profile.workstation_id
        result.execution_preference = profile.execution_preference.to_dict()
        return {"workstation_id": profile.workstation_id}

    _run_step(step1, _load_profile)

    # Step 2: Validate/resolve mode
    step2 = BootStep(name="resolve_mode")
    result.steps.append(step2)

    resolved_mode = mode or "command_center"

    def _resolve_mode():
        from umh.workstation.modes import ModeRegistry

        registry = ModeRegistry()
        if not registry.validate_mode(resolved_mode):
            raise ValueError(f"Invalid mode: {resolved_mode}")
        profile_data = registry.get_mode(resolved_mode)
        return {
            "mode": resolved_mode,
            "description": profile_data.description if profile_data else "",
        }

    _run_step(step2, _resolve_mode)
    result.mode = resolved_mode

    # Step 3: Load/register default devices
    step3 = BootStep(name="load_devices")
    result.steps.append(step3)

    def _load_devices():
        from umh.workstation.device_registry import DeviceRegistry, create_default_devices

        registry = DeviceRegistry()
        devices = create_default_devices()
        for d in devices:
            registry.register_device(d)
        result.loaded_devices = [d.to_dict() for d in devices]
        return {"device_count": len(devices)}

    _run_step(step3, _load_devices)

    # Step 4: Load/register default environments
    step4 = BootStep(name="load_environments")
    result.steps.append(step4)

    def _load_environments():
        from umh.workstation.environment_registry import (
            WorkstationEnvironmentRegistry,
            create_default_environments,
        )

        registry = WorkstationEnvironmentRegistry()
        envs = create_default_environments()
        for e in envs:
            registry.register_environment(e)
        result.loaded_environments = [e.to_dict() for e in envs]
        return {"environment_count": len(envs)}

    _run_step(step4, _load_environments)

    # Step 5: Load/create active session
    step5 = BootStep(name="load_session")
    result.steps.append(step5)

    def _load_session():
        from umh.workstation.session_state import get_session_store

        session_store = get_session_store()
        session = session_store.get_active_session(user_id)
        if session is None:
            session = session_store.create_session(
                user_id=user_id,
                workstation_id=result.workstation_id,
                mode=resolved_mode,
            )
        result.loaded_session = session.to_dict()
        return {"session_id": session.session_id, "status": session.status.value}

    _run_step(step5, _load_session)

    # Step 6: Load recent trace summary
    step6 = BootStep(name="load_traces")
    result.steps.append(step6)

    def _load_traces():
        from umh.workstation.resume import summarize_recent_traces

        if trace_store is None:
            return {"trace_count": 0, "source": "unavailable"}
        trace_ids, successes, failures = summarize_recent_traces(trace_store, user_id)
        return {
            "trace_count": len(trace_ids),
            "successes": successes,
            "failures": failures,
        }

    _run_step(step6, _load_traces)

    # Step 7: Load pending approvals
    step7 = BootStep(name="load_approvals")
    result.steps.append(step7)

    def _load_approvals():
        from umh.workstation.resume import list_pending_approvals

        approvals = list_pending_approvals(user_id, approval_store=approval_store)
        result.pending_approvals = [a.to_dict() for a in approvals]
        return {"pending_count": len(approvals)}

    _run_step(step7, _load_approvals)

    # Step 8: Build resume summary
    step8 = BootStep(name="build_resume")
    result.steps.append(step8)

    def _build_resume():
        from umh.workstation.operator_profile import OperatorProfile
        from umh.workstation.resume import build_resume_summary
        from umh.workstation.session_state import SessionState

        profile = (
            OperatorProfile.from_dict(result.loaded_profile) if result.loaded_profile else None
        )
        session = SessionState.from_dict(result.loaded_session) if result.loaded_session else None

        if profile is None:
            return {"source": "unavailable"}

        summary = build_resume_summary(
            profile=profile,
            session=session,
            trace_store=trace_store,
            approval_store=approval_store,
        )
        result.resume_summary = summary.to_dict()
        return {"generated": True}

    _run_step(step8, _build_resume)

    # Step 9: Resolve execution preference
    step9 = BootStep(name="resolve_preference")
    result.steps.append(step9)

    def _resolve_preference():
        from umh.workstation.modes import ModeRegistry

        registry = ModeRegistry()
        mode_profile = registry.get_mode(resolved_mode)
        pref_env = "local"
        if mode_profile:
            pref_env = mode_profile.default_environment_preference
        result.execution_preference["preferred_environment"] = pref_env
        return {"preferred_environment": pref_env}

    _run_step(step9, _resolve_preference)

    # Step 10: Finalize
    step10 = BootStep(name="finalize")
    result.steps.append(step10)

    def _finalize():
        completed = sum(1 for s in result.steps if s.status == "completed")
        failed = sum(1 for s in result.steps if s.status == "failed")
        return {"completed": completed, "failed": failed, "total": len(result.steps)}

    _run_step(step10, _finalize)

    failed_steps = [s for s in result.steps if s.status == "failed"]
    result.status = "completed" if not failed_steps else "partial"
    result.completed_at = _iso_now()

    return result
