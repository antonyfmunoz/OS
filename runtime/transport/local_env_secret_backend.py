"""
Local .env secret backend for Phase 94D.9S.

Development/bootstrap backend that reads secrets from a local .env file
outside the repository. The file must be at a safe path like
~/.umh/secrets/.env — never inside the repo.

This backend allows workers to check secret availability and retrieve
values for approved local actions. Secret values are NEVER printed,
logged, or exposed to model context.

The model may know: a key exists, what scope it belongs to.
The model may NOT know: the value.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from eos_ai.transport.secret_broker_contracts import (
    SecretBackendType,
    SecretRef,
    SecretScope,
    SecretUseStatus,
)


DEFAULT_SECRET_PATH = os.path.expanduser("~/.umh/secrets/.env")
REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

SCOPE_PREFIX_MAP: dict[str, SecretScope] = {
    "GOOGLE_": SecretScope.GOOGLE_WORKSPACE,
    "WHOP_": SecretScope.WHOP,
    "STRIPE_": SecretScope.STRIPE,
    "GITHUB_": SecretScope.GITHUB,
    "DISCORD_": SecretScope.DISCORD,
}


def validate_env_path_is_outside_repo(path: str, repo_root: str = REPO_ROOT) -> list[str]:
    """Validate that the secret .env path is outside the repository."""
    errors: list[str] = []
    resolved = str(Path(path).resolve())
    repo_resolved = str(Path(repo_root).resolve())

    if resolved.startswith(repo_resolved):
        errors.append(
            f"Secret file path is inside repository: {path} "
            f"(resolves to {resolved}, repo is {repo_resolved})"
        )

    return errors


def reject_repo_env_files(path: str, repo_root: str = REPO_ROOT) -> bool:
    """Return True if the path is inside the repo (rejected)."""
    return len(validate_env_path_is_outside_repo(path, repo_root)) > 0


def _parse_env_lines(lines: list[str]) -> dict[str, str]:
    """Parse .env lines into key-value pairs. Internal use only."""
    result: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def load_env_file_keys_only(path: str = DEFAULT_SECRET_PATH) -> list[str]:
    """Load only the KEY names from a .env file. Never returns values."""
    errors = validate_env_path_is_outside_repo(path)
    if errors:
        return []

    try:
        with open(path) as f:
            lines = f.readlines()
    except (OSError, FileNotFoundError):
        return []

    parsed = _parse_env_lines(lines)
    return list(parsed.keys())


def has_secret(path: str, key: str) -> bool:
    """Check if a secret key exists in the .env file."""
    keys = load_env_file_keys_only(path)
    return key in keys


def get_secret_value_for_local_action(path: str, key: str) -> tuple[SecretUseStatus, str]:
    """Retrieve a secret value for use in an approved local action.

    WARNING: This function returns the actual secret value.
    It must ONLY be called inside approved deterministic action execution.
    The return value must NEVER be printed, logged, sent to model context,
    included in messages, or stored in memory.

    Returns (status, value). Value is empty string if unavailable.
    """
    errors = validate_env_path_is_outside_repo(path)
    if errors:
        return (SecretUseStatus.UNAVAILABLE, "")

    try:
        with open(path) as f:
            lines = f.readlines()
    except (OSError, FileNotFoundError):
        return (SecretUseStatus.UNAVAILABLE, "")

    parsed = _parse_env_lines(lines)
    if key not in parsed:
        return (SecretUseStatus.UNAVAILABLE, "")

    return (SecretUseStatus.AVAILABLE, parsed[key])


def _infer_scope_from_key(key: str) -> SecretScope:
    """Infer the secret scope from the key prefix."""
    upper_key = key.upper()
    for prefix, scope in SCOPE_PREFIX_MAP.items():
        if upper_key.startswith(prefix):
            return scope
    return SecretScope.GENERIC


def build_secret_ref_from_key(
    key: str,
    scope: SecretScope | None = None,
    account: str = "",
    path: str = DEFAULT_SECRET_PATH,
) -> SecretRef:
    """Build a SecretRef from a key name. Never includes the value."""
    if scope is None:
        scope = _infer_scope_from_key(key)

    available = has_secret(path, key)

    return SecretRef(
        key=key,
        scope=scope,
        account=account,
        backend=SecretBackendType.LOCAL_ENV,
        description=f"Local .env secret: {key}",
        available=available,
    )


def list_available_secret_refs(
    path: str = DEFAULT_SECRET_PATH,
    account: str = "",
) -> list[SecretRef]:
    """List all available secret refs (metadata only, no values)."""
    keys = load_env_file_keys_only(path)
    return [build_secret_ref_from_key(key, account=account, path=path) for key in keys]


def build_secret_availability_report(path: str = DEFAULT_SECRET_PATH) -> dict[str, Any]:
    """Build a report of secret availability. Never includes values."""
    keys = load_env_file_keys_only(path)
    return {
        "backend": SecretBackendType.LOCAL_ENV.value,
        "path": path,
        "keys_available": len(keys),
        "keys": keys,
        "values_included": False,
        "note": "Secret values are NEVER included in reports",
    }
