"""Policy/configuration driven model-executor selection."""

from __future__ import annotations

import os

from substrate.execution.attempts.model_executor_contract import ModelExecutor

_DEFAULT_PROVIDER = "codex"
_DEFAULT_CODEX_MODEL = "gpt-5.3-codex-spark"
_TEST_ONLY_PROVIDERS = {"deterministic", "conformance"}


def selected_provider_name() -> str:
    return (os.environ.get("UMH_MODEL_EXECUTOR_PROVIDER") or _DEFAULT_PROVIDER).strip().lower()


def selected_codex_model() -> str:
    return (os.environ.get("UMH_CODEX_MODEL") or _DEFAULT_CODEX_MODEL).strip()


def build_model_executor(provider: str | None = None) -> ModelExecutor:
    name = (provider or selected_provider_name()).strip().lower()
    if name == "codex":
        from substrate.execution.attempts.model_executors.codex import CodexModelExecutor

        return CodexModelExecutor()
    if name in _TEST_ONLY_PROVIDERS:
        if os.environ.get("UMH_ALLOW_TEST_MODEL_EXECUTOR") != "1":
            raise ValueError(
                f"test-only model executor provider {name!r} requires "
                "UMH_ALLOW_TEST_MODEL_EXECUTOR=1"
            )
        from substrate.execution.attempts.model_executors.deterministic import (
            DeterministicConformanceExecutor,
        )

        return DeterministicConformanceExecutor()
    raise ValueError(f"unsupported model executor provider: {name}")


__all__ = ["build_model_executor", "selected_codex_model", "selected_provider_name"]
