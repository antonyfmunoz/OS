"""
Discord Channel Mode Routing v1 — bounded channel→mode classification.

Purpose
-------
EOS exposes two operating modes on Discord, selected by which channel a
message lands in:

  - builder  : internal / dev / substrate-development lane. Used to update
               EOS itself. Full dev context, code, workflows, system ops.
  - product  : user-facing / SaaS-runtime lane. Behaves like EOS as a
               product — may still call local/VPS Claude sessions, tools,
               skills, workflows behind the scenes, but must preserve
               product-facing context, behavior, and output style.

CRITICAL INVARIANT
------------------
There is exactly ONE substrate and ONE broader router. Mode is metadata
that rides through the existing pipeline; it is NOT a second cognition
system. Both modes still flow through:

    Discord → discord_text_transport → inject_transcript
            → VoiceSessionRuntime.submit_utterance
            → voice_eos_responder → model_router.call_with_fallback

Mode affects ONLY:
  - session mapping (which persistent Claude tmux session to target)
  - routing metadata (observability)
  - responder target (vps | local)

Mode does NOT affect:
  - the router itself
  - the substrate itself
  - TTS sanitization / footer split behavior
  - the Claude CLI backend priority

Env vars (all default OFF / unknown)
------------------------------------
  EOS_DISCORD_BUILDER_CHANNELS    comma-separated channel ids
  EOS_DISCORD_PRODUCT_CHANNELS    comma-separated channel ids
  EOS_DISCORD_BUILDER_TARGET      "vps" | "local"   (default "vps")
  EOS_DISCORD_BUILDER_SESSION     session name      (default "dex_builder_main")
  EOS_DISCORD_PRODUCT_TARGET      "vps" | "local"   (default "vps")
  EOS_DISCORD_PRODUCT_SESSION     session name      (default "dex_product_main")
  EOS_DISCORD_MODE_PER_CHANNEL    truthy → suffix session name with channel id

Resolution rules
----------------
- Exact-match only. No fuzzy logic.
- A channel id listed in BUILDER_CHANNELS resolves to "builder".
- A channel id listed in PRODUCT_CHANNELS resolves to "product".
- A channel id in both lists → "builder" wins (dev intent is explicit).
- Any other channel (including None) → "unknown".

Unknown mode is a safe no-op: callers should treat it exactly like the
pre-mode-routing path (shared defaults from model_router env vars).

This module imports NOTHING from the hot path (gateway, cognitive_loop,
model_router, agent_runtime, primitives). It is a pure, bounded helper.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Optional

LAYER_NAME = "discord_mode_routing"
LAYER_VERSION = "v1.1"

MODE_BUILDER = "builder"
MODE_PRODUCT = "product"
MODE_UNKNOWN = "unknown"

_VALID_MODES = frozenset({MODE_BUILDER, MODE_PRODUCT, MODE_UNKNOWN})

_ENV_BUILDER_CHANNELS = "EOS_DISCORD_BUILDER_CHANNELS"
_ENV_PRODUCT_CHANNELS = "EOS_DISCORD_PRODUCT_CHANNELS"
_ENV_BUILDER_TARGET = "EOS_DISCORD_BUILDER_TARGET"
_ENV_BUILDER_SESSION = "EOS_DISCORD_BUILDER_SESSION"
_ENV_PRODUCT_TARGET = "EOS_DISCORD_PRODUCT_TARGET"
_ENV_PRODUCT_SESSION = "EOS_DISCORD_PRODUCT_SESSION"
_ENV_PER_CHANNEL = "EOS_DISCORD_MODE_PER_CHANNEL"

_DEFAULT_BUILDER_SESSION = "dex_builder_main"
_DEFAULT_PRODUCT_SESSION = "dex_product_main"
_DEFAULT_TARGET = "vps"
_VALID_TARGETS = frozenset({"vps", "local"})


def _parse_id_set(env_name: str) -> set[str]:
    raw = os.getenv(env_name, "") or ""
    return {tok.strip() for tok in raw.split(",") if tok.strip()}


def _flag_truthy(env_name: str) -> bool:
    return (os.getenv(env_name, "") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _norm_target(raw: Optional[str]) -> str:
    val = (raw or "").strip().lower()
    if val in _VALID_TARGETS:
        return val
    return _DEFAULT_TARGET


def resolve_discord_mode(
    guild_id: Optional[Any],
    channel_id: Optional[Any],
) -> str:
    """Classify a Discord (guild, channel) into a substrate mode.

    Returns one of: "builder" | "product" | "unknown".

    Exact-match allowlists only. Builder wins if a channel appears in
    both lists.
    """
    if channel_id is None:
        return MODE_UNKNOWN
    cid = str(channel_id).strip()
    if not cid:
        return MODE_UNKNOWN

    builder_ids = _parse_id_set(_ENV_BUILDER_CHANNELS)
    product_ids = _parse_id_set(_ENV_PRODUCT_CHANNELS)

    if cid in builder_ids:
        return MODE_BUILDER
    if cid in product_ids:
        return MODE_PRODUCT
    return MODE_UNKNOWN


def resolve_mode_session(
    mode: str,
    guild_id: Optional[Any] = None,
    channel_id: Optional[Any] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Resolve {target, session_name, mode, policy} for a given mode.

    Returns a dict:
        {
          "mode":              "builder" | "product" | "unknown",
          "target":            "vps" | "local",
          "session_name":      <string>,
          "source":            "default" | "override" | "delegated",
          "delegated_local":   bool,
          "delegation_reason": str | None,
          "policy_version":    str | None,
        }

    For "unknown", returns mode="unknown" with no target/session override
    — callers MUST treat this as "use the router's env-level defaults".

    Target resolution uses the hybrid execution target policy
    (``target_policy.resolve_execution_policy``).  Builder defaults to
    local, product defaults to vps, product may delegate to local when
    explicitly enabled.
    """
    if mode not in _VALID_MODES:
        mode = MODE_UNKNOWN

    if mode == MODE_UNKNOWN:
        return {
            "mode": MODE_UNKNOWN,
            "target": None,
            "session_name": None,
            "source": "default",
            "delegated_local": False,
            "delegation_reason": None,
            "policy_version": None,
        }

    # ── target resolution via target_policy ──────────────────────────────
    from substrate.execution.bridge.target_policy import resolve_execution_policy

    policy = resolve_execution_policy(mode, metadata=metadata)
    target = policy["target"]
    delegated_local = policy["delegated_local"]
    delegation_reason = policy.get("delegation_reason")

    # Per-mode env override still respected (backward compat):
    # If the mode-specific EOS_DISCORD_*_TARGET env is set, it takes
    # precedence over the policy default — but the policy's delegation
    # can still flip it.
    if mode == MODE_BUILDER:
        env_target_raw = os.getenv(_ENV_BUILDER_TARGET)
    else:
        env_target_raw = os.getenv(_ENV_PRODUCT_TARGET)

    # Determine source for observability
    if delegated_local:
        source = "delegated"
    elif env_target_raw and _norm_target(env_target_raw) != target:
        # env override changed the policy default
        target = _norm_target(env_target_raw)
        source = "override"
    else:
        source = "default"

    # ── session name resolution ──────────────────────────────────────────
    if mode == MODE_BUILDER:
        base = (
            os.getenv(_ENV_BUILDER_SESSION) or _DEFAULT_BUILDER_SESSION
        ).strip() or _DEFAULT_BUILDER_SESSION
    else:  # MODE_PRODUCT
        base = (
            os.getenv(_ENV_PRODUCT_SESSION) or _DEFAULT_PRODUCT_SESSION
        ).strip() or _DEFAULT_PRODUCT_SESSION

    per_channel = _flag_truthy(_ENV_PER_CHANNEL)
    if per_channel and channel_id is not None and str(channel_id).strip():
        session_name = f"{base}_{str(channel_id).strip()}"
    else:
        session_name = base

    return {
        "mode": mode,
        "target": target,
        "session_name": session_name,
        "source": source,
        "delegated_local": delegated_local,
        "delegation_reason": delegation_reason,
        "policy_version": policy.get("policy_version"),
    }


# ─── Thread-local mode context ───────────────────────────────────────────────
#
# Lets the Discord ingress layer inject mode routing decisions that the
# model_router's Claude CLI backend picks up WITHOUT changing call_with_fallback's
# signature. Scoped to the calling thread; cleared on exit of the context
# manager. If nothing is set, the router falls back to its existing env-var
# behavior (EOS_ROUTER_CLAUDE_CLI_TARGET / EOS_ROUTER_CLAUDE_CLI_SESSION).

_tls = threading.local()


def current_mode_context() -> Optional[dict[str, Any]]:
    """Return the current thread's mode context, or None if unset.

    Shape (when set)::

        {
          "mode":              "builder" | "product",
          "target":            "vps" | "local",
          "session_name":      <string>,
          "guild_id":          <string or None>,
          "channel_id":        <string or None>,
          "source":            "default" | "override" | "delegated",
          "delegated_local":   bool,
          "delegation_reason": str | None,
          "policy_version":    str | None,
        }
    """
    val = getattr(_tls, "mode_context", None)
    if val is None:
        return None
    return dict(val)


@contextmanager
def mode_context(
    mode: str,
    *,
    target: Optional[str] = None,
    session_name: Optional[str] = None,
    guild_id: Optional[Any] = None,
    channel_id: Optional[Any] = None,
    source: Optional[str] = None,
    delegated_local: bool = False,
    delegation_reason: Optional[str] = None,
    policy_version: Optional[str] = None,
):
    """Bind a mode context for the duration of the block.

    Unknown/None mode is a no-op — we do not poison the thread-local so the
    router keeps its env-default behavior.
    """
    if mode not in (MODE_BUILDER, MODE_PRODUCT):
        yield None
        return

    prev = getattr(_tls, "mode_context", None)
    ctx = {
        "mode": mode,
        "target": target,
        "session_name": session_name,
        "guild_id": str(guild_id) if guild_id is not None else None,
        "channel_id": str(channel_id) if channel_id is not None else None,
        "source": source or "default",
        "delegated_local": delegated_local,
        "delegation_reason": delegation_reason,
        "policy_version": policy_version,
    }
    _tls.mode_context = ctx
    try:
        yield ctx
    finally:
        if prev is None:
            try:
                del _tls.mode_context
            except AttributeError:
                pass
        else:
            _tls.mode_context = prev


def clear_mode_context_for_tests() -> None:
    """Test helper — clear any dangling thread-local state."""
    try:
        del _tls.mode_context
    except AttributeError:
        pass


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "MODE_BUILDER",
    "MODE_PRODUCT",
    "MODE_UNKNOWN",
    "resolve_discord_mode",
    "resolve_mode_session",
    "current_mode_context",
    "mode_context",
    "clear_mode_context_for_tests",
]
