"""Policy/configuration driven model-executor selection."""

from __future__ import annotations

import os

from substrate.execution.attempts.model_executor_contract import ModelExecutor

_DEFAULT_PROVIDER = "codex"


def selected_provider_name() -> str:
    return (os.environ.get("UMH_MODEL_EXECUTOR_PROVIDER") or _DEFAULT_PROVIDER).strip().lower()


def build_model_executor(provider: str | None = None) -> ModelExecutor:
    name = (provider or selected_provider_name()).strip().lower()
    if name == "codex":
        from substrate.execution.attempts.model_executors.codex import CodexModelExecutor

        return CodexModelExecutor()
    if name in {"deterministic", "conformance"}:
        from substrate.execution.attempts.model_executors.deterministic import (
            DeterministicConformanceExecutor,
        )

        return DeterministicConformanceExecutor()
    raise ValueError(f"unsupported model executor provider: {name}")


__all__ = ["build_model_executor", "selected_provider_name"]
