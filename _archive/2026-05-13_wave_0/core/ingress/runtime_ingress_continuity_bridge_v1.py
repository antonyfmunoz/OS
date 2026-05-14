"""Runtime Ingress Continuity Bridge v1.

Bridges ingress sessions with cognition, workflows,
continuity, embodiment, and observability layers.

The bridge does not execute — it links ingress context
to the governed substrate layers.

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSource,
    RuntimeIngressContext,
    RuntimeIngressSignal,
    _new_id,
    _now_iso,
)


class RuntimeIngressContinuityBridge:
    """Bridges ingress sessions with substrate layers.

    Links ingress to cognition, workflows, continuity,
    embodiment, and observability. Does not execute.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/ingress_sessions",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._continuity_records: list[dict[str, Any]] = []
        self._total_bridges: int = 0

    def capture_ingress_context(
        self,
        signal: RuntimeIngressSignal,
        cognition_snapshot: dict[str, Any] | None = None,
    ) -> RuntimeIngressContext:
        """Capture the operational context at ingress time."""
        cog = cognition_snapshot or {}
        cog_state = cog.get("cognitive_state", {})

        context = RuntimeIngressContext(
            session_id=signal.session_id,
            source=signal.source,
            active_focus_id=cog_state.get("active_focus_id", ""),
            open_loop_count=cog_state.get("open_loop_count", 0),
            continuity_chain_length=cog_state.get("continuity_chain_length", 0),
            operator_mode=cog_state.get("operator_mode", ""),
            cognition_phase=cog_state.get("phase", ""),
        )
        return context

    def bridge_to_cognition(
        self,
        signal: RuntimeIngressSignal,
        cognition_session_id: str,
    ) -> dict[str, Any]:
        """Link an ingress signal to its cognition session."""
        record = {
            "bridge_id": _new_id("ingbrg"),
            "bridge_type": "cognition",
            "signal_id": signal.signal_id,
            "session_id": signal.session_id,
            "source": signal.source.value,
            "cognition_session_id": cognition_session_id,
            "timestamp": _now_iso(),
        }
        self._persist_bridge(record)
        self._total_bridges += 1
        return record

    def bridge_to_workflow(
        self,
        signal: RuntimeIngressSignal,
        workflow_id: str,
        workflow_type: str = "",
    ) -> dict[str, Any]:
        """Link an ingress signal to a workflow execution."""
        record = {
            "bridge_id": _new_id("ingbrg"),
            "bridge_type": "workflow",
            "signal_id": signal.signal_id,
            "session_id": signal.session_id,
            "source": signal.source.value,
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "timestamp": _now_iso(),
        }
        self._persist_bridge(record)
        self._total_bridges += 1
        return record

    def bridge_to_continuity(
        self,
        signal: RuntimeIngressSignal,
        continuity_record_id: str,
        continuation_type: str = "",
    ) -> dict[str, Any]:
        """Link an ingress signal to a continuity record."""
        record = {
            "bridge_id": _new_id("ingbrg"),
            "bridge_type": "continuity",
            "signal_id": signal.signal_id,
            "session_id": signal.session_id,
            "source": signal.source.value,
            "continuity_record_id": continuity_record_id,
            "continuation_type": continuation_type,
            "timestamp": _now_iso(),
        }
        self._persist_bridge(record)
        self._total_bridges += 1
        return record

    def bridge_to_embodiment(
        self,
        signal: RuntimeIngressSignal,
        embodiment_path: str,
    ) -> dict[str, Any]:
        """Link an ingress signal to an embodiment path."""
        record = {
            "bridge_id": _new_id("ingbrg"),
            "bridge_type": "embodiment",
            "signal_id": signal.signal_id,
            "session_id": signal.session_id,
            "source": signal.source.value,
            "embodiment_path": embodiment_path,
            "timestamp": _now_iso(),
        }
        self._persist_bridge(record)
        self._total_bridges += 1
        return record

    def _persist_bridge(self, record: dict[str, Any]) -> None:
        self._continuity_records.append(record)
        path = self._state_dir / "ingress_continuity_bridges.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def get_bridges_for_signal(
        self, signal_id: str,
    ) -> list[dict[str, Any]]:
        return [r for r in self._continuity_records if r.get("signal_id") == signal_id]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_bridges": self._total_bridges,
            "bridge_types": {
                bt: sum(1 for r in self._continuity_records if r.get("bridge_type") == bt)
                for bt in ["cognition", "workflow", "continuity", "embodiment"]
            },
        }
