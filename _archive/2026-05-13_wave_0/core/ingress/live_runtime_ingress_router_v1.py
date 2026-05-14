"""Live Runtime Ingress Router v1.

Canonical ingress routing: normalizes signals from any
surface and routes them through LiveSubstrateRuntimeSpine.process().

No ingress surface may orchestrate directly.
All ingress → normalize → spine.process() → response.

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressPhase,
    IngressSource,
    RuntimeIngressLineage,
    RuntimeIngressReceipt,
    RuntimeIngressResponse,
    RuntimeIngressSignal,
    _content_hash,
    _new_id,
    _now_iso,
)


SOURCE_TO_SPINE_SOURCE: dict[str, str] = {
    "discord": "discord",
    "cli": "manual",
    "api": "api",
    "webhook": "api",
    "cron": "cron",
    "internal": "spine",
}

COMMAND_PREFIX = "!"


class LiveRuntimeIngressRouter:
    """Routes all ingress signals through the canonical spine.

    Normalizes signals from any surface into RuntimeIngressSignal,
    dispatches through spine.process(), and returns normalized responses.
    Cannot execute directly — always routes through spine.
    """

    def __init__(
        self,
        spine: Any = None,
        state_dir: str | Path = "data/runtime/ingress_lineage",
    ) -> None:
        self._spine = spine
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._total_routed: int = 0
        self._total_denied: int = 0
        self._receipts: list[RuntimeIngressReceipt] = []
        self._lineage: list[RuntimeIngressLineage] = []

    def route(
        self,
        signal: RuntimeIngressSignal,
    ) -> RuntimeIngressResponse:
        """Route an ingress signal through the canonical spine."""
        start = time.monotonic()

        normalized_cmd = self._normalize_command(signal.raw_input)
        signal.normalized_command = normalized_cmd
        signal.ingress_phase = IngressPhase.NORMALIZED

        spine_source = SOURCE_TO_SPINE_SOURCE.get(
            signal.source.value, "manual"
        )

        if self._spine is None:
            duration_ms = (time.monotonic() - start) * 1000
            self._total_denied += 1
            signal.ingress_phase = IngressPhase.DENIED

            receipt = self._emit_receipt(
                signal, IngressPhase.DENIED, "",
                "no_spine", duration_ms, approved=False,
            )

            return self._build_response(
                signal, "denied", normalized_cmd,
                error="No spine configured",
                receipt_id=receipt.receipt_id,
                duration_ms=duration_ms,
            )

        try:
            from core.runtime.live_runtime_contracts_v1 import (
                RuntimeSignalSource,
            )
            source_enum = RuntimeSignalSource(spine_source)
        except (ImportError, ValueError):
            source_enum = None

        signal.ingress_phase = IngressPhase.ROUTED

        try:
            outcome = self._spine.process(
                raw_input=signal.raw_input,
                source=source_enum,
                user_id=signal.operator_id,
                channel_id=signal.channel_id,
                payload=signal.payload,
            )

            duration_ms = (time.monotonic() - start) * 1000
            succeeded = getattr(outcome, "succeeded", False)
            status = "success" if succeeded else "failed"
            outcome_id = getattr(outcome, "outcome_id", "")
            command_name = getattr(outcome, "command_name", normalized_cmd)
            result_data = getattr(outcome, "result_data", {})
            error_msg = getattr(outcome, "error_message", "")
            governance = getattr(outcome, "governance_verdict", "")

            signal.ingress_phase = IngressPhase.COMPLETED
            self._total_routed += 1

            receipt = self._emit_receipt(
                signal, IngressPhase.COMPLETED, outcome_id,
                governance, duration_ms,
            )
            self._emit_lineage(signal, outcome_id)

            return self._build_response(
                signal, status, command_name,
                result_data=result_data, error=error_msg,
                receipt_id=receipt.receipt_id,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            signal.ingress_phase = IngressPhase.FAILED
            self._total_denied += 1

            self._emit_receipt(
                signal, IngressPhase.FAILED, "",
                "exception", duration_ms, approved=False,
            )

            return self._build_response(
                signal, "failed", normalized_cmd,
                error=str(exc), duration_ms=duration_ms,
            )

    def _normalize_command(self, raw_input: str) -> str:
        """Normalize raw input into a canonical command form."""
        text = raw_input.strip()
        if text.startswith(COMMAND_PREFIX):
            text = text[len(COMMAND_PREFIX):]
        return text.strip().lower().split()[0] if text.strip() else ""

    def _build_response(
        self,
        signal: RuntimeIngressSignal,
        status: str,
        command_name: str,
        result_data: dict[str, Any] | None = None,
        error: str = "",
        receipt_id: str = "",
        duration_ms: float = 0.0,
    ) -> RuntimeIngressResponse:
        return RuntimeIngressResponse(
            signal_id=signal.signal_id,
            session_id=signal.session_id,
            source=signal.source,
            status=status,
            command_name=command_name,
            result_data=result_data or {},
            error_message=error,
            receipt_id=receipt_id,
        )

    def _emit_receipt(
        self,
        signal: RuntimeIngressSignal,
        phase: IngressPhase,
        outcome_id: str,
        governance: str,
        duration_ms: float,
        approved: bool = True,
    ) -> RuntimeIngressReceipt:
        receipt = RuntimeIngressReceipt(
            signal_id=signal.signal_id,
            session_id=signal.session_id,
            source=signal.source,
            ingress_phase=phase,
            spine_outcome_id=outcome_id,
            governance_verdict=governance,
            duration_ms=duration_ms,
            approved=approved,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "ingress_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt

    def _emit_lineage(
        self,
        signal: RuntimeIngressSignal,
        outcome_id: str,
    ) -> RuntimeIngressLineage:
        lineage = RuntimeIngressLineage(
            signal_id=signal.signal_id,
            session_id=signal.session_id,
            source=signal.source,
            spine_outcome_id=outcome_id,
            ingress_phase=signal.ingress_phase,
        )
        self._lineage.append(lineage)

        path = self._state_dir / "ingress_lineage.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(lineage.to_dict(), default=str) + "\n")

        return lineage

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_routed": self._total_routed,
            "total_denied": self._total_denied,
            "total_receipts": len(self._receipts),
            "total_lineage": len(self._lineage),
        }
