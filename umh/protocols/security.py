"""Security protocols — contracts for access control and confidentiality.

Security is distinct from governance: governance decides policy and authority
levels; security enforces access control, credential management, and
data confidentiality.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AccessPolicy(Protocol):
    """Contract for access control decisions."""

    def check_access(
        self,
        principal: str,
        resource: str,
        action: str,
    ) -> tuple[bool, str]: ...


@runtime_checkable
class SecretProvider(Protocol):
    """Contract for secure credential retrieval."""

    def get_secret(self, key: str) -> str | None: ...

    def has_secret(self, key: str) -> bool: ...
