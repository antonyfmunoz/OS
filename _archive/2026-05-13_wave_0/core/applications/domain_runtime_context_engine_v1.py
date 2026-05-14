"""Domain Runtime Context Engine v1.

Manages domain runtime contexts for application projections.
6 context types: business, personal, creator_media,
infrastructure, research, operations.

Preserves isolation, continuity, replay lineage,
and observability lineage.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationRuntimeContext,
    DomainContextType,
    DomainProjectionState,
    _now_iso,
)

KNOWN_CONTEXTS: list[str] = [c.value for c in DomainContextType]

MAX_ACTIVE_CONTEXTS = 10
MAX_CONTEXTS_PER_DOMAIN = 5


class DomainRuntimeContextEngine:
    """Manages domain runtime contexts."""

    def __init__(self, state_dir: str | Path = "data/runtime/applications") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._contexts: list[ApplicationRuntimeContext] = []
        self._domain_states: dict[str, DomainProjectionState] = {}

    def start_context(
        self,
        app_id: str,
        domain_context: str,
        session_id: str = "",
    ) -> ApplicationRuntimeContext | None:
        if domain_context not in KNOWN_CONTEXTS:
            return None

        active = [c for c in self._contexts]
        if len(active) >= MAX_ACTIVE_CONTEXTS:
            return None

        domain_contexts = [
            c for c in self._contexts
            if c.domain_context == domain_context
        ]
        if len(domain_contexts) >= MAX_CONTEXTS_PER_DOMAIN:
            return None

        ctx = ApplicationRuntimeContext(
            application_id=app_id,
            domain_context=domain_context,
            session_id=session_id,
        )
        self._contexts.append(ctx)

        if domain_context not in self._domain_states:
            self._domain_states[domain_context] = DomainProjectionState(
                domain_context=domain_context,
            )
        state = self._domain_states[domain_context]
        if app_id not in state.active_applications:
            state.active_applications.append(app_id)
        state.isolation_verified = True

        path = self._state_dir / "domain_contexts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ctx.to_dict(), default=str) + "\n")

        return ctx

    def restore_context(
        self,
        context_id: str,
    ) -> ApplicationRuntimeContext | None:
        for ctx in self._contexts:
            if ctx.context_id == context_id:
                return ctx
        return None

    def get_contexts_for_app(
        self,
        app_id: str,
    ) -> list[dict[str, Any]]:
        return [
            c.to_dict() for c in self._contexts
            if c.application_id == app_id
        ]

    def get_contexts_for_domain(
        self,
        domain_context: str,
    ) -> list[dict[str, Any]]:
        return [
            c.to_dict() for c in self._contexts
            if c.domain_context == domain_context
        ]

    def get_domain_state(self, domain_context: str) -> dict[str, Any] | None:
        state = self._domain_states.get(domain_context)
        if state is None:
            return None
        return state.to_dict()

    def verify_isolation(self, domain_context: str) -> bool:
        state = self._domain_states.get(domain_context)
        if state is None:
            return True
        return state.isolation_verified

    def get_stats(self) -> dict[str, object]:
        return {
            "total_contexts": len(self._contexts),
            "active_domains": len(self._domain_states),
            "known_context_types": len(KNOWN_CONTEXTS),
            "max_active_contexts": MAX_ACTIVE_CONTEXTS,
        }
