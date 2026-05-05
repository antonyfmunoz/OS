"""UMH Execution Environments — where execution runs.

Each execution is routed to an environment based on its capability type
and security requirements. Currently all execution runs locally — this
module makes that explicit and provides the extension point for future
container, sandbox, and remote execution.

Usage:
    from umh.execution.environment import select_environment

    env = select_environment(request)
    # env.id == "local"
    # env.env_type == EnvironmentType.LOCAL
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.execution.contract import ExecutionClass, ExecutionRequest

_log = logging.getLogger(__name__)


class EnforcementVerdict(str, Enum):
    """Result of environment enforcement check."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class EnforcementResult:
    """Outcome of enforce_environment() check."""

    verdict: EnforcementVerdict
    reason: str = ""


class EnvironmentType(str, Enum):
    """Where execution physically runs."""

    LOCAL = "local"
    SANDBOX = "sandbox"
    CONTAINER = "container"
    REMOTE = "remote"


class ExecutionMode(str, Enum):
    """Whether an environment has real execution backing."""

    REAL = "real"
    SIMULATED = "simulated"
    NOT_IMPLEMENTED = "not_implemented"


class SecurityLevel(str, Enum):
    """Security posture of an environment."""

    TRUSTED = "trusted"
    SANDBOXED = "sandboxed"
    ISOLATED = "isolated"


@dataclass(frozen=True)
class EnvironmentSpec:
    """Describes an execution environment."""

    id: str
    env_type: EnvironmentType
    supported_capabilities: frozenset[str]
    security_level: SecurityLevel
    execution_mode: ExecutionMode = ExecutionMode.REAL
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, capability_type: str) -> bool:
        return capability_type in self.supported_capabilities


_LOCAL_ENV = EnvironmentSpec(
    id="local",
    env_type=EnvironmentType.LOCAL,
    supported_capabilities=frozenset(
        {
            "llm_call",
            "shell_command",
            "file_operation",
            "computer_use",
        }
    ),
    security_level=SecurityLevel.TRUSTED,
    execution_mode=ExecutionMode.REAL,
)

_SANDBOX_ENV = EnvironmentSpec(
    id="sandbox",
    env_type=EnvironmentType.SANDBOX,
    supported_capabilities=frozenset(
        {
            "file_operation",
            "shell_command",
        }
    ),
    security_level=SecurityLevel.SANDBOXED,
    execution_mode=ExecutionMode.SIMULATED,
)

_CONTAINER_ENV = EnvironmentSpec(
    id="container",
    env_type=EnvironmentType.CONTAINER,
    supported_capabilities=frozenset(
        {
            "browser_action",
            "shell_command",
        }
    ),
    security_level=SecurityLevel.ISOLATED,
    execution_mode=ExecutionMode.NOT_IMPLEMENTED,
)

_ENVIRONMENTS: dict[str, EnvironmentSpec] = {
    "local": _LOCAL_ENV,
    "sandbox": _SANDBOX_ENV,
    "container": _CONTAINER_ENV,
}

_FILE_OPERATIONS = frozenset({"file_read", "file_list", "file_stat", "file_write", "file_delete"})


def requires_real_execution(request: ExecutionRequest) -> bool:
    """Determine whether a request needs a REAL execution environment.

    All concrete operations require real backing. Only explicitly marked
    dry-run/plan-only operations in PURE class may tolerate simulation.
    """
    if request.execution_class == ExecutionClass.PURE:
        return not request.inputs.get("dry_run", False)
    return True


def _classify_capability(request: ExecutionRequest) -> str:
    """Map request to capability type string for environment matching."""
    if request.execution_class == ExecutionClass.LLM_CALL:
        return "llm_call"
    if request.operation == "shell_command":
        return "shell_command"
    if request.operation in _FILE_OPERATIONS:
        return "file_operation"
    if request.operation.startswith("browser_"):
        return "browser_action"
    if request.operation.startswith("computer_"):
        return "computer_use"
    if request.operation.startswith("os_"):
        return "os_interaction"
    return request.execution_class.value


def enforce_environment(
    request: ExecutionRequest, environment: EnvironmentSpec
) -> EnforcementResult:
    """Check whether a request is allowed to execute in the given environment.

    Enforces capability support, sandbox constraints, and security level
    compatibility. This runs BEFORE execution and BEFORE scoring.
    """
    capability = _classify_capability(request)

    if capability not in environment.supported_capabilities:
        return EnforcementResult(
            verdict=EnforcementVerdict.DENY,
            reason=f"Environment '{environment.id}' does not support capability '{capability}'",
        )

    if request.constraints.sandbox and environment.security_level == SecurityLevel.TRUSTED:
        if request.operation in _FILE_OPERATIONS:
            return EnforcementResult(
                verdict=EnforcementVerdict.DENY,
                reason=f"Sandbox required but environment '{environment.id}' is trusted (not sandboxed)",
            )

    if request.execution_class == ExecutionClass.SIDE_EFFECT:
        if environment.security_level not in (
            SecurityLevel.TRUSTED,
            SecurityLevel.SANDBOXED,
            SecurityLevel.ISOLATED,
        ):
            return EnforcementResult(
                verdict=EnforcementVerdict.DENY,
                reason=f"Side-effect execution requires a recognized security level",
            )

    if requires_real_execution(request) and environment.execution_mode != ExecutionMode.REAL:
        return EnforcementResult(
            verdict=EnforcementVerdict.DENY,
            reason=(
                f"Environment '{environment.id}' has no real execution backing "
                f"(mode={environment.execution_mode.value})"
            ),
        )

    return EnforcementResult(verdict=EnforcementVerdict.ALLOW)


def select_environment(request: ExecutionRequest) -> EnvironmentSpec:
    """Select the best execution environment for a request.

    Pipeline:
    1. Build candidate list from all registered environments
    2. Filter by enforce_environment() — only ALLOW verdicts pass
    3. If 0 candidates: return local (fallback, enforcement logged)
    4. If 1 candidate: return it
    5. If >1 candidates: use scoring to pick the best, fallback to local
    """
    capability = _classify_capability(request)
    candidates: list[EnvironmentSpec] = []
    selection_reason = ""

    for env in _ENVIRONMENTS.values():
        result = enforce_environment(request, env)
        if result.verdict == EnforcementVerdict.ALLOW:
            candidates.append(env)

    if not candidates:
        local_enforcement = enforce_environment(request, _LOCAL_ENV)
        if local_enforcement.verdict == EnforcementVerdict.ALLOW:
            _log.warning(
                "No environment passed enforcement for op=%s capability=%s — falling back to local",
                request.operation,
                capability,
            )
            return _LOCAL_ENV
        _log.warning(
            "No valid environment for op=%s capability=%s (local also denied: %s)",
            request.operation,
            capability,
            local_enforcement.reason,
        )
        return _LOCAL_ENV

    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates — prefer sandbox for sandboxed file ops
    if request.operation in _FILE_OPERATIONS and request.constraints.sandbox:
        for c in candidates:
            if c.env_type == EnvironmentType.SANDBOX:
                return c

    # Multiple candidates — use scoring if available, but only if
    # the winner differs from local and has meaningful data.
    # NOT_IMPLEMENTED environments never win scoring.
    try:
        from umh.execution.scoring import get_capability_scorer

        scorer = get_capability_scorer()
        best = None
        best_score = -1.0

        for c in candidates:
            if c.execution_mode == ExecutionMode.NOT_IMPLEMENTED:
                continue
            stats = scorer.get_env_stats(capability, c.env_type.value)
            if stats.total_calls < 5:
                continue
            score = stats.success_rate * 1000.0 - stats.avg_latency_ms
            if score > best_score:
                best_score = score
                best = c

        if best is not None:
            _log.debug(
                "Scoring selected environment '%s' for %s (score=%.1f)",
                best.id,
                capability,
                best_score,
            )
            return best
    except Exception:
        pass

    # Default: prefer local when no scoring data differentiates
    for c in candidates:
        if c.env_type == EnvironmentType.LOCAL:
            return c
    return candidates[0]


def get_environment(env_id: str) -> EnvironmentSpec | None:
    """Look up an environment by ID."""
    return _ENVIRONMENTS.get(env_id)


def list_environments() -> list[EnvironmentSpec]:
    """Return all registered environments."""
    return list(_ENVIRONMENTS.values())
