"""Shared Cockpit token normalization and comparison helpers."""

from __future__ import annotations

import hmac


def normalize_secret(value: object) -> str:
    """Normalize a configured or presented bearer/API token.

    Empty and whitespace-only values normalize to "", which callers must treat
    as invalid configuration or invalid credentials.
    """
    return str(value or "").strip()


def secret_configured(value: object) -> bool:
    return bool(normalize_secret(value))


def token_matches(presented: object, configured: object) -> bool:
    expected = normalize_secret(configured)
    actual = normalize_secret(presented)
    if not expected or not actual:
        return False
    return hmac.compare_digest(actual, expected)
