"""Command Runtime — canonical intent-to-action layer for all operator surfaces.

Every operator interaction (voice, cockpit, API, mobile, meeting) routes
through the Command Runtime. It normalizes raw input into a structured
Command, classifies the action type deterministically, assembles full
context from all Phase 4-8 subsystems, and routes into existing UMH
infrastructure (EmpireRouter, WorkPacketEngine, Continuity, Presence).

Phase 9. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


# ── Enums ─────────────────────────────────────────────────────────────────


class CommandActionType(str, Enum):
    """What kind of operation the operator is requesting."""

    QUERY = "query"
    EXECUTE = "execute"
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    SCHEDULE = "schedule"
    SWITCH_PROFILE = "switch_profile"
    SWITCH_SESSION = "switch_session"
    CREATE_OBJECTIVE = "create_objective"
    CREATE_WORKPACKET = "create_workpacket"
    CREATE_SEQUENCE = "create_sequence"

    @property
    def is_mutation(self) -> bool:
        return self in (
            CommandActionType.EXECUTE,
            CommandActionType.APPROVE,
            CommandActionType.REJECT,
            CommandActionType.SCHEDULE,
            CommandActionType.SWITCH_PROFILE,
            CommandActionType.SWITCH_SESSION,
            CommandActionType.CREATE_OBJECTIVE,
            CommandActionType.CREATE_WORKPACKET,
            CommandActionType.CREATE_SEQUENCE,
        )

    @property
    def requires_approval(self) -> bool:
        return self in (
            CommandActionType.EXECUTE,
            CommandActionType.CREATE_SEQUENCE,
        )


class CommandStatus(str, Enum):
    """Lifecycle of a command."""

    RECEIVED = "received"
    CLASSIFIED = "classified"
    CONTEXT_ASSEMBLED = "context_assembled"
    ROUTED = "routed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            CommandStatus.COMPLETED,
            CommandStatus.FAILED,
            CommandStatus.CANCELLED,
            CommandStatus.REJECTED,
        )


class CommandSource(str, Enum):
    """Where the command originated."""

    COCKPIT = "cockpit"
    VOICE = "voice"
    API = "api"
    MEETING = "meeting"
    MOBILE = "mobile"
    TICK_LOOP = "tick_loop"
    INTERNAL = "internal"


class CommandEventType(str, Enum):
    """Timeline event types for command lifecycle."""

    COMMAND_RECEIVED = "command_received"
    COMMAND_CLASSIFIED = "command_classified"
    CONTEXT_ASSEMBLED = "context_assembled"
    COMMAND_ROUTED = "command_routed"
    APPROVAL_REQUESTED = "approval_requested"
    COMMAND_APPROVED = "command_approved"
    COMMAND_REJECTED = "command_rejected"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    COMMAND_CANCELLED = "command_cancelled"


# ── Data Models ──────────────────────────────────────────────────────────


@dataclass
class CommandContext:
    """Full context assembled for command execution."""

    profile_mode: str = ""
    session_id: str = ""
    attention_state: str = ""
    interruption_level: str = ""
    interaction_surface: str = ""
    operator_present: bool = False
    active_objectives: list[dict[str, Any]] = field(default_factory=list)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    blocked_items: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: int = 0
    current_projections: list[dict[str, Any]] = field(default_factory=list)
    active_risks: list[dict[str, Any]] = field(default_factory=list)
    continuity_hash: str = ""
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_mode": self.profile_mode,
            "session_id": self.session_id,
            "attention_state": self.attention_state,
            "interruption_level": self.interruption_level,
            "interaction_surface": self.interaction_surface,
            "operator_present": self.operator_present,
            "active_objectives": self.active_objectives,
            "active_work_packets": self.active_work_packets,
            "active_loops": self.active_loops,
            "blocked_items": self.blocked_items,
            "pending_approvals": self.pending_approvals,
            "current_projections": self.current_projections,
            "active_risks": self.active_risks,
            "continuity_hash": self.continuity_hash,
            "drift_warnings": self.drift_warnings,
        }


@dataclass
class Command:
    """Canonical command contract — every operator interaction becomes one."""

    command_id: str = ""
    source: str = ""
    raw_input: str = ""
    normalized_command: str = ""
    operator_id: str = ""
    profile_mode: str = ""
    session_id: str = ""
    timestamp: float = 0.0
    confidence: float = 1.0
    target_domain: str = ""
    target_agents: list[str] = field(default_factory=list)
    action_type: str = ""
    approval_required: bool = False
    workpacket_id: str = ""
    status: str = "received"
    context: dict[str, Any] = field(default_factory=dict)
    routing_result: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def __post_init__(self) -> None:
        import uuid
        if not self.command_id:
            self.command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "source": self.source,
            "raw_input": self.raw_input,
            "normalized_command": self.normalized_command,
            "operator_id": self.operator_id,
            "profile_mode": self.profile_mode,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "target_domain": self.target_domain,
            "target_agents": self.target_agents,
            "action_type": self.action_type,
            "approval_required": self.approval_required,
            "workpacket_id": self.workpacket_id,
            "status": self.status,
            "context": self.context,
            "routing_result": self.routing_result,
            "outcome": self.outcome,
            "error": self.error,
        }


@dataclass
class CommandEvent:
    """Timeline event for command lifecycle tracking."""

    event_id: str = ""
    event_type: str = ""
    command_id: str = ""
    timestamp: float = 0.0
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        import uuid
        if not self.event_id:
            self.event_id = f"cevt-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class CommandRoutingDecision:
    """Audit record of how a command was routed."""

    command_id: str = ""
    action_type: str = ""
    destination_system: str = ""
    approval_state: str = ""
    workpacket_id: str = ""
    routing_result: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    decided_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.decided_at:
            self.decided_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "action_type": self.action_type,
            "destination_system": self.destination_system,
            "approval_state": self.approval_state,
            "workpacket_id": self.workpacket_id,
            "routing_result": self.routing_result,
            "outcome": self.outcome,
            "decided_at": self.decided_at,
        }


# ── Command Classifier ──────────────────────────────────────────────────


# Verb patterns for deterministic classification (ordered by specificity)
_ACTION_PATTERNS: list[tuple[str, CommandActionType]] = [
    # Approval verbs
    (r"\bapprove\b", CommandActionType.APPROVE),
    (r"\baccept\b", CommandActionType.APPROVE),
    (r"\bauthorize\b", CommandActionType.APPROVE),
    (r"\bgrant\b", CommandActionType.APPROVE),
    (r"\breject\b", CommandActionType.REJECT),
    (r"\bdeny\b", CommandActionType.REJECT),
    (r"\bdecline\b", CommandActionType.REJECT),
    # Profile switching
    (r"\bswitch\s+(?:to\s+)?(?:\w+\s+)?profile\b", CommandActionType.SWITCH_PROFILE),
    (r"\bactivate\s+(?:\w+\s+)?profile\b", CommandActionType.SWITCH_PROFILE),
    (r"\bswitch\s+(?:to\s+)?(?:developer|engineer|research|music|design|content|command|finance|learning)\b",
     CommandActionType.SWITCH_PROFILE),
    # Session switching
    (r"\bswitch\s+(?:to\s+)?session\b", CommandActionType.SWITCH_SESSION),
    (r"\bjoin\s+session\b", CommandActionType.SWITCH_SESSION),
    # Creation verbs (order: most specific first)
    (r"\bcreate\s+(?:a\s+)?sequence\b", CommandActionType.CREATE_SEQUENCE),
    (r"\bbuild\s+(?:a\s+)?sequence\b", CommandActionType.CREATE_SEQUENCE),
    (r"\bcreate\s+(?:a\s+)?(?:work\s*)?packet\b", CommandActionType.CREATE_WORKPACKET),
    (r"\badd\s+(?:a\s+)?(?:work\s*)?packet\b", CommandActionType.CREATE_WORKPACKET),
    (r"\bcreate\s+(?:a\s+)?(?:new\s+)?objective\b", CommandActionType.CREATE_OBJECTIVE),
    (r"\badd\s+(?:a\s+)?(?:new\s+)?objective\b", CommandActionType.CREATE_OBJECTIVE),
    (r"\bset\s+(?:a\s+)?(?:new\s+)?objective\b", CommandActionType.CREATE_OBJECTIVE),
    (r"\bcreate\s+(?:a\s+)?(?:new\s+)?goal\b", CommandActionType.CREATE_OBJECTIVE),
    (r"\badd\s+(?:a\s+)?(?:new\s+)?goal\b", CommandActionType.CREATE_OBJECTIVE),
    # Scheduling
    (r"\bschedule\b", CommandActionType.SCHEDULE),
    (r"\bdefer\b", CommandActionType.SCHEDULE),
    (r"\bpostpone\b", CommandActionType.SCHEDULE),
    (r"\bqueue\b", CommandActionType.SCHEDULE),
    # Review
    (r"\breview\b", CommandActionType.REVIEW),
    (r"\baudit\b", CommandActionType.REVIEW),
    (r"\binspect\b", CommandActionType.REVIEW),
    (r"\bcheck\b", CommandActionType.REVIEW),
    (r"\bexamine\b", CommandActionType.REVIEW),
    # Query (question-like patterns)
    (r"\bwhat\b", CommandActionType.QUERY),
    (r"\bwho\b", CommandActionType.QUERY),
    (r"\bwhere\b", CommandActionType.QUERY),
    (r"\bwhen\b", CommandActionType.QUERY),
    (r"\bhow\s+(?:many|much|long|far)\b", CommandActionType.QUERY),
    (r"\bshow\s+(?:me\s+)?", CommandActionType.QUERY),
    (r"\blist\b", CommandActionType.QUERY),
    (r"\bstatus\b", CommandActionType.QUERY),
    (r"\bsummar(?:y|ize)\b", CommandActionType.QUERY),
    (r"\btell\s+me\b", CommandActionType.QUERY),
    (r"\bget\b", CommandActionType.QUERY),
    (r"^how\b", CommandActionType.QUERY),
    (r"\?$", CommandActionType.QUERY),
    # Execute (action verbs — catch-all for mutations)
    (r"\bbuild\b", CommandActionType.EXECUTE),
    (r"\bimplement\b", CommandActionType.EXECUTE),
    (r"\bdeploy\b", CommandActionType.EXECUTE),
    (r"\bfix\b", CommandActionType.EXECUTE),
    (r"\brefactor\b", CommandActionType.EXECUTE),
    (r"\binstall\b", CommandActionType.EXECUTE),
    (r"\bupdate\b", CommandActionType.EXECUTE),
    (r"\bupgrade\b", CommandActionType.EXECUTE),
    (r"\bremove\b", CommandActionType.EXECUTE),
    (r"\bdelete\b", CommandActionType.EXECUTE),
    (r"\brun\b", CommandActionType.EXECUTE),
    (r"\bstart\b", CommandActionType.EXECUTE),
    (r"\bstop\b", CommandActionType.EXECUTE),
    (r"\brestart\b", CommandActionType.EXECUTE),
    (r"\bmigrate\b", CommandActionType.EXECUTE),
]

# Compiled patterns for performance
_COMPILED_PATTERNS: list[tuple[re.Pattern[str], CommandActionType]] = [
    (re.compile(p, re.IGNORECASE), t) for p, t in _ACTION_PATTERNS
]

# Profile mode name mapping
_PROFILE_NAMES: dict[str, str] = {
    "developer": "developer",
    "dev": "developer",
    "engineer": "developer",
    "engineering": "developer",
    "research": "research",
    "researcher": "research",
    "music": "music",
    "musician": "music",
    "design": "design",
    "designer": "design",
    "content": "content",
    "creator": "content",
    "writer": "content",
    "command": "command_center",
    "command_center": "command_center",
    "executive": "command_center",
    "finance": "finance",
    "financial": "finance",
    "learning": "learning",
    "study": "learning",
    "student": "learning",
}


class CommandClassifier:
    """Deterministic command classifier — verb pattern matching only.

    Does NOT duplicate the IntentClassifier's domain/risk/entity work.
    Only classifies the action type (what operation the operator wants).
    """

    def classify(self, raw_input: str) -> tuple[CommandActionType, float]:
        """Classify raw input into an action type with confidence.

        Returns (action_type, confidence). Confidence is 1.0 for exact
        pattern matches, 0.5 for the fallback.
        """
        text = raw_input.strip()
        if not text:
            return CommandActionType.QUERY, 0.5

        for pattern, action_type in _COMPILED_PATTERNS:
            if pattern.search(text):
                return action_type, 1.0

        return CommandActionType.EXECUTE, 0.5

    def extract_profile_target(self, raw_input: str) -> str:
        """Extract target profile name from a profile switch command."""
        lower = raw_input.lower()
        for name, mode in _PROFILE_NAMES.items():
            if name in lower:
                return mode
        return ""

    def extract_objective_text(self, raw_input: str) -> str:
        """Extract the objective description from a create-objective command."""
        patterns = [
            r"(?:create|add|set)\s+(?:a\s+)?(?:new\s+)?(?:objective|goal)\s*[:\-]?\s*(.+)",
        ]
        for p in patterns:
            m = re.search(p, raw_input, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return raw_input

    def extract_packet_target(self, raw_input: str) -> str:
        """Extract packet identifier from approve/reject commands."""
        patterns = [
            r"(?:approve|reject|accept|deny)\s+(?:work\s*)?packet\s+(\S+)",
            r"(?:approve|reject|accept|deny)\s+(\S+)",
        ]
        for p in patterns:
            m = re.search(p, raw_input, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""


# ── Context Assembler ────────────────────────────────────────────────────


class ContextAssembler:
    """Gathers full execution context from all Phase 4-8 subsystems.

    The operator should never have to restate context. Every command
    automatically receives the current state of the entire system.
    """

    def assemble(self) -> CommandContext:
        ctx = CommandContext()

        self._assemble_presence(ctx)
        self._assemble_continuity(ctx)
        self._assemble_strategy(ctx)
        self._assemble_tick_loop(ctx)
        self._assemble_projections(ctx)

        return ctx

    def _assemble_presence(self, ctx: CommandContext) -> None:
        try:
            from substrate.organism.presence_runtime import get_presence_runtime
            rt = get_presence_runtime()
            snapshot = rt.capture_snapshot()
            ctx.profile_mode = snapshot.active_profile_mode
            ctx.session_id = snapshot.active_session
            ctx.attention_state = snapshot.attention_state
            ctx.interruption_level = snapshot.interruption_budget
            ctx.interaction_surface = snapshot.interaction_surface
            ctx.operator_present = snapshot.operator_present
        except Exception as exc:
            logger.debug("presence assembly skipped: %s", exc)

    def _assemble_continuity(self, ctx: CommandContext) -> None:
        try:
            from substrate.organism.continuity_runtime import get_continuity_runtime
            rt = get_continuity_runtime()
            snapshot = rt.capture_snapshot()
            ctx.active_objectives = snapshot.active_objectives
            ctx.active_work_packets = snapshot.active_work_packets
            ctx.active_loops = snapshot.active_loops
            ctx.blocked_items = snapshot.blocked_items
            ctx.pending_approvals = len(snapshot.approvals_waiting)
            ctx.continuity_hash = snapshot.reality_hash
        except Exception as exc:
            logger.debug("continuity assembly skipped: %s", exc)

    def _assemble_strategy(self, ctx: CommandContext) -> None:
        try:
            from substrate.organism.strategic_gap_engine import get_gap_engine
            engine = get_gap_engine()
            state = engine.get_strategic_state()
            ctx.drift_warnings = [
                {"goal": w.get("goal_title", ""), "severity": w.get("severity", ""),
                 "days": w.get("days_stagnant", 0)}
                for w in state.get("drift_warnings", [])
            ]
        except Exception as exc:
            logger.debug("strategy assembly skipped: %s", exc)

    def _assemble_tick_loop(self, ctx: CommandContext) -> None:
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop
            loop = get_tick_loop()
            status = loop.get_status()
            ctx.active_loops = ctx.active_loops or []
            if status.get("running"):
                ctx.active_loops.append({
                    "system": "tick_loop",
                    "frequency": status.get("frequency", ""),
                    "cycle": status.get("cycle_count", 0),
                })
        except Exception as exc:
            logger.debug("tick loop assembly skipped: %s", exc)

    def _assemble_projections(self, ctx: CommandContext) -> None:
        try:
            from substrate.organism.projection_engine import get_projection_engine
            engine = get_projection_engine()
            state = engine.get_projection_state()
            ctx.current_projections = state.get("trends", [])[:5]
            ctx.active_risks = state.get("risks", [])[:5]
        except Exception as exc:
            logger.debug("projection assembly skipped: %s", exc)


# ── Command Router ───────────────────────────────────────────────────────


class CommandRouter:
    """Routes classified commands into existing UMH systems.

    Never executes directly — always routes into the appropriate
    existing subsystem (EmpireRouter, WorkPacketEngine, Continuity, etc.).
    """

    def route(self, command: Command) -> CommandRoutingDecision:
        """Route a classified command to its destination system."""
        action = command.action_type
        decision = CommandRoutingDecision(
            command_id=command.command_id,
            action_type=action,
        )

        try:
            if action == CommandActionType.QUERY.value:
                self._route_query(command, decision)
            elif action == CommandActionType.EXECUTE.value:
                self._route_execute(command, decision)
            elif action == CommandActionType.REVIEW.value:
                self._route_review(command, decision)
            elif action == CommandActionType.APPROVE.value:
                self._route_approve(command, decision)
            elif action == CommandActionType.REJECT.value:
                self._route_reject(command, decision)
            elif action == CommandActionType.SCHEDULE.value:
                self._route_schedule(command, decision)
            elif action == CommandActionType.SWITCH_PROFILE.value:
                self._route_switch_profile(command, decision)
            elif action == CommandActionType.SWITCH_SESSION.value:
                self._route_switch_session(command, decision)
            elif action == CommandActionType.CREATE_OBJECTIVE.value:
                self._route_create_objective(command, decision)
            elif action == CommandActionType.CREATE_WORKPACKET.value:
                self._route_create_workpacket(command, decision)
            elif action == CommandActionType.CREATE_SEQUENCE.value:
                self._route_create_sequence(command, decision)
            else:
                decision.destination_system = "empire_router"
                decision.approval_state = "unknown"

        except Exception as exc:
            logger.error("command routing failed for %s: %s", command.command_id, exc)
            decision.outcome = {"error": str(exc)}

        return decision

    def _route_query(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        """Route query commands to continuity/reality systems."""
        dec.destination_system = "continuity_runtime"
        dec.approval_state = "not_required"

        lower = cmd.raw_input.lower()
        if any(kw in lower for kw in ("changed", "happened", "gone", "away", "missed")):
            dec.destination_system = "continuity_runtime"
            dec.outcome = self._query_continuity(cmd)
        elif any(kw in lower for kw in ("status", "state", "overview", "summary")):
            dec.destination_system = "empire_router"
            dec.outcome = self._query_reality(cmd)
        elif any(kw in lower for kw in ("risk", "threat", "danger")):
            dec.destination_system = "projection_engine"
            dec.outcome = self._query_projections(cmd)
        elif any(kw in lower for kw in ("drift", "stagnant", "stuck")):
            dec.destination_system = "strategic_tick_loop"
            dec.outcome = self._query_drift(cmd)
        else:
            dec.destination_system = "empire_router"
            dec.outcome = self._query_reality(cmd)

    def _route_execute(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        """Route execution commands through Empire Router."""
        dec.destination_system = "empire_router"
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            result = router.route(
                intent=cmd.raw_input,
                profile_mode=cmd.profile_mode,
                operator_available=cmd.context.get("operator_present", True),
            )
            dec.routing_result = result.to_dict()
            dec.approval_state = "required" if result.required_approvals else "not_required"
            if result.work_packets:
                dec.workpacket_id = result.work_packets[0].get("packet_id", "")
        except Exception as exc:
            logger.error("empire routing failed: %s", exc)
            dec.outcome = {"error": str(exc)}

    def _route_review(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        """Route review commands to appropriate subsystem."""
        dec.destination_system = "empire_router"
        dec.approval_state = "not_required"
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            result = router.route(
                intent=cmd.raw_input,
                profile_mode=cmd.profile_mode,
            )
            dec.routing_result = result.to_dict()
        except Exception as exc:
            logger.error("review routing failed: %s", exc)
            dec.outcome = {"error": str(exc)}

    def _route_approve(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "approval_system"
        dec.approval_state = "approved"
        classifier = CommandClassifier()
        target = classifier.extract_packet_target(cmd.raw_input)
        if target:
            dec.workpacket_id = target
            dec.outcome = self._process_approval(target, approved=True)
        else:
            dec.outcome = {"error": "no packet target found in command"}

    def _route_reject(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "approval_system"
        dec.approval_state = "rejected"
        classifier = CommandClassifier()
        target = classifier.extract_packet_target(cmd.raw_input)
        if target:
            dec.workpacket_id = target
            dec.outcome = self._process_approval(target, approved=False)
        else:
            dec.outcome = {"error": "no packet target found in command"}

    def _route_schedule(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "tick_loop"
        dec.approval_state = "not_required"
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop
            loop = get_tick_loop()
            from substrate.organism.strategic_tick_loop import CandidateWorkItem
            candidate = CandidateWorkItem(
                title=cmd.raw_input,
                domain=cmd.target_domain or "general",
                priority_score=0.5,
                impact="medium",
                risk="low",
            )
            loop._candidate_queue.add(candidate)
            dec.outcome = {
                "scheduled": True,
                "candidate_id": candidate.candidate_id,
            }
        except Exception as exc:
            logger.error("schedule routing failed: %s", exc)
            dec.outcome = {"error": str(exc)}

    def _route_switch_profile(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "presence_runtime"
        dec.approval_state = "not_required"
        classifier = CommandClassifier()
        target_profile = classifier.extract_profile_target(cmd.raw_input)
        if target_profile:
            try:
                from substrate.organism.presence_runtime import get_presence_runtime
                rt = get_presence_runtime()
                rt.change_profile(target_profile)
                dec.outcome = {"switched": True, "profile": target_profile}
            except Exception as exc:
                logger.error("profile switch failed: %s", exc)
                dec.outcome = {"error": str(exc)}
        else:
            dec.outcome = {"error": "no profile target found in command"}

    def _route_switch_session(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "presence_runtime"
        dec.approval_state = "not_required"
        dec.outcome = {"note": "session switch requires explicit session_id via API"}

    def _route_create_objective(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "strategic_gap_engine"
        dec.approval_state = "not_required"
        classifier = CommandClassifier()
        objective_text = classifier.extract_objective_text(cmd.raw_input)
        if objective_text:
            try:
                from substrate.organism.strategic_gap_engine import get_gap_engine
                engine = get_gap_engine()
                goal = engine.add_goal(
                    title=objective_text,
                    domain=cmd.target_domain or "general",
                )
                dec.outcome = {
                    "created": True,
                    "goal_id": goal.get("goal_id", ""),
                    "title": objective_text,
                }
            except Exception as exc:
                logger.error("objective creation failed: %s", exc)
                dec.outcome = {"error": str(exc)}
        else:
            dec.outcome = {"error": "no objective text found"}

    def _route_create_workpacket(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "empire_router"
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            result = router.route(intent=cmd.raw_input, profile_mode=cmd.profile_mode)
            dec.routing_result = result.to_dict()
            dec.approval_state = "required" if result.required_approvals else "not_required"
            if result.work_packets:
                dec.workpacket_id = result.work_packets[0].get("packet_id", "")
        except Exception as exc:
            logger.error("workpacket creation failed: %s", exc)
            dec.outcome = {"error": str(exc)}

    def _route_create_sequence(self, cmd: Command, dec: CommandRoutingDecision) -> None:
        dec.destination_system = "empire_router"
        dec.approval_state = "required"
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            result = router.route(intent=cmd.raw_input, profile_mode=cmd.profile_mode)
            dec.routing_result = result.to_dict()
            if result.work_packets:
                dec.workpacket_id = result.work_packets[0].get("packet_id", "")
        except Exception as exc:
            logger.error("sequence creation failed: %s", exc)
            dec.outcome = {"error": str(exc)}

    # ── Query helpers ─────────────────────────────────────────────────

    def _query_continuity(self, cmd: Command) -> dict[str, Any]:
        try:
            from substrate.organism.continuity_runtime import get_continuity_runtime
            rt = get_continuity_runtime()
            brief = rt.generate_brief()
            brief_data = brief.to_dict() if hasattr(brief, "to_dict") else str(brief)
            return {"type": "continuity_brief", "brief": brief_data}
        except Exception as exc:
            return {"error": str(exc)}

    def _query_reality(self, cmd: Command) -> dict[str, Any]:
        try:
            from substrate.organism.empire_router import EmpireRouter
            router = EmpireRouter()
            snapshot = router.get_reality_snapshot()
            return {"type": "reality_snapshot", "snapshot": snapshot.to_dict()}
        except Exception as exc:
            return {"error": str(exc)}

    def _query_projections(self, cmd: Command) -> dict[str, Any]:
        try:
            from substrate.organism.projection_engine import get_projection_engine
            engine = get_projection_engine()
            state = engine.get_projection_state()
            return {
                "type": "projections",
                "risks": state.get("risks", []),
                "opportunities": state.get("opportunities", []),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _query_drift(self, cmd: Command) -> dict[str, Any]:
        try:
            from substrate.organism.strategic_tick_loop import get_tick_loop
            loop = get_tick_loop()
            status = loop.get_status()
            return {
                "type": "drift",
                "drift_warnings": status.get("drift_warnings", []),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _process_approval(self, packet_id: str, approved: bool) -> dict[str, Any]:
        try:
            from substrate.organism.universal_work_queue import UniversalWorkQueue
            q = UniversalWorkQueue()
            pkt = q.get_packet(packet_id)
            if not pkt:
                return {"error": f"packet {packet_id} not found"}
            new_status = "approved" if approved else "rejected"
            q.update_status(packet_id, new_status)
            return {"processed": True, "packet_id": packet_id, "new_status": new_status}
        except Exception as exc:
            return {"error": str(exc)}


# ── Command Timeline ─────────────────────────────────────────────────────


class CommandTimeline:
    """JSONL-backed timeline of all command lifecycle events.

    Integrates with Continuity Runtime by emitting events that the
    continuity timeline can observe.
    """

    def __init__(self, data_dir: str = "") -> None:
        if not data_dir:
            data_dir = os.path.join(_repo_root(), "data", "umh", "command", "timeline")
        self._data_dir = data_dir
        os.makedirs(self._data_dir, exist_ok=True)
        self._events_path = os.path.join(self._data_dir, "events.jsonl")

    def emit(self, event: CommandEvent) -> None:
        """Append an event to the timeline."""
        try:
            with open(self._events_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except OSError as exc:
            logger.error("failed to write command event: %s", exc)

    def get_events(
        self,
        since: float = 0,
        command_id: str = "",
        event_type: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read events with optional filters."""
        events: list[dict[str, Any]] = []
        if not os.path.exists(self._events_path):
            return events

        try:
            with open(self._events_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if since and evt.get("timestamp", 0) < since:
                        continue
                    if command_id and evt.get("command_id") != command_id:
                        continue
                    if event_type and evt.get("event_type") != event_type:
                        continue
                    events.append(evt)
        except OSError as exc:
            logger.error("failed to read command timeline: %s", exc)

        events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return events[:limit]

    def get_command_history(self, command_id: str) -> list[dict[str, Any]]:
        """Get full lifecycle history for a single command."""
        return self.get_events(command_id=command_id, limit=1000)


# ── Command History ──────────────────────────────────────────────────────


class CommandHistory:
    """JSONL-backed store of all commands and their outcomes."""

    def __init__(self, data_dir: str = "") -> None:
        if not data_dir:
            data_dir = os.path.join(_repo_root(), "data", "umh", "command")
        self._data_dir = data_dir
        os.makedirs(self._data_dir, exist_ok=True)
        self._commands_path = os.path.join(self._data_dir, "commands.jsonl")

    def save(self, command: Command) -> None:
        try:
            with open(self._commands_path, "a") as f:
                f.write(json.dumps(command.to_dict()) + "\n")
        except OSError as exc:
            logger.error("failed to save command: %s", exc)

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        if not os.path.exists(self._commands_path):
            return commands
        try:
            with open(self._commands_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        commands.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.error("failed to read commands: %s", exc)

        commands.sort(key=lambda c: c.get("timestamp", 0), reverse=True)
        return commands[:limit]

    def get_pending(self) -> list[dict[str, Any]]:
        return [
            c for c in self.get_recent(limit=200)
            if c.get("status") in ("received", "classified", "context_assembled",
                                    "routed", "pending_approval", "executing")
        ]

    def get_by_status(self, status: str, limit: int = 50) -> list[dict[str, Any]]:
        return [
            c for c in self.get_recent(limit=500)
            if c.get("status") == status
        ][:limit]

    def update_status(
        self,
        command_id: str,
        status: str,
        outcome: dict[str, Any] | None = None,
        required_current_status: set[str] | None = None,
    ) -> bool:
        """Update a command's status by rewriting the JSONL file.

        If required_current_status is provided, the update only applies when the
        command's current status is in that set — making the check-and-write atomic
        within a single file pass (no TOCTOU window).
        """
        if not os.path.exists(self._commands_path):
            return False

        lines: list[str] = []
        found = False
        try:
            with open(self._commands_path, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        cmd = json.loads(stripped)
                        if cmd.get("command_id") == command_id:
                            if required_current_status is not None and cmd.get("status") not in required_current_status:
                                return False
                            cmd["status"] = status
                            if outcome:
                                cmd["outcome"] = outcome
                            found = True
                        lines.append(json.dumps(cmd))
                    except json.JSONDecodeError:
                        lines.append(stripped)
        except OSError:
            return False

        if found:
            try:
                with open(self._commands_path, "w") as f:
                    f.write("\n".join(lines) + "\n")
            except OSError:
                return False
        return found


# ── Command Runtime (Orchestrator) ───────────────────────────────────────


class CommandRuntime:
    """Top-level orchestrator — the canonical entry point for all operator commands.

    submit() is the single entry point. Every surface (voice, cockpit, API,
    meeting, mobile) calls submit() with raw input and source metadata.

    Pipeline:
        receive → classify → assemble context → route → record → return
    """

    def __init__(self) -> None:
        self._classifier = CommandClassifier()
        self._assembler = ContextAssembler()
        self._router = CommandRouter()
        self._timeline = CommandTimeline()
        self._history = CommandHistory()

    def submit(
        self,
        raw_input: str,
        source: str = "cockpit",
        operator_id: str = "",
        session_id: str = "",
        profile_mode: str = "",
    ) -> Command:
        """Submit a command — the canonical entry point for all surfaces.

        Returns the fully processed Command with routing decision and outcome.
        """
        # 1. Receive
        command = Command(
            source=source,
            raw_input=raw_input,
            normalized_command=self._normalize(raw_input),
            operator_id=operator_id,
            session_id=session_id,
            profile_mode=profile_mode,
        )
        self._emit_event(command, CommandEventType.COMMAND_RECEIVED,
                         f"Command received from {source}")

        # 2. Classify
        action_type, confidence = self._classifier.classify(raw_input)
        command.action_type = action_type.value
        command.confidence = confidence
        command.status = CommandStatus.CLASSIFIED.value
        self._emit_event(command, CommandEventType.COMMAND_CLASSIFIED,
                         f"Classified as {action_type.value} (confidence={confidence})")

        # 3. Assemble context
        ctx = self._assembler.assemble()
        command.context = ctx.to_dict()
        if not command.profile_mode:
            command.profile_mode = ctx.profile_mode
        if not command.session_id:
            command.session_id = ctx.session_id
        command.status = CommandStatus.CONTEXT_ASSEMBLED.value
        self._emit_event(command, CommandEventType.CONTEXT_ASSEMBLED,
                         "Full context assembled from Phases 4-8")

        # 4. Classify domain (via IntentClassifier)
        # Fail-closed: if classifier fails, mutations require approval
        try:
            from substrate.organism.intent_classifier import IntentClassifier
            ic = IntentClassifier()
            classification = ic.classify(raw_input)
            command.target_domain = classification.domain
            command.approval_required = (
                action_type.requires_approval
                or classification.approval_required
            )
        except Exception as exc:
            logger.warning("intent classification failed, fail-closed: %s", exc)
            if action_type.is_mutation:
                command.approval_required = True

        # 5. Route
        decision = self._router.route(command)
        command.routing_result = decision.to_dict()
        command.workpacket_id = decision.workpacket_id

        if command.approval_required and action_type.is_mutation:
            command.status = CommandStatus.PENDING_APPROVAL.value
            self._emit_event(command, CommandEventType.APPROVAL_REQUESTED,
                             f"Approval required for {action_type.value}")
        else:
            command.status = CommandStatus.ROUTED.value
            self._emit_event(command, CommandEventType.COMMAND_ROUTED,
                             f"Routed to {decision.destination_system}")

        # 6. For non-mutation commands, mark completed immediately
        if not action_type.is_mutation or not command.approval_required:
            command.outcome = decision.outcome
            command.status = CommandStatus.COMPLETED.value
            self._emit_event(command, CommandEventType.EXECUTION_COMPLETED,
                             "Command completed")

        # 7. Record
        self._history.save(command)

        return command

    def approve_command(self, command_id: str) -> dict[str, Any]:
        """Approve a pending command and execute it. Atomic state transition."""
        _APPROVABLE = {"pending_approval", "routed", "received", "classified", "context_assembled"}

        if not self._history.update_status(
            command_id, CommandStatus.APPROVED.value,
            required_current_status=_APPROVABLE,
        ):
            return {"error": f"command {command_id} not found or not in approvable state"}

        self._timeline.emit(CommandEvent(
            event_type=CommandEventType.COMMAND_APPROVED.value,
            command_id=command_id,
            summary="Command approved by operator",
        ))

        self._history.update_status(
            command_id, CommandStatus.EXECUTING.value,
            required_current_status={"approved"},
        )
        self._timeline.emit(CommandEvent(
            event_type=CommandEventType.EXECUTION_STARTED.value,
            command_id=command_id,
            summary="Execution started",
        ))

        commands = [c for c in self._history.get_recent(200) if c.get("command_id") == command_id]
        target = commands[0] if commands else {}
        cmd = Command(**{k: v for k, v in target.items() if k in Command.__dataclass_fields__})
        decision = self._router.route(cmd)

        outcome = decision.outcome or decision.routing_result
        self._history.update_status(command_id, CommandStatus.COMPLETED.value, outcome)
        self._timeline.emit(CommandEvent(
            event_type=CommandEventType.EXECUTION_COMPLETED.value,
            command_id=command_id,
            summary="Execution completed",
            details=outcome,
        ))

        return {"approved": True, "command_id": command_id, "outcome": outcome}

    def reject_command(self, command_id: str, reason: str = "") -> dict[str, Any]:
        """Reject a pending command. Atomic state transition — no TOCTOU window."""
        _REJECTABLE = {"received", "classified", "context_assembled", "routed", "pending_approval"}
        safe_reason = reason[:500] if reason else ""

        if not self._history.update_status(
            command_id, CommandStatus.REJECTED.value,
            {"reason": safe_reason},
            required_current_status=_REJECTABLE,
        ):
            return {"rejected": False, "error": f"command {command_id} not found or not rejectable"}
        self._timeline.emit(CommandEvent(
            event_type=CommandEventType.COMMAND_REJECTED.value,
            command_id=command_id,
            summary=f"Command rejected: {safe_reason}" if safe_reason else "Command rejected",
        ))
        return {"rejected": True, "command_id": command_id}

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history.get_recent(limit)

    def get_pending(self) -> list[dict[str, Any]]:
        return self._history.get_pending()

    def get_timeline(
        self, since: float = 0, command_id: str = "",
        event_type: str = "", limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._timeline.get_events(
            since=since, command_id=command_id,
            event_type=event_type, limit=limit,
        )

    def get_status(self) -> dict[str, Any]:
        """Overall command runtime status."""
        recent = self._history.get_recent(limit=100)
        pending = [c for c in recent if c.get("status") in
                   ("received", "classified", "context_assembled", "routed",
                    "pending_approval", "executing")]
        completed = [c for c in recent if c.get("status") == "completed"]
        failed = [c for c in recent if c.get("status") == "failed"]

        return {
            "phase": "Phase 9 — Command Runtime",
            "total_commands": len(recent),
            "pending": len(pending),
            "completed": len(completed),
            "failed": len(failed),
            "pending_approvals": len([
                c for c in recent if c.get("status") == "pending_approval"
            ]),
            "last_command": recent[0] if recent else None,
        }

    def _normalize(self, raw: str) -> str:
        """Normalize raw input: strip, collapse whitespace."""
        return re.sub(r"\s+", " ", raw.strip())

    def _emit_event(
        self, command: Command, event_type: CommandEventType, summary: str,
    ) -> None:
        self._timeline.emit(CommandEvent(
            event_type=event_type.value,
            command_id=command.command_id,
            summary=summary,
        ))


# ── Singleton ────────────────────────────────────────────────────────────

_instance: CommandRuntime | None = None


def get_command_runtime() -> CommandRuntime:
    global _instance
    if _instance is None:
        _instance = CommandRuntime()
    return _instance


def reset_command_runtime() -> None:
    global _instance
    _instance = None
