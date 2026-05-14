"""CLI Runtime Ingress Adapter v1.

Converts CLI commands into RuntimeIngressSignal for
routing through the canonical spine.

The CLI adapter:
  - Converts terminal commands → RuntimeIngressSignal
  - Preserves terminal session lineage
  - Preserves operational continuity
  - CANNOT execute directly
  - CANNOT bypass the ingress router

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import os
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSource,
    RuntimeIngressIdentity,
    RuntimeIngressSignal,
    _new_id,
    _now_iso,
)


class CLIRuntimeIngressAdapter:
    """Converts CLI commands to normalized ingress signals.

    Cannot execute directly — produces signals for the
    ingress router to dispatch through the spine.
    """

    def __init__(
        self,
        terminal_session_id: str = "",
    ) -> None:
        self._terminal_session_id = terminal_session_id or _new_id("term")
        self._identity: RuntimeIngressIdentity | None = None
        self._total_adapted: int = 0
        self._command_history: list[str] = []

    def adapt_command(
        self,
        raw_input: str,
        operator_name: str = "",
    ) -> RuntimeIngressSignal:
        """Convert a CLI command into an ingress signal."""
        identity = self._resolve_identity(operator_name)

        signal = RuntimeIngressSignal(
            source=IngressSource.CLI,
            raw_input=raw_input,
            operator_id=identity.operator_id,
            channel_id=self._terminal_session_id,
            payload={
                "terminal_session": self._terminal_session_id,
                "cwd": os.getcwd(),
                "command_index": len(self._command_history),
            },
        )
        self._command_history.append(raw_input)
        self._total_adapted += 1
        return signal

    def _resolve_identity(
        self, operator_name: str,
    ) -> RuntimeIngressIdentity:
        if self._identity:
            return self._identity

        name = operator_name or os.environ.get("USER", "operator")
        self._identity = RuntimeIngressIdentity(
            operator_id=f"op-cli-{name}",
            source=IngressSource.CLI,
            display_name=name,
            source_specific_id=self._terminal_session_id,
            authenticated=True,
        )
        return self._identity

    def get_identity(self) -> RuntimeIngressIdentity | None:
        return self._identity

    def get_command_history(self, limit: int = 20) -> list[str]:
        return self._command_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "terminal_session_id": self._terminal_session_id,
            "total_adapted": self._total_adapted,
            "command_history_size": len(self._command_history),
        }
