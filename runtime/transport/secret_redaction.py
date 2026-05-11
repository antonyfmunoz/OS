"""
Secret redaction utilities for Phase 94D.9S.

Ensures secret values never appear in logs, messages, reports,
or model context. Provides pattern-based and value-based redaction.

All output that could contain secrets passes through redaction
before being written to any observable channel.
"""

from __future__ import annotations

import re
from typing import Any

from eos_ai.transport.secret_broker_contracts import SecretRef


SECRET_KEY_PATTERNS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "private_key",
    "privatekey",
    "access_key",
    "auth_token",
    "cookie",
    "session_id",
    "session_key",
    "credential",
    "totp",
    "2fa",
    "mfa",
    "oauth",
    "refresh_token",
    "client_secret",
)

REDACTED_PLACEHOLDER = "[REDACTED]"

ENV_LINE_PATTERN = re.compile(
    r"^(\s*[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$"
)


def looks_like_secret_key(key: str) -> bool:
    """Check if a key name looks like it contains a secret value."""
    lower = key.lower()
    return any(pattern in lower for pattern in SECRET_KEY_PATTERNS)


def redact_env_line(line: str) -> str:
    """Redact the value portion of a KEY=VALUE line if key looks secret."""
    match = ENV_LINE_PATTERN.match(line)
    if not match:
        return line

    key_part = match.group(1)
    if looks_like_secret_key(key_part):
        return f"{key_part}={REDACTED_PLACEHOLDER}"

    return line


def redact_secret_values(text: str, known_secret_values: list[str]) -> str:
    """Replace any occurrence of known secret values in text with [REDACTED].

    This is the nuclear option — if a secret value somehow appears in output,
    this catches it before it reaches any observable channel.
    """
    result = text
    for value in known_secret_values:
        if value and len(value) >= 3:
            result = result.replace(value, REDACTED_PLACEHOLDER)
    return result


def redact_mapping(mapping: dict[str, Any], secret_keys: set[str] | None = None) -> dict[str, Any]:
    """Redact values in a dict where keys look like secrets or are in secret_keys."""
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        if secret_keys and key in secret_keys:
            redacted[key] = REDACTED_PLACEHOLDER
        elif looks_like_secret_key(key):
            redacted[key] = REDACTED_PLACEHOLDER
        elif isinstance(value, dict):
            redacted[key] = redact_mapping(value, secret_keys)
        else:
            redacted[key] = value
    return redacted


def safe_repr_secret_ref(secret_ref: SecretRef) -> str:
    """Safe string representation of a SecretRef — never includes value."""
    return (
        f"SecretRef(key='{secret_ref.key}', scope='{secret_ref.scope.value}', "
        f"account='{secret_ref.account}', available={secret_ref.available})"
    )


def redact_potential_secrets_in_output(text: str) -> str:
    """Heuristic redaction of lines that look like they contain secrets."""
    lines = text.split("\n")
    result = []
    for line in lines:
        result.append(redact_env_line(line))
    return "\n".join(result)
