"""Remote execution port — substrate-layer abstraction for SSH and remote ops.

The adapter layer (adapters/ssh/) registers its concrete functions at startup.
Substrate code calls the thin wrappers here, never importing from adapters/.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

_ssh_run_fn: Optional[Callable] = None
_ssh_reachable_fn: Optional[Callable] = None
_scp_to_fn: Optional[Callable] = None


def register_ssh(
    *,
    ssh_run: Optional[Callable] = None,
    ssh_reachable: Optional[Callable] = None,
    scp_to: Optional[Callable] = None,
) -> None:
    """Register SSH adapter functions."""
    global _ssh_run_fn, _ssh_reachable_fn, _scp_to_fn
    if ssh_run is not None:
        _ssh_run_fn = ssh_run
    if ssh_reachable is not None:
        _ssh_reachable_fn = ssh_reachable
    if scp_to is not None:
        _scp_to_fn = scp_to


def ssh_run(*args: Any, **kwargs: Any) -> Any:
    """Run a command via SSH, or None if not registered."""
    if _ssh_run_fn is not None:
        return _ssh_run_fn(*args, **kwargs)
    return None


def ssh_reachable(*args: Any, **kwargs: Any) -> bool:
    """Check if SSH target is reachable, or False if not registered."""
    if _ssh_reachable_fn is not None:
        return _ssh_reachable_fn(*args, **kwargs)
    return False


def scp_to(*args: Any, **kwargs: Any) -> Any:
    """Copy file via SCP, or None if not registered."""
    if _scp_to_fn is not None:
        return _scp_to_fn(*args, **kwargs)
    return None
