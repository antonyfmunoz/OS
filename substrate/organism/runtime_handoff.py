"""Runtime handoff — bridges Work Packets to runtime sessions.

Prepares RuntimeHandoffPreview so the operator can see exactly what
will happen before approving a runtime launch. Never starts a runtime
without approval.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from substrate.organism.runtime_manager import RuntimeManager
from substrate.organism.runtime_session import RuntimeSession, RuntimeType

logger = logging.getLogger(__name__)


@dataclass
class RuntimeHandoffPreview:
    preview_id: str = ""
    work_packet_id: str = ""
    workcell_id: str = ""
    recommended_runtime: str = RuntimeType.SHELL.value
    reason: str = ""
    risk_class: str = "low"
    sandbox_required: bool = True
    expected_artifacts: list[str] = field(default_factory=list)
    validation_plan: str = ""
    approval_required: bool = True
    blocked_reason: str = ""
    what_will_happen: list[str] = field(default_factory=list)
    what_will_not_happen: list[str] = field(default_factory=list)
    command: str = ""
    prompt: str = ""
    operator_session_id: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeHandoffPreview:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


_WILL_NOT_HAPPEN: list[str] = [
    "No production files will be mutated",
    "No PR will be created",
    "No merge will occur",
    "No ProductionOutcomeCommitted will be emitted",
    "No credentials will be modified",
    "No DNS changes will be made",
    "No external client actions will be taken",
    "Runtime operates in sandbox/worktree only",
]


def classify_runtime_need(
    intent_type: str,
    work_packet_id: str = "",
    operator_input: str = "",
) -> dict[str, Any]:
    runtime_intents = {"create_work", "build", "inspect", "analyze", "test", "validate"}

    needs_runtime = False
    for kw in ("run", "build", "inspect", "execute", "start", "launch", "test", "validate", "workcell", "runtime"):
        if kw in operator_input.lower():
            needs_runtime = True
            break

    if intent_type in runtime_intents:
        needs_runtime = True

    if not needs_runtime:
        return {"needs_runtime": False, "reason": "intent does not require runtime execution"}

    recommended = RuntimeType.SHELL.value
    if any(kw in operator_input.lower() for kw in ("claude", "agent", "code review", "implement")):
        recommended = RuntimeType.CLAUDE_CODE_PTY.value

    return {
        "needs_runtime": True,
        "recommended_runtime": recommended,
        "reason": f"intent_type={intent_type} with runtime keywords detected",
    }


def create_handoff_preview(
    work_packet_id: str = "",
    workcell_id: str = "",
    operator_session_id: str = "",
    operator_input: str = "",
    intent_type: str = "create_work",
    risk_class: str = "low",
    command: str = "",
    prompt: str = "",
    manager: RuntimeManager | None = None,
) -> RuntimeHandoffPreview:
    mgr = manager or RuntimeManager()

    classification = classify_runtime_need(
        intent_type=intent_type,
        work_packet_id=work_packet_id,
        operator_input=operator_input,
    )

    if not classification["needs_runtime"]:
        return RuntimeHandoffPreview(
            preview_id=f"rhp-{uuid.uuid4().hex[:8]}",
            work_packet_id=work_packet_id,
            blocked_reason="intent does not require runtime execution",
            timestamp=time.time(),
        )

    recommended = classification.get("recommended_runtime", RuntimeType.SHELL.value)

    if not command and not prompt:
        if recommended == RuntimeType.SHELL.value:
            command = "git status --short && git log --oneline -5"
        prompt = operator_input

    adapters = mgr.get_adapters()
    adapter_info = adapters.get(recommended, {})
    adapter_available = adapter_info.get("available", False)

    blocked_reason = ""
    if not adapter_available:
        if recommended == RuntimeType.CLAUDE_CODE_PTY.value:
            recommended = RuntimeType.SHELL.value
            adapter_info = adapters.get(recommended, {})
            adapter_available = adapter_info.get("available", False)
            if not adapter_available:
                blocked_reason = "no available runtime adapter"
        else:
            blocked_reason = f"adapter {recommended} not available"

    if risk_class in ("high", "critical"):
        blocked_reason = f"risk_class={risk_class} is blocked for runtime execution"
    approval_required = risk_class == "medium" or True

    what_will_happen = [
        f"Create sandbox/worktree for session",
        f"Run {recommended} adapter in isolated environment",
        f"Stream stdout/stderr events to cockpit",
        f"Collect artifacts and validation results",
        f"Session can be stopped at any time by operator",
    ]
    if command:
        what_will_happen.insert(1, f"Execute: {command[:120]}")

    return RuntimeHandoffPreview(
        preview_id=f"rhp-{uuid.uuid4().hex[:8]}",
        work_packet_id=work_packet_id,
        workcell_id=workcell_id,
        recommended_runtime=recommended,
        reason=classification.get("reason", ""),
        risk_class=risk_class,
        sandbox_required=True,
        expected_artifacts=["session_output.log", "event_stream.jsonl"],
        validation_plan="exit_code_check + output_inspection + artifact_collection",
        approval_required=approval_required,
        blocked_reason=blocked_reason,
        what_will_happen=what_will_happen,
        what_will_not_happen=list(_WILL_NOT_HAPPEN),
        command=command,
        prompt=prompt,
        operator_session_id=operator_session_id,
        timestamp=time.time(),
    )


def execute_approved_handoff(
    preview: RuntimeHandoffPreview,
    approved_by: str = "operator",
    manager: RuntimeManager | None = None,
) -> tuple[RuntimeSession | None, dict[str, Any]]:
    if preview.blocked_reason:
        return None, {"started": False, "reason": preview.blocked_reason}

    mgr = manager or RuntimeManager()

    session, policy = mgr.create_runtime_session(
        runtime_type=preview.recommended_runtime,
        command=preview.command,
        prompt=preview.prompt,
        work_packet_id=preview.work_packet_id,
        operator_session_id=preview.operator_session_id,
        workcell_id=preview.workcell_id,
        risk_class=preview.risk_class,
    )

    if not policy.get("allowed", True):
        return session, {"started": False, "reason": session.failure_reason, "session_id": session.session_id}

    result = mgr.start_session(session.session_id, approved_by=approved_by)
    return session, {
        "started": result.started,
        "session_id": session.session_id,
        "status": result.status,
        "output": result.output[:500] if result.output else "",
        "error": result.error,
    }
