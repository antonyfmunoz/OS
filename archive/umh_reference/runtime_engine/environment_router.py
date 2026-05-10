"""EnvironmentRouter — resolve WHERE to execute an action.

Maps ExecutableActions to execution environments based on
action_type, target, and domain. Pure resolution — no side
effects, no I/O, no execution.

Pipeline position:
    ExecutableAction → EnvironmentRouter → ExecutionAdapter → Result

Usage::

    from umh.runtime_engine.environment_router import resolve_environment

    route = resolve_environment(action)
    # route.environment == ExecutionEnvironment.API
    # route.adapter_name == "mock_api"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ─── Environment enum ────────────────────────────────────────────


class ExecutionEnvironment(str, Enum):
    LOCAL = "LOCAL"
    API = "API"
    HUMAN = "HUMAN"
    TOOL = "TOOL"
    UNKNOWN = "UNKNOWN"


# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvironmentRoute:
    """Resolved execution destination for an action."""

    environment: ExecutionEnvironment
    adapter_name: str
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "environment": self.environment.value,
            "adapter_name": self.adapter_name,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


NO_ROUTE = EnvironmentRoute(
    environment=ExecutionEnvironment.UNKNOWN,
    adapter_name="no_op",
    confidence=0.0,
    reason="no_resolution",
)


# ─── Type-based routing table ────────────────────────────────────

TYPE_ROUTES: dict[str, tuple[ExecutionEnvironment, str]] = {
    "API_CALL": (ExecutionEnvironment.API, "mock_api"),
    "MESSAGE": (ExecutionEnvironment.HUMAN, "human"),
    "TASK": (ExecutionEnvironment.LOCAL, "local"),
    "HUMAN_INSTRUCTION": (ExecutionEnvironment.HUMAN, "human"),
    "NO_OP": (ExecutionEnvironment.LOCAL, "no_op"),
}

# ─── Target overrides ────────────────────────────────────────────

TARGET_OVERRIDES: dict[str, tuple[ExecutionEnvironment, str]] = {
    "self": (ExecutionEnvironment.LOCAL, "local"),
    "human": (ExecutionEnvironment.HUMAN, "human"),
}

# ─── Domain overrides ────────────────────────────────────────────

DOMAIN_ENVIRONMENT_HINTS: dict[str, ExecutionEnvironment] = {
    "automation": ExecutionEnvironment.TOOL,
    "integration": ExecutionEnvironment.API,
}


# ─── Resolution ──────────────────────────────────────────────────


def resolve_environment(action: object) -> EnvironmentRoute:
    """Determine execution environment for an action.

    Resolution order:
    1. Target override (most specific)
    2. Domain hint
    3. Action type mapping
    4. UNKNOWN fallback
    """
    action_type = getattr(action, "action_type", "")
    target = getattr(action, "target", None) or ""
    domain = getattr(action, "domain", "") or ""

    # 1. Target override
    target_lower = target.lower() if target else ""
    if target_lower in TARGET_OVERRIDES:
        env, adapter = TARGET_OVERRIDES[target_lower]
        return EnvironmentRoute(
            environment=env,
            adapter_name=adapter,
            confidence=0.9,
            reason=f"target_override:{target_lower}",
        )

    # 2. Domain hint
    domain_lower = domain.lower() if domain else ""
    if domain_lower in DOMAIN_ENVIRONMENT_HINTS:
        env = DOMAIN_ENVIRONMENT_HINTS[domain_lower]
        adapter = _adapter_for_environment(env, action_type)
        return EnvironmentRoute(
            environment=env,
            adapter_name=adapter,
            confidence=0.7,
            reason=f"domain_hint:{domain_lower}",
        )

    # 3. Type mapping
    if action_type in TYPE_ROUTES:
        env, adapter = TYPE_ROUTES[action_type]
        return EnvironmentRoute(
            environment=env,
            adapter_name=adapter,
            confidence=0.8,
            reason=f"type_route:{action_type}",
        )

    # 4. Fallback
    return EnvironmentRoute(
        environment=ExecutionEnvironment.UNKNOWN,
        adapter_name="no_op",
        confidence=0.0,
        reason=f"no_route_for:{action_type or 'empty'}",
    )


def _adapter_for_environment(env: ExecutionEnvironment, action_type: str) -> str:
    """Select adapter name based on environment and action type."""
    if env == ExecutionEnvironment.LOCAL:
        return "local"
    if env == ExecutionEnvironment.API:
        return "mock_api"
    if env == ExecutionEnvironment.HUMAN:
        return "human"
    if env == ExecutionEnvironment.TOOL:
        return "tool"
    return "no_op"


if __name__ == "__main__":
    print("environment_router import OK")
