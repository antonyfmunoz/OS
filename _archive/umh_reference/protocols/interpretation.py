"""Interpretation protocol — contract for intent compilation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.signal.types import SignalBundle


@runtime_checkable
class IntentCompiler(Protocol):
    """Compiles a signal bundle into a structured intent."""

    def compile(self, bundle: SignalBundle) -> Any: ...
