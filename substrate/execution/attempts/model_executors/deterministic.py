"""Deterministic conformance adapter for ModelExecutor contract tests."""

from __future__ import annotations

import os
import time

from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelInvocation,
    ModelExecutorReadiness,
    ModelTerminalResult,
    ModelWorkPacketInput,
)


class DeterministicConformanceExecutor:
    def __init__(self, *, mode: str | None = None) -> None:
        self.mode = mode or os.environ.get("UMH_DETERMINISTIC_EXECUTOR_MODE", "success")
        self.identity = ModelExecutorIdentity(
            provider="deterministic",
            model="conformance",
            version="1",
            adapter=type(self).__name__,
        )

    def readiness(self, *, env: dict[str, str] | None = None) -> ModelExecutorReadiness:
        return ModelExecutorReadiness(
            ok=self.mode != "not_ready",
            authenticated=self.mode != "not_ready",
            identity=self.identity,
            reason="" if self.mode != "not_ready" else "deterministic not_ready mode",
        )

    def build_invocation(self, packet: ModelWorkPacketInput) -> ModelInvocation:
        return ModelInvocation(argv=["python3", "-c", "print('deterministic content')"], stdin="")

    def collect_result(
        self, packet: ModelWorkPacketInput, completed: object | None, *, duration_seconds: float
    ) -> ModelTerminalResult:
        if completed is None:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                timed_out=True,
                retry_class="external_transient",
                duration_seconds=duration_seconds,
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )
        stdout = getattr(completed, "stdout", "") or ""
        return ModelTerminalResult(
            ok=getattr(completed, "returncode", 1) == 0 and bool(stdout.strip()),
            status="succeeded" if getattr(completed, "returncode", 1) == 0 else "failed",
            stdout=stdout,
            summary=stdout[-500:],
            exit_code=getattr(completed, "returncode", None),
            duration_seconds=duration_seconds,
            retry_class="not_retryable",
            identity=self.identity,
            proof_binding=packet.proof_binding,
        )

    def invoke(self, packet: ModelWorkPacketInput, *, env: dict[str, str]) -> ModelTerminalResult:
        start = time.monotonic()
        if self.mode == "timeout":
            return ModelTerminalResult(
                ok=False,
                status="failed",
                timed_out=True,
                retry_class="external_transient",
                duration_seconds=time.monotonic() - start,
                identity=self.identity,
                proof_binding=packet.proof_binding,
                summary="deterministic timeout",
            )
        if self.mode == "empty":
            return ModelTerminalResult(
                ok=False,
                status="failed",
                retry_class="malformed_output",
                duration_seconds=time.monotonic() - start,
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )
        return ModelTerminalResult(
            ok=True,
            status="succeeded",
            stdout=f"deterministic content for {packet.attempt_id}",
            summary="deterministic content",
            exit_code=0,
            duration_seconds=time.monotonic() - start,
            retry_class="not_retryable",
            usage={"input_tokens": 0, "output_tokens": 0},
            cost={"amount_usd": None, "status": "not_metered"},
            identity=self.identity,
            proof_binding=packet.proof_binding,
        )


__all__ = ["DeterministicConformanceExecutor"]
