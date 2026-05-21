"""Signal protocol — contract for signal ingestion and classification."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.signal.types import Signal, SignalBundle


@runtime_checkable
class SignalClassifier(Protocol):
    """Classifies raw input into typed signals."""

    def classify(self, text: str, source: str = "user") -> SignalBundle: ...


@runtime_checkable
class SignalFilter(Protocol):
    """Filters or transforms a signal bundle before intent compilation."""

    def filter(self, bundle: SignalBundle) -> SignalBundle: ...
