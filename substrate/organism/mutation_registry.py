"""MutationRegistry — canonical registry of executable mutation types.

Every mutation the organism can perform is registered here with its
risk profile, reversibility, required capabilities, blast radius,
timeout limits, and verification requirements.

The GovernedExecutionSpine consults this registry before executing
any ActionEnvelope. Unregistered mutations are rejected.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.action_envelope import (
    ActionType,
    BlastRadius,
    ReversibilityClass,
)
from substrate.organism.execution_modes import ExecutionMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MutationSpec:
    """Declares the governance profile for a mutation type."""

    name: str
    action_type: ActionType
    risk_level: str = "low"
    reversibility: ReversibilityClass = ReversibilityClass.FULLY_REVERSIBLE
    allowed_modes: tuple[ExecutionMode, ...] = (
        ExecutionMode.ASSISTED,
        ExecutionMode.AUTONOMOUS,
    )
    required_capabilities: tuple[str, ...] = ()
    verification_required: bool = True
    rollback_supported: bool = False
    blast_radius: BlastRadius = BlastRadius.LOCAL_RUNTIME
    timeout_seconds: float = 60.0
    max_retries: int = 0
    require_approval: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "action_type": self.action_type.value,
            "risk_level": self.risk_level,
            "reversibility": self.reversibility.value,
            "allowed_modes": [m.value for m in self.allowed_modes],
            "required_capabilities": list(self.required_capabilities),
            "verification_required": self.verification_required,
            "rollback_supported": self.rollback_supported,
            "blast_radius": self.blast_radius.value,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "require_approval": self.require_approval,
            "description": self.description,
        }


# ── Built-in mutation specs ─────────────────────────────────────────────────

LOG_ROTATION = MutationSpec(
    name="log_rotation",
    action_type=ActionType.FILESYSTEM,
    risk_level="low",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("filesystem",),
    verification_required=True,
    rollback_supported=False,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=60.0,
    description="Rotate large log files",
)

CONTAINER_RESTART = MutationSpec(
    name="container_restart",
    action_type=ActionType.CONTAINER,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("docker",),
    verification_required=True,
    rollback_supported=True,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=60.0,
    require_approval=True,
    description="Restart a Docker container",
)

RUNTIME_REFRESH = MutationSpec(
    name="runtime_refresh",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("docker",),
    verification_required=False,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    description="Refresh runtime availability data",
)

TEST_SUITE_RUN = MutationSpec(
    name="test_suite",
    action_type=ActionType.TEST,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("python",),
    verification_required=False,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=120.0,
    description="Run the organism test suite",
)

GRAPH_REBUILD = MutationSpec(
    name="graph_rebuild",
    action_type=ActionType.GRAPH,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("filesystem", "python"),
    verification_required=True,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=300.0,
    description="Rebuild codebase dependency graph",
)

BRANCH_CLEANUP = MutationSpec(
    name="branch_cleanup",
    action_type=ActionType.CLEANUP,
    risk_level="low",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("git",),
    verification_required=False,
    rollback_supported=False,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    description="Delete merged git branches",
)

DISK_CLEANUP = MutationSpec(
    name="disk_cleanup",
    action_type=ActionType.CLEANUP,
    risk_level="low",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("filesystem",),
    verification_required=False,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=60.0,
    description="Clean __pycache__ and rotated logs",
)

REPO_HEALTH_SCAN = MutationSpec(
    name="repo_health",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(
        ExecutionMode.OBSERVE,
        ExecutionMode.RECOMMEND,
        ExecutionMode.ASSISTED,
        ExecutionMode.AUTONOMOUS,
    ),
    verification_required=False,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    description="Read-only repo health scan",
)

DOCKER_HEALTH_SCAN = MutationSpec(
    name="docker_health",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(
        ExecutionMode.OBSERVE,
        ExecutionMode.RECOMMEND,
        ExecutionMode.ASSISTED,
        ExecutionMode.AUTONOMOUS,
    ),
    verification_required=False,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    description="Read-only Docker health scan",
)

RUNTIME_RECONCILIATION = MutationSpec(
    name="runtime_reconciliation",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("docker", "tmux"),
    verification_required=True,
    blast_radius=BlastRadius.MULTI_SERVICE,
    timeout_seconds=90.0,
    description="Reconcile runtime topology",
)

# ── Phase 6.2: Additional mutation specs for coverage ─────────────────────────

DOCKER_EXEC = MutationSpec(
    name="docker_exec",
    action_type=ActionType.CONTAINER,
    risk_level="high",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("docker",),
    verification_required=True,
    rollback_supported=False,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=60.0,
    require_approval=True,
    description="Execute a command inside a Docker container",
)

TMUX_SEND = MutationSpec(
    name="tmux_send",
    action_type=ActionType.PROCESS,
    risk_level="high",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("tmux",),
    verification_required=False,
    rollback_supported=False,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=30.0,
    require_approval=True,
    description="Send command to a tmux session",
)

SHELL_EXECUTE = MutationSpec(
    name="shell_execute",
    action_type=ActionType.PROCESS,
    risk_level="critical",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("shell",),
    verification_required=True,
    rollback_supported=False,
    blast_radius=BlastRadius.CLUSTER_WIDE,
    timeout_seconds=120.0,
    require_approval=True,
    description="Execute an arbitrary shell command",
)

PROCESS_KILL = MutationSpec(
    name="process_kill",
    action_type=ActionType.PROCESS,
    risk_level="critical",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("shell",),
    verification_required=False,
    rollback_supported=False,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=10.0,
    require_approval=True,
    description="Kill an operating system process",
)

GIT_MUTATE = MutationSpec(
    name="git_mutate",
    action_type=ActionType.STATE,
    risk_level="high",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("git",),
    verification_required=True,
    rollback_supported=True,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=60.0,
    require_approval=True,
    description="Mutating git operation (push, reset, merge, rebase)",
)

REMOTE_NODE_EXEC = MutationSpec(
    name="remote_node_exec",
    action_type=ActionType.PROCESS,
    risk_level="high",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("ssh",),
    verification_required=True,
    rollback_supported=False,
    blast_radius=BlastRadius.EXTERNAL,
    timeout_seconds=120.0,
    require_approval=True,
    description="Execute command on a remote node via SSH",
)

FILE_WRITE = MutationSpec(
    name="file_write",
    action_type=ActionType.FILESYSTEM,
    risk_level="medium",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED, ExecutionMode.AUTONOMOUS),
    required_capabilities=("filesystem",),
    verification_required=False,
    rollback_supported=False,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=30.0,
    description="Write or modify a file on disk",
)

FILE_DELETE = MutationSpec(
    name="file_delete",
    action_type=ActionType.FILESYSTEM,
    risk_level="medium",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("filesystem",),
    verification_required=False,
    rollback_supported=False,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=30.0,
    require_approval=True,
    description="Delete a file or directory",
)

SOUL_DOC_WRITE = MutationSpec(
    name="soul_doc_write",
    action_type=ActionType.FILESYSTEM,
    risk_level="high",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("filesystem",),
    verification_required=True,
    rollback_supported=True,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    require_approval=True,
    description="Create or modify an agent soul document",
)

SESSION_LAUNCH = MutationSpec(
    name="session_launch",
    action_type=ActionType.PROCESS,
    risk_level="high",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("tmux",),
    verification_required=True,
    rollback_supported=True,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=60.0,
    require_approval=True,
    description="Launch a new Claude or agent session",
)

DEPLOYMENT = MutationSpec(
    name="deployment",
    action_type=ActionType.DEPLOYMENT,
    risk_level="critical",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("docker", "git"),
    verification_required=True,
    rollback_supported=True,
    blast_radius=BlastRadius.MULTI_SERVICE,
    timeout_seconds=300.0,
    require_approval=True,
    description="Deploy code or configuration to production",
)

CREDENTIAL_WRITE = MutationSpec(
    name="credential_write",
    action_type=ActionType.FILESYSTEM,
    risk_level="critical",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=(ExecutionMode.ASSISTED,),
    required_capabilities=("filesystem",),
    verification_required=True,
    rollback_supported=False,
    blast_radius=BlastRadius.CLUSTER_WIDE,
    timeout_seconds=30.0,
    require_approval=True,
    description="Write or modify credentials or secrets",
)


class MutationRegistry:
    """Registry of all executable mutation types.

    The GovernedExecutionSpine checks every ActionEnvelope against
    this registry. Unregistered mutation names are rejected.
    """

    def __init__(self) -> None:
        self._specs: dict[str, MutationSpec] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        for spec in (
            LOG_ROTATION,
            CONTAINER_RESTART,
            RUNTIME_REFRESH,
            TEST_SUITE_RUN,
            GRAPH_REBUILD,
            BRANCH_CLEANUP,
            DISK_CLEANUP,
            REPO_HEALTH_SCAN,
            DOCKER_HEALTH_SCAN,
            RUNTIME_RECONCILIATION,
            DOCKER_EXEC,
            TMUX_SEND,
            SHELL_EXECUTE,
            PROCESS_KILL,
            GIT_MUTATE,
            REMOTE_NODE_EXEC,
            FILE_WRITE,
            FILE_DELETE,
            SOUL_DOC_WRITE,
            SESSION_LAUNCH,
            DEPLOYMENT,
            CREDENTIAL_WRITE,
        ):
            self.register(spec)

    def register(self, spec: MutationSpec) -> None:
        if spec.name in self._specs:
            logger.warning("overwriting mutation spec: %s", spec.name)
        self._specs[spec.name] = spec
        logger.debug("mutation registered: %s (risk=%s)", spec.name, spec.risk_level)

    def lookup(self, name: str) -> MutationSpec | None:
        return self._specs.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._specs

    def all_specs(self) -> list[MutationSpec]:
        return list(self._specs.values())

    def specs_by_risk(self, risk: str) -> list[MutationSpec]:
        return [s for s in self._specs.values() if s.risk_level == risk]

    def specs_by_type(self, action_type: ActionType) -> list[MutationSpec]:
        return [s for s in self._specs.values() if s.action_type == action_type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_specs": len(self._specs),
            "specs": {name: spec.to_dict() for name, spec in self._specs.items()},
            "by_risk": {
                risk: len(self.specs_by_risk(risk))
                for risk in ("low", "medium", "high", "critical")
            },
        }
