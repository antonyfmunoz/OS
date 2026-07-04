"""Canonical operation runtime — the single declared mutation-submission entry.

WP-P1-001. This module *declares* the one canonical path from operator intent
to a governed state mutation:

    governed_mutation  →  MutationRouter  →  GovernedExecutionSpine

There is exactly one operation runtime. Rival work/command runtimes
(``GovernedWorkRuntime``, ``CommandRuntime``, and the organism loop's direct
``WorkPacketExecutor`` step) are *adapters* that, when routing is enabled,
submit their mutation-executing step into this canonical path instead of
governing (or executing) independently. They do not constitute a second
choke point.

This module holds no execution logic of its own — it is a declaration plus a
deterministic routing flag. It never imports transports/ or services/
(substrate dependency direction). The concrete router/spine are obtained from
the running daemon at call time by the adapter, exactly as the transport shim
does; this module only decides *whether* an adapter should route.

Design constraints (WP-P1-001):
- Deterministic-first: the flag is a plain env/default lookup, never an LLM.
- Fail-safe default: routing is OFF by default so deploying this packet is a
  no-op for running services until the flag is explicitly enabled. Every
  adapter preserves its exact prior behavior when routing is disabled, so
  rollback is "unset the flag" with no code revert.
- No new spine, no new approval store: this declares the existing canonical
  runtime; it does not create another one.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# The single canonical operation runtime, named once here so tests, docs, and
# adapters reference one string instead of re-deriving it.
CANONICAL_OPERATION_RUNTIME = "governed_mutation -> MutationRouter -> GovernedExecutionSpine"

# Env flag that enables adapter routing through the canonical runtime. Off by
# default: deploying WP-P1-001 changes no running behavior until this is set,
# so the staged cutover is controlled entirely by this switch.
_ROUTE_FLAG_ENV = "UMH_CANONICAL_RUNTIME_ROUTING"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def canonical_runtime_routing_enabled() -> bool:
    """Deterministic check: should adapters route their mutation step through
    the canonical governed runtime?

    Reads the ``UMH_CANONICAL_RUNTIME_ROUTING`` env var. Any of 1/true/yes/on
    (case-insensitive) enables routing; anything else (including unset) keeps
    the pre-P1-001 behavior. No LLM, no network — a pure lookup so the routing
    decision is part of the deterministic spine.
    """
    return os.environ.get(_ROUTE_FLAG_ENV, "").strip().lower() in _TRUTHY


def canonical_runtime_name() -> str:
    """Return the declared canonical operation runtime identifier."""
    return CANONICAL_OPERATION_RUNTIME
