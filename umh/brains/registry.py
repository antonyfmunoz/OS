"""Brain registry — stores and retrieves brain profiles + expression state.

In-memory registry. One substrate, many expressed brains.
Brains are views, not databases. The registry stores identity (BrainProfile)
and epigenetic config (ExpressionState), nothing else.

No imports from execution engine, adapters, tools, or shell.
Event publishing is best-effort — failures never break core operations.
"""

from __future__ import annotations

import threading
from typing import Any

from umh.brains.profile import (
    AuthorityLevel,
    BrainProfile,
    ExpressionState,
)
from umh.core.clock import iso_now as _iso_now


# ─── Registry state ─────────────────────────────────────────────────────

_lock = threading.Lock()
_profiles: dict[str, BrainProfile] = {}
_expression_states: dict[str, ExpressionState] = {}


def _publish(event_type: str, payload: dict[str, Any]) -> None:
    """Best-effort event publishing — never crashes."""
    try:
        from umh.events.stream import publish

        publish(event_type, payload=payload, actor_id="brain_registry")
    except Exception:
        pass


# ─── Core CRUD ───────────────────────────────────────────────────────────


def register(
    profile: BrainProfile,
    expression_state: ExpressionState | None = None,
) -> None:
    """Register a brain profile and optional expression state."""
    with _lock:
        _profiles[profile.brain_id] = profile
        if expression_state is not None:
            _expression_states[profile.brain_id] = expression_state
        elif profile.brain_id not in _expression_states:
            _expression_states[profile.brain_id] = ExpressionState(
                brain_id=profile.brain_id,
                inherited_from=profile.parent_brain_id,
            )

    _publish(
        "brain.registered",
        {
            "brain_id": profile.brain_id,
            "name": profile.name,
            "brain_type": profile.brain_type,
            "parent": profile.parent_brain_id,
        },
    )


# Backward compat alias
register_brain = register


def get(brain_id: str) -> BrainProfile | None:
    with _lock:
        return _profiles.get(brain_id)


# Backward compat alias
get_profile = get


def list_all() -> list[BrainProfile]:
    with _lock:
        return list(_profiles.values())


def list_brains() -> list[str]:
    """Return all registered brain IDs."""
    with _lock:
        return list(_profiles.keys())


def children(parent_brain_id: str) -> list[BrainProfile]:
    """Return all direct children of a parent brain."""
    with _lock:
        return [p for p in _profiles.values() if p.parent_brain_id == parent_brain_id]


# ─── Expression state ───────────────────────────────────────────────────


def get_expression(brain_id: str) -> ExpressionState | None:
    with _lock:
        return _expression_states.get(brain_id)


# Backward compat alias
get_expression_state = get_expression


def update_expression(brain_id: str, state: ExpressionState) -> None:
    with _lock:
        _expression_states[brain_id] = state


# Backward compat alias
update_expression_state = update_expression


def apply_correction(brain_id: str, correction: dict[str, Any]) -> bool:
    """Apply an epigenetic correction to a brain's expression state.

    Returns True if applied, False if brain not found.
    Modifies expression state ONLY — never touches substrate.
    """
    with _lock:
        state = _expression_states.get(brain_id)
        if state is None:
            return False
        state.apply_correction(correction)

    _publish(
        "brain.correction_applied",
        {
            "brain_id": brain_id,
            "correction_type": correction.get("type", "unknown"),
            "checkpoint_version": state.checkpoint_version,
        },
    )
    return True


# ─── Inheritance ─────────────────────────────────────────────────────────


def create_child(
    parent_brain_id: str,
    name: str,
    brain_type: str = "project",
    *,
    overrides: dict[str, Any] | None = None,
) -> BrainProfile | None:
    """Create a child brain inheriting parent expression state.

    Returns None if parent not found.
    overrides can contain: scope, authority, active_primitives,
    retrieval_weights, tool_permissions, metadata.
    """
    with _lock:
        parent = _profiles.get(parent_brain_id)
        if parent is None:
            return None

        parent_expr = _expression_states.get(parent_brain_id)

        ov = overrides or {}
        child_id = ov.get("brain_id", f"{parent_brain_id}.{name.lower().replace(' ', '_')}")

        authority = ov.get("authority", parent.authority)
        if isinstance(authority, str):
            authority = AuthorityLevel(authority)

        child = BrainProfile(
            brain_id=child_id,
            name=name,
            brain_type=brain_type,
            parent_brain_id=parent_brain_id,
            scope=ov.get("scope", dict(parent.scope)),
            authority=authority,
            active_primitives=tuple(ov.get("active_primitives", parent.active_primitives)),
            retrieval_weights=ov.get("retrieval_weights", dict(parent.retrieval_weights)),
            tool_permissions=tuple(ov.get("tool_permissions", parent.tool_permissions)),
            metadata=ov.get("metadata", {}),
            amplified_concepts=frozenset(ov.get("amplified_concepts", parent.amplified_concepts)),
            silenced_concepts=frozenset(ov.get("silenced_concepts", parent.silenced_concepts)),
            preferred_patterns=tuple(ov.get("preferred_patterns", parent.preferred_patterns)),
        )

        _profiles[child.brain_id] = child

        if parent_expr:
            child_expr = ExpressionState.inherit(parent_expr, child.brain_id)
        else:
            child_expr = ExpressionState(
                brain_id=child.brain_id,
                inherited_from=parent_brain_id,
            )
        _expression_states[child.brain_id] = child_expr

    _publish(
        "brain.child_created",
        {
            "child_id": child.brain_id,
            "parent_id": parent_brain_id,
            "brain_type": brain_type,
        },
    )
    return child


def resolve_with_inheritance(brain_id: str) -> BrainProfile | None:
    """Resolve a brain profile with parent inheritance applied.

    Child's explicit values override parent. Amplified/silenced
    concepts are unioned. Retrieval weights are merged (child wins).
    """
    with _lock:
        profile = _profiles.get(brain_id)
        if profile is None:
            return None

        if profile.parent_brain_id is None:
            return profile

        parent = _profiles.get(profile.parent_brain_id)
        if parent is None:
            return profile

        merged_weights = {**parent.retrieval_weights, **profile.retrieval_weights}
        merged_amplified = parent.amplified_concepts | profile.amplified_concepts
        merged_silenced = parent.silenced_concepts | profile.silenced_concepts
        merged_primitives = parent.active_primitives + tuple(
            p for p in profile.active_primitives if p not in parent.active_primitives
        )
        merged_patterns = parent.preferred_patterns + tuple(
            p for p in profile.preferred_patterns if p not in parent.preferred_patterns
        )

        return BrainProfile(
            brain_id=profile.brain_id,
            name=profile.name,
            brain_type=profile.brain_type,
            authority=profile.authority,
            active_primitives=merged_primitives,
            amplified_concepts=merged_amplified,
            silenced_concepts=merged_silenced,
            preferred_patterns=merged_patterns,
            retrieval_weights=merged_weights,
            parent_brain_id=profile.parent_brain_id,
            scope={**parent.scope, **profile.scope},
            tool_permissions=profile.tool_permissions or parent.tool_permissions,
            metadata={**parent.metadata, **profile.metadata},
        )


# ─── Default brains ─────────────────────────────────────────────────────


def ensure_default_brains(project_metadata: dict[str, Any] | None = None) -> list[str]:
    """Create default brain identities if not already present.

    Idempotent — safe to call multiple times.
    Returns list of brain_ids that were created (empty if all existed).
    """
    created: list[str] = []

    defaults = [
        BrainProfile(
            brain_id="system",
            name="System",
            brain_type="system",
            authority=AuthorityLevel.ADMIN,
            active_primitives=("state", "constraint", "signal", "feedback"),
        ),
        BrainProfile(
            brain_id="user",
            name="User",
            brain_type="user",
            authority=AuthorityLevel.APPROVE,
            active_primitives=("goal", "action", "outcome"),
        ),
        BrainProfile(
            brain_id="claude_code",
            name="Claude Code",
            brain_type="agent",
            parent_brain_id="system",
            authority=AuthorityLevel.EXECUTE,
            active_primitives=("action", "change", "resource"),
        ),
        BrainProfile(
            brain_id="workstation",
            name="Workstation",
            brain_type="workstation",
            parent_brain_id="system",
            authority=AuthorityLevel.OBSERVE,
            active_primitives=("state", "signal"),
        ),
    ]

    if project_metadata:
        defaults.append(
            BrainProfile(
                brain_id="project",
                name=project_metadata.get("name", "Project"),
                brain_type="project",
                parent_brain_id="system",
                authority=AuthorityLevel.PROPOSE,
                scope=project_metadata,
                active_primitives=("goal", "constraint", "resource"),
            )
        )

    with _lock:
        for profile in defaults:
            if profile.brain_id not in _profiles:
                _profiles[profile.brain_id] = profile
                _expression_states[profile.brain_id] = ExpressionState(
                    brain_id=profile.brain_id,
                    inherited_from=profile.parent_brain_id,
                )
                created.append(profile.brain_id)

    for bid in created:
        _publish("brain.default_created", {"brain_id": bid})

    return created


# ─── Singleton accessor ─────────────────────────────────────────────────

_registry_instance = None
_registry_lock = threading.Lock()


class BrainRegistry:
    """Object-oriented wrapper for module-level functions.

    Exists for callers that prefer an instance interface.
    All methods delegate to module-level functions.
    """

    def register(
        self, profile: BrainProfile, expression_state: ExpressionState | None = None
    ) -> None:
        register(profile, expression_state)

    def get(self, brain_id: str) -> BrainProfile | None:
        return get(brain_id)

    def list(self) -> list[BrainProfile]:
        return list_all()

    def children(self, parent_brain_id: str) -> list[BrainProfile]:
        return children(parent_brain_id)

    def create_child(
        self, parent_brain_id: str, name: str, brain_type: str = "project", **kw
    ) -> BrainProfile | None:
        return create_child(parent_brain_id, name, brain_type, **kw)

    def get_expression(self, brain_id: str) -> ExpressionState | None:
        return get_expression(brain_id)

    def update_expression(self, brain_id: str, state: ExpressionState) -> None:
        update_expression(brain_id, state)

    def apply_correction(self, brain_id: str, correction: dict[str, Any]) -> bool:
        return apply_correction(brain_id, correction)

    def reset(self) -> None:
        clear()


def get_brain_registry() -> BrainRegistry:
    """Get the singleton BrainRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = BrainRegistry()
    return _registry_instance


# ─── Test helper ─────────────────────────────────────────────────────────


def clear() -> None:
    """Reset registry — for testing only."""
    with _lock:
        _profiles.clear()
        _expression_states.clear()


# Backward compat alias
reset = clear
