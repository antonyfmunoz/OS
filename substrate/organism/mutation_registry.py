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
from dataclasses import dataclass
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
    # When the control plane (organism daemon) is unavailable, only a mutation
    # whose spec sets this True — AND which is low-risk and LOCAL_RUNTIME/LOCAL_FILE
    # in blast radius — may execute in degraded mode. Everything else fails closed.
    # Default False: absence of an explicit opt-in means "reject when ungoverned".
    degraded_mode_allowed: bool = False
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
            "degraded_mode_allowed": self.degraded_mode_allowed,
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
    degraded_mode_allowed=True,
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
    degraded_mode_allowed=True,
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


# ── API-layer mutation specs (C34) ────────────────────────────────────────────
# Operator-initiated mutations work in any execution mode.
_ALL_MODES = (
    ExecutionMode.OBSERVE,
    ExecutionMode.RECOMMEND,
    ExecutionMode.ASSISTED,
    ExecutionMode.AUTONOMOUS,
)

SETTINGS_UPDATE = MutationSpec(
    name="settings_update",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Update a system or user setting",
)

CONFIG_SET = MutationSpec(
    name="config_set",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Set a configuration value",
)

APPROVAL_DECIDE = MutationSpec(
    name="approval_decide",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Approve or reject a pending action",
)

EOS_ACTION_PROPOSAL_DECISION = MutationSpec(
    name="eos_action_proposal_decision",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.EXTERNAL,
    timeout_seconds=15.0,
    description=(
        "Approve or reject a pending EOS agent action proposal — bounded UPDATE "
        "of one agent_actions row via the approve-reject-decision seam "
        "(decider is the authenticated operator; never executes the action)"
    ),
)

EOS_ACTION_PROPOSAL_EXECUTE = MutationSpec(
    name="eos_action_proposal_execute",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.EXTERNAL,
    timeout_seconds=30.0,
    description=(
        "Execute an approved EOS action proposal through the executor seam — "
        "atomic approved→executing claim, non-provider allowlist "
        "(create_task/create_document) writes in the EOS app database"
    ),
)

INTENT_LOOP_SUBMIT = MutationSpec(
    name="intent_loop_submit",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    # LOW risk + LOCAL_FILE + degraded opt-in: the P4S-31B operator-submit gate
    # captures one bounded operator intent as substrate-owned JSON state
    # (<runtime-state>/operator/intent_loop/) at AWAITING_APPROVAL. The write is
    # governed (never an ungoverned append); the gate HOLDS — submission never
    # auto-advances past AWAITING_APPROVAL. Degraded opt-in keeps the capture
    # REAL-governed even when the organism daemon is down (mandatory degraded
    # audit record). Never dispatches, executes a provider, or writes a
    # projection DB.
    degraded_mode_allowed=True,
    description=(
        "Capture one P4S-31B operator intent → deterministic IntentSpec + "
        "WorkPacketDraft → bounded substrate-owned JSON state at "
        "AWAITING_APPROVAL (the gate HOLDS; never auto-advances, never "
        "dispatches, executes, or writes a projection DB)"
    ),
)

INTENT_LOOP_APPROVAL_DECISION = MutationSpec(
    name="intent_loop_approval_decision",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    # LOW risk + LOCAL_FILE + degraded opt-in: the P4S-31 MVP operating-loop
    # approval gate writes ONLY substrate-owned JSON state
    # (<runtime-state>/operator/intent_loop/). Opting into degraded mode lets the
    # gate stay REAL-governed even when the organism daemon is down — the
    # fail-closed router still emits a mandatory degraded audit record. It is
    # never a provider action, projection-DB write, or non-local mutation.
    degraded_mode_allowed=True,
    description=(
        "Approve or reject one P4S-31 MVP operating-loop packet draft — bounded "
        "substrate-owned JSON state transition (AWAITING_APPROVAL → APPROVED/"
        "REJECTED → PROOF_RECORDED); never dispatches, executes, or writes a "
        "projection DB"
    ),
)

OBJECTIVE_GOAL_WRITE = MutationSpec(
    name="objective_goal_write",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    # LOW risk + LOCAL_FILE + degraded opt-in: Wave 1 canonical Objective
    # identity writes — GoalRegistry create-or-reuse / CAS update of one
    # Goal(OBJECTIVE) record beneath the runtime-state boundary
    # (<runtime-state>/strategic_gaps/goals.jsonl). Idempotent under
    # tenant_id + objective_key + scope_hash; never dispatches, executes,
    # or writes a projection DB.
    degraded_mode_allowed=True,
    description=(
        "Create-or-reuse / update one canonical Objective Goal record via "
        "GoalRegistry (idempotent, versioned, locked JSONL beneath the "
        "runtime-state boundary; never dispatches or executes)"
    ),
)

OBJECTIVE_PLAN_ASSESS = MutationSpec(
    name="objective_plan_assess",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=15.0,
    verification_required=False,
    degraded_mode_allowed=True,
    description=(
        "Assess one Cockpit objective message: planning session + intent "
        "assessment + bounded grounding snapshot, JSONL state under "
        "<runtime-state>/operator/objective_planning/ (never dispatches)"
    ),
)

OBJECTIVE_PLAN_COMPILE = MutationSpec(
    name="objective_plan_compile",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=30.0,
    verification_required=False,
    degraded_mode_allowed=True,
    description=(
        "Compile one versioned ObjectivePlanRecord (current/desired/gap + "
        "DAG-validated graph) and materialize canonical WorkPackets at most "
        "PLANNED with non-empty approval gates — plan acceptance never "
        "authorizes execution"
    ),
)

OBJECTIVE_PLAN_DECISION = MutationSpec(
    name="objective_plan_decision",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    degraded_mode_allowed=True,
    description=(
        "Record one HUD plan decision (approve/reject/cancel) with "
        "authorization_effect=plan_acceptance_only — packets stay at most "
        "PLANNED, zero ExecutionAttempts, execution authorization remains a "
        "distinct unresolved future decision"
    ),
)

OBJECTIVE_PLAN_REVISE = MutationSpec(
    name="objective_plan_revise",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=30.0,
    verification_required=False,
    degraded_mode_allowed=True,
    description=(
        "Append plan version v(n+1) from a validated revision edit set; "
        "v(n) flips to SUPERSEDED and is preserved — versions are "
        "append-only, never rewritten"
    ),
)

VOICE_CONSENT_GRANT = MutationSpec(
    name="voice_consent_grant",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    # LOW risk + LOCAL_FILE + degraded opt-in: P4S-31D-1 records one operator's
    # explicit per-device, per-mode voice capture consent as substrate-owned
    # JSON state (data/umh/voice/consent_grants.json). Fully reversible via
    # voice_consent_revoke. Never opens a microphone, never captures audio,
    # never dispatches — capture itself happens client-side only AFTER the
    # fail-closed gate (VoiceConsentStore.require_active_grant) sees this grant.
    degraded_mode_allowed=True,
    description=(
        "Record one explicit operator VoiceConsentGrant (per device, per "
        "activation mode) as substrate-owned JSON state — the fail-closed "
        "consent gate for voice capture; never captures audio or dispatches"
    ),
)

VOICE_CONSENT_REVOKE = MutationSpec(
    name="voice_consent_revoke",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_FILE,
    timeout_seconds=10.0,
    verification_required=False,
    # Revocation must ALWAYS be executable (degraded opt-in): losing the
    # control plane must never leave a consent grant un-revocable.
    degraded_mode_allowed=True,
    description=(
        "Revoke an operator VoiceConsentGrant (per device, per activation "
        "mode) — sets revoked_at on the substrate-owned JSON record; all "
        "capture in that mode is refused fail-closed afterwards"
    ),
)

GOVERNANCE_UPDATE = MutationSpec(
    name="governance_update",
    action_type=ActionType.STATE,
    risk_level="high",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    require_approval=True,
    description="Update governance policy or execution mode",
)

CHANNEL_MESSAGE_SEND = MutationSpec(
    name="channel_message_send",
    action_type=ActionType.NETWORK,
    risk_level="low",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.EXTERNAL,
    timeout_seconds=15.0,
    description="Send a message to an external channel",
)

CONVERSATION_SEND = MutationSpec(
    name="conversation_send",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Send or record an internal conversation message",
)

MEMORY_PROMOTE = MutationSpec(
    name="memory_promote",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Promote a memory entry to a higher tier",
)

WORK_PACKET_CREATE = MutationSpec(
    name="work_packet_create",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Create a new work packet",
)

WORK_PACKET_UPDATE = MutationSpec(
    name="work_packet_update",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Update an existing work packet",
)

PROJECTION_EVENT = MutationSpec(
    name="projection_event",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Register a projection-level event",
)

ADAPTER_UPDATE = MutationSpec(
    name="adapter_update",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=15.0,
    description="Update an adapter status or configuration",
)

SANDBOX_CREATE = MutationSpec(
    name="sandbox_create",
    action_type=ActionType.PROCESS,
    risk_level="high",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=120.0,
    require_approval=True,
    description="Create or launch a sandboxed execution environment",
)

STATE_MUTATE = MutationSpec(
    name="state_mutate",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Generic state mutation for low-risk cockpit operations",
)

WORK_PACKET_EXECUTE = MutationSpec(
    name="work_packet_execute",
    action_type=ActionType.PROCESS,
    risk_level="high",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=600.0,
    require_approval=True,
    description="Execute a work packet through the agent execution pipeline",
)

STRATEGY_MUTATE = MutationSpec(
    name="strategy_mutate",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Create, update, or delete a strategy goal or recommendation",
)

OPERATOR_LOOP_CONTROL = MutationSpec(
    name="operator_loop_control",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Start, stop, pause, or resume the operator tick loop",
)

SESSION_MUTATE = MutationSpec(
    name="session_mutate",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Start, suspend, resume, or manage an operator session",
)

PRESENCE_UPDATE = MutationSpec(
    name="presence_update",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Update operator presence or session state",
)

COMMAND_SUBMIT = MutationSpec(
    name="command_submit",
    action_type=ActionType.PROCESS,
    risk_level="medium",
    reversibility=ReversibilityClass.IRREVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=30.0,
    description="Submit, classify, approve, or reject an operator command",
)

WORKSTATION_MUTATE = MutationSpec(
    name="workstation_mutate",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Prepare, restore, or snapshot a workstation",
)

PROFILE_MUTATE = MutationSpec(
    name="profile_mutate",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Activate or deactivate a profile or system mode",
)

CONTINUITY_MUTATE = MutationSpec(
    name="continuity_mutate",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=15.0,
    description="Capture, depart, resume, handoff, or generate continuity brief",
)

TICK_CANDIDATE_DECIDE = MutationSpec(
    name="tick_candidate_decide",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Accept or reject a tick-loop candidate",
)

OUTCOME_RECORD = MutationSpec(
    name="outcome_record",
    action_type=ActionType.STATE,
    risk_level="low",
    reversibility=ReversibilityClass.FULLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.LOCAL_RUNTIME,
    timeout_seconds=10.0,
    description="Record an outcome or execution result",
)

COGNITIVE_EXECUTION = MutationSpec(
    name="cognitive_execution",
    action_type=ActionType.STATE,
    risk_level="medium",
    reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
    allowed_modes=_ALL_MODES,
    blast_radius=BlastRadius.SINGLE_SERVICE,
    timeout_seconds=120.0,
    max_retries=0,
    verification_required=True,
    description="Cognitive loop LLM execution through governed spine",
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
            SETTINGS_UPDATE,
            CONFIG_SET,
            APPROVAL_DECIDE,
            EOS_ACTION_PROPOSAL_DECISION,
            EOS_ACTION_PROPOSAL_EXECUTE,
            INTENT_LOOP_SUBMIT,
            INTENT_LOOP_APPROVAL_DECISION,
            OBJECTIVE_GOAL_WRITE,
            OBJECTIVE_PLAN_ASSESS,
            OBJECTIVE_PLAN_COMPILE,
            OBJECTIVE_PLAN_DECISION,
            OBJECTIVE_PLAN_REVISE,
            VOICE_CONSENT_GRANT,
            VOICE_CONSENT_REVOKE,
            GOVERNANCE_UPDATE,
            CHANNEL_MESSAGE_SEND,
            CONVERSATION_SEND,
            MEMORY_PROMOTE,
            WORK_PACKET_CREATE,
            WORK_PACKET_UPDATE,
            PROJECTION_EVENT,
            ADAPTER_UPDATE,
            SANDBOX_CREATE,
            STATE_MUTATE,
            WORK_PACKET_EXECUTE,
            STRATEGY_MUTATE,
            OPERATOR_LOOP_CONTROL,
            SESSION_MUTATE,
            PRESENCE_UPDATE,
            COMMAND_SUBMIT,
            WORKSTATION_MUTATE,
            PROFILE_MUTATE,
            CONTINUITY_MUTATE,
            TICK_CANDIDATE_DECIDE,
            OUTCOME_RECORD,
            COGNITIVE_EXECUTION,
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
