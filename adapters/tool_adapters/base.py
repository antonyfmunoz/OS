"""Base adapter — shared interface and deny-rule machinery."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from substrate.governance.risk_classes import RiskClass


class BaseAdapter(ABC):
    """Abstract adapter with deny-rule infrastructure.

    Subclasses declare _DENIED_OPERATIONS (exact matches) and
    _DENIED_PATTERNS (regex patterns). The base validates
    before dispatching to the concrete implementation.
    """

    _DENIED_OPERATIONS: frozenset[str] = frozenset()
    _DENIED_PATTERNS: tuple[re.Pattern[str], ...] = ()

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def _execute_impl(self, operation: str, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass: ...

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Validate against deny rules, then dispatch."""
        denial = self._check_denied(operation, params)
        if denial:
            raise PermissionError(denial)
        return self._execute_impl(operation, params)

    def _check_denied(self, operation: str, params: dict[str, Any]) -> str | None:
        """Return a denial reason, or None if allowed."""
        if operation in self._DENIED_OPERATIONS:
            return f"operation '{operation}' is denied by {self.name} adapter"

        check_str = f"{operation} {' '.join(str(v) for v in params.values())}"
        for pattern in self._DENIED_PATTERNS:
            if pattern.search(check_str):
                return f"pattern '{pattern.pattern}' matched in {self.name} adapter — blocked"

        return None
