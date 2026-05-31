"""Claude Code PTY runtime adapter — skeleton with truthful availability.

Detects whether the claude binary is installed, whether runtime policy
allows Claude Code execution, and prepares for future PTY session management.
Falls back truthfully when unavailable.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

from substrate.organism.runtime_adapter import (
    RuntimeAdapter,
    RuntimeInjectRequest,
    RuntimeStartRequest,
    RuntimeStartResult,
)
from substrate.organism.runtime_session import (
    RuntimeEvent,
    RuntimeEventType,
    persist_event,
)

logger = logging.getLogger(__name__)


def _detect_claude_binary() -> tuple[bool, str]:
    path = shutil.which("claude")
    if path:
        return True, path
    common_paths = [
        os.path.expanduser("~/.claude/local/claude"),
        "/usr/local/bin/claude",
        "/usr/bin/claude",
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return True, p
    return False, ""


def _detect_runtime_policy() -> tuple[bool, str]:
    policy_env = os.environ.get("UMH_CLAUDE_RUNTIME_POLICY", "sandbox_only")
    if policy_env in ("sandbox_only", "enabled"):
        return True, policy_env
    return False, f"policy={policy_env} does not allow Claude Code runtime"


class ClaudeCodeRuntimeAdapter(RuntimeAdapter):
    adapter_id = "claude-code-adapter-v1"
    runtime_type = "claude_code_pty"

    def __init__(self) -> None:
        self._binary_found, self._binary_path = _detect_claude_binary()
        self._policy_allowed, self._policy_reason = _detect_runtime_policy()

    def is_available(self) -> bool:
        return self._binary_found and self._policy_allowed

    def availability_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "available": self.is_available(),
            "adapter_id": self.adapter_id,
            "runtime_type": self.runtime_type,
            "binary_found": self._binary_found,
            "binary_path": self._binary_path or None,
            "policy_allowed": self._policy_allowed,
            "policy_reason": self._policy_reason,
        }
        if not self.is_available():
            reasons: list[str] = []
            if not self._binary_found:
                reasons.append("claude binary not found in PATH or common locations")
            if not self._policy_allowed:
                reasons.append(self._policy_reason)
            detail["unavailable_reasons"] = reasons
            detail["required_configuration"] = [
                "Install Claude Code CLI (claude binary in PATH)",
                "Set UMH_CLAUDE_RUNTIME_POLICY=sandbox_only or enabled",
                "Ensure valid authentication (OAuth token or API key)",
            ]
            detail["next_steps"] = [
                "Install Claude Code: npm install -g @anthropic-ai/claude-code",
                "Authenticate: claude auth login",
                "Verify: claude --version",
            ]
        return detail

    def prepare(self, request: RuntimeStartRequest) -> dict[str, Any]:
        if not self.is_available():
            detail = self.availability_detail()
            return {
                "ready": False,
                "reason": "Claude Code runtime not available",
                "detail": detail,
            }
        if request.risk_class not in ("low",):
            return {
                "ready": False,
                "reason": f"risk_class={request.risk_class} requires explicit operator approval for Claude Code",
            }
        if request.sandbox_required and not request.cwd:
            return {"ready": False, "reason": "sandbox cwd required but not provided"}
        if request.cwd and not os.path.isdir(request.cwd):
            return {"ready": False, "reason": f"cwd does not exist: {request.cwd}"}
        return {
            "ready": True,
            "binary_path": self._binary_path,
            "cwd": request.cwd,
            "prompt": request.prompt,
        }

    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        prep = self.prepare(request)
        if not prep.get("ready"):
            persist_event(RuntimeEvent.create(
                session_id=request.session_id,
                event_type=RuntimeEventType.BLOCKED,
                message=prep.get("reason", "not ready"),
            ))
            return RuntimeStartResult(
                session_id=request.session_id,
                started=False,
                error=prep.get("reason", "preparation failed"),
                metadata={"adapter": self.adapter_id, "detail": prep},
            )

        persist_event(RuntimeEvent.create(
            session_id=request.session_id,
            event_type=RuntimeEventType.RUNTIME_STARTING,
            message="Claude Code PTY session starting (skeleton — full PTY management in Phase 13.3+)",
        ))

        return RuntimeStartResult(
            session_id=request.session_id,
            started=False,
            error="Claude Code PTY session management not yet implemented — skeleton adapter",
            metadata={
                "adapter": self.adapter_id,
                "binary_path": self._binary_path,
                "implementation_phase": "13.3+",
                "note": "Adapter correctly detects availability; full PTY lifecycle deferred",
            },
        )

    def inject(self, request: RuntimeInjectRequest) -> dict[str, Any]:
        return {
            "injected": False,
            "reason": "Claude Code PTY injection not yet implemented — skeleton adapter",
        }

    def stop(self, session_id: str, reason: str = "") -> dict[str, Any]:
        return {
            "stopped": False,
            "reason": "no active Claude Code PTY session to stop — skeleton adapter",
        }

    def status(self, session_id: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": "Claude Code PTY not yet implemented — skeleton adapter",
        }

    def collect_output(self, session_id: str) -> str:
        return ""

    def collect_artifacts(self, session_id: str) -> list[str]:
        return []

    def validate(self, session_id: str) -> dict[str, Any]:
        return {"valid": False, "reason": "skeleton adapter — no session to validate"}

    def cleanup(self, session_id: str) -> dict[str, Any]:
        return {"cleaned": True, "reason": "skeleton adapter — nothing to clean"}
