"""
Hybrid Execution Target Policy v1 — deterministic target resolution.

Purpose
-------
Resolves which execution target (``"local"`` or ``"vps"``) a request should
use, based on the operating mode and optional metadata.  Pure, bounded,
deterministic — no network calls, no LLM classification, no hot-path imports.

Design rules
------------
- Builder mode defaults to **local** (development work).
- Product mode defaults to **vps** (user-facing runtime).
- Unknown mode defaults to **vps** (safe fallback).
- Product mode may **delegate** to local when explicitly enabled AND a
  deterministic trigger fires.  Delegation changes the target only — the
  mode and persona remain product-facing.
- Invalid / unrecognised target values clamp to the mode's default.

Env vars
--------
  EOS_BUILDER_DEFAULT_TARGET          "local" | "vps"  (default "local")
  EOS_PRODUCT_DEFAULT_TARGET          "vps" | "local"  (default "vps")
  EOS_PRODUCT_ALLOW_LOCAL_DELEGATION  "1" | "0"        (default "0")
  EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS  comma-separated  (default "")

This module imports NOTHING from the hot path (gateway, cognitive_loop,
model_router, agent_runtime, primitives).
"""

from __future__ import annotations

import os
from typing import Any, Optional

__all__ = [
    "POLICY_VERSION",
    "resolve_execution_target",
    "resolve_execution_policy",
    "should_delegate_product_to_local",
]

POLICY_VERSION = "v1"

_VALID_TARGETS = frozenset({"vps", "local"})

# ── defaults per mode ────────────────────────────────────────────────────────

_ENV_BUILDER_DEFAULT_TARGET = "EOS_BUILDER_DEFAULT_TARGET"
_ENV_PRODUCT_DEFAULT_TARGET = "EOS_PRODUCT_DEFAULT_TARGET"

_BUILDER_DEFAULT = "local"
_PRODUCT_DEFAULT = "vps"
_UNKNOWN_DEFAULT = "vps"

# ── product delegation ───────────────────────────────────────────────────────

_ENV_PRODUCT_ALLOW_LOCAL_DELEGATION = "EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"
_ENV_PRODUCT_LOCAL_DELEGATION_KEYWORDS = "EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"


def _flag_truthy(env_name: str) -> bool:
    return (os.getenv(env_name, "") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _clamp_target(raw: Optional[str], default: str) -> str:
    """Normalise a target string; return *default* if invalid."""
    val = (raw or "").strip().lower()
    if val in _VALID_TARGETS:
        return val
    return default


def _mode_default(mode: str) -> str:
    """Return the hard default for a mode (ignoring env overrides)."""
    if mode == "builder":
        return _BUILDER_DEFAULT
    if mode == "product":
        return _PRODUCT_DEFAULT
    return _UNKNOWN_DEFAULT


# ── public API ───────────────────────────────────────────────────────────────


def resolve_execution_target(
    mode: str,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """Return ``"local"`` or ``"vps"`` for *mode* + optional *metadata*.

    Resolution order:
      1. Product-mode delegation check (if enabled + keyword match).
      2. Env-var override for the mode's default target.
      3. Hard-coded mode default (builder→local, product→vps, unknown→vps).
    """
    hard_default = _mode_default(mode)

    # Env override for mode default (e.g. EOS_BUILDER_DEFAULT_TARGET=vps)
    if mode == "builder":
        env_override = os.getenv(_ENV_BUILDER_DEFAULT_TARGET)
    elif mode == "product":
        env_override = os.getenv(_ENV_PRODUCT_DEFAULT_TARGET)
    else:
        env_override = None

    base_target = _clamp_target(env_override, hard_default)

    # Product delegation: may flip target to local if allowed + triggered
    if mode == "product" and base_target == "vps":
        if should_delegate_product_to_local(metadata=metadata):
            return "local"

    return base_target


def resolve_execution_policy(
    mode: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return a full policy dict for observability.

    Shape::

        {
          "mode": str,
          "target": "local" | "vps",
          "hard_default": "local" | "vps",
          "env_override": str | None,
          "delegated_local": bool,
          "delegation_reason": str | None,
          "policy_version": "v1",
        }
    """
    hard_default = _mode_default(mode)

    if mode == "builder":
        env_raw = os.getenv(_ENV_BUILDER_DEFAULT_TARGET)
    elif mode == "product":
        env_raw = os.getenv(_ENV_PRODUCT_DEFAULT_TARGET)
    else:
        env_raw = None

    base_target = _clamp_target(env_raw, hard_default)
    delegated = False
    delegation_reason: Optional[str] = None

    if mode == "product" and base_target == "vps":
        delegated, delegation_reason = _check_delegation(metadata)
        if delegated:
            base_target = "local"

    return {
        "mode": mode,
        "target": base_target,
        "hard_default": hard_default,
        "env_override": env_raw,
        "delegated_local": delegated,
        "delegation_reason": delegation_reason,
        "policy_version": POLICY_VERSION,
    }


def should_delegate_product_to_local(
    text: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """Check whether product mode should delegate to local execution.

    Returns ``True`` only when ALL of:
      1. ``EOS_PRODUCT_ALLOW_LOCAL_DELEGATION`` is truthy.
      2. A deterministic trigger fires (keyword match in *text* or
         ``metadata["text"]``, or ``metadata["force_local"]`` is truthy).

    No fuzzy / LLM classification. Exact substring match only.
    """
    ok, _ = _check_delegation(metadata, text)
    return ok


def _check_delegation(
    metadata: Optional[dict[str, Any]] = None,
    text: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Internal: return (delegated, reason) tuple."""
    if not _flag_truthy(_ENV_PRODUCT_ALLOW_LOCAL_DELEGATION):
        return False, None

    # Explicit force flag in metadata
    if metadata and metadata.get("force_local"):
        return True, "metadata:force_local"

    # Keyword match against utterance text
    effective_text = text or (metadata or {}).get("text") or ""
    if not effective_text:
        return False, None

    raw_kw = (os.getenv(_ENV_PRODUCT_LOCAL_DELEGATION_KEYWORDS) or "").strip()
    if not raw_kw:
        return False, None

    lower_text = effective_text.lower()
    for kw in raw_kw.split(","):
        kw = kw.strip().lower()
        if kw and kw in lower_text:
            return True, f"keyword:{kw}"

    return False, None
