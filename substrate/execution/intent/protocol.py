"""Canonical Operator Intent Protocol — the ONE conversational work seam.

Plan §5 (Wave 1). This module is the SEMANTIC OWNER of operator intent:
transports (cockpit chat route, voice seam) are thin adapters that may invoke
it but never define intent semantics. Text and voice flow through the same
protocol.

One protocol, NOT one universal state machine:
  - COMMUNICATE / QUERY_STATE          → conversation output only, ZERO artifacts
  - CREATE_TASK / Task mutations       → canonical WorkPacket lifecycle
  - CREATE_OBJECTIVE / Plan mutations  → ObjectivePlanRecord versioning
  - PROVIDE_DECISION                   → resolves a DecisionRequest (surface/
                                         focus only — chat NEVER commits)
  - CLARIFICATION_RESPONSE             → resumes its planning session

Legacy cutover (§23.5): this protocol NEVER invokes the ``intent_loop_*``
mutations. New Cockpit work writes only to GoalRegistry (Objectives),
PlanningStore (Plans/sessions), the canonical WorkPacket store, the canonical
approval authority, and the shared EventSpine. Legacy IntentLoopRecords are
readable via :func:`read_legacy_intent_loops` — never written.

Deterministic-first: classification, reference resolution, existing-work
resolution, and ambiguity policy are pure functions of (text, ContextFrame).
The legacy ``IntentSpec`` remains a compatibility signal wrapped inside
:class:`IntentResolution`; new work never derives lifecycle from
``IntentLoopStage``.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from substrate.contracts.work_context import PrincipalContext, WorkScope
from substrate.execution.intent.context_frame import ContextFrame
from substrate.execution.intent.intent_spec import IntentSpec
from substrate.execution.planning.records import (
    IntentAssessmentState,
    PlanningSession,
    PlanningStageMarker,
)
from substrate.execution.planning.store import PlanningStore, message_fingerprint

logger = logging.getLogger(__name__)

# Mutation names this protocol submits under (registered in mutation_registry).
ASSESS_MUTATION_NAME = "objective_plan_assess"
GOAL_WRITE_MUTATION_NAME = "objective_goal_write"

# ── Canonical enums ──────────────────────────────────────────────────────────


class IntentClass(str, Enum):
    """The one canonical intent-class vocabulary (plan §5)."""

    COMMUNICATE = "communicate"
    QUERY_STATE = "query_state"
    CREATE_TASK = "create_task"
    CREATE_OBJECTIVE = "create_objective"
    MODIFY_TASK = "modify_task"
    MODIFY_PLAN = "modify_plan"
    MODIFY_OBJECTIVE = "modify_objective"
    LINK_WORK = "link_work"
    UNLINK_WORK = "unlink_work"
    REPRIORITIZE_WORK = "reprioritize_work"
    REORDER_DEPENDENCIES = "reorder_dependencies"
    CANCEL_WORK = "cancel_work"
    PAUSE_WORK = "pause_work"
    RESUME_WORK = "resume_work"
    REQUEST_EXECUTION = "request_execution"
    PROVIDE_DECISION = "provide_decision"
    CLARIFICATION_RESPONSE = "clarification_response"


class PlanningScale(str, Enum):
    """Fractal planning scales (§6) — scales, not different ontologies."""

    NONE = "none"  # communication / query — no work artifact
    ATOMIC_TASK = "atomic_task"
    PROJECT_OBJECTIVE = "project_objective"
    PROGRAM_OBJECTIVE = "program_objective"
    PORTFOLIO_OBJECTIVE = "portfolio_objective"
    INSTITUTION_OBJECTIVE = "institution_objective"


class DecisionRequirement(str, Enum):
    """§23.1 — whether this work class routes a Decision to the HUD at all.

    Atomic Task capture NEVER creates a HUD Decision (no approval fatigue);
    the packet is simply non-executable until a future execution decision
    (Wave 2). Objective Plans require a plan-acceptance Decision once ready.
    """

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"


# ── Resolution records ───────────────────────────────────────────────────────


@dataclass
class ReferenceResolution:
    """Which existing objects the operator's words refer to."""

    candidates: list[dict[str, Any]] = field(default_factory=list)
    selected: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    rejected: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExistingWorkRelationshipResolution:
    """How this message relates to work that already exists (plan §5)."""

    relationship: str = "new_work"
    # new_work | restatement_of_existing | revision_of_plan | lifecycle_op
    matched_plan_record_id: str = ""
    matched_objective_id: str = ""
    matched_packet_id: str = ""
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MaterialAmbiguity:
    """One ambiguity that changes scope/target/authority — needs the operator."""

    dimension: str = ""
    description: str = ""
    options: list[dict[str, Any]] = field(default_factory=list)
    question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntentResolution:
    """The protocol's output — wraps the legacy IntentSpec as compat signal."""

    intent_id: str = ""
    intent_class: str = IntentClass.COMMUNICATE.value
    planning_scale: str = PlanningScale.NONE.value
    principal_context: dict[str, Any] = field(default_factory=dict)
    work_scope: dict[str, Any] = field(default_factory=dict)
    reference_resolution: dict[str, Any] = field(default_factory=dict)
    existing_work_resolution: dict[str, Any] = field(default_factory=dict)
    material_assumptions: list[str] = field(default_factory=list)
    material_ambiguities: list[dict[str, Any]] = field(default_factory=list)
    clarification_required: bool = False
    clarification_questions: list[dict[str, str]] = field(default_factory=list)
    assessment_state: str = IntentAssessmentState.SUFFICIENTLY_SPECIFIED.value
    decision_requirement: str = DecisionRequirement.NOT_REQUIRED.value
    risk_level: str = "low"
    correlation_id: str = ""
    compat_spec: dict[str, Any] = field(default_factory=dict)
    deterministic: bool = True
    resolved_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentResolution:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def creates_work(self) -> bool:
        return self.intent_class in (
            IntentClass.CREATE_TASK.value,
            IntentClass.CREATE_OBJECTIVE.value,
        )


# ── Deterministic classification tables ──────────────────────────────────────

_DECISION_RE = re.compile(
    r"^\s*(approve|reject|deny|sign\s+off\s+on)\b|\b(approve|reject|deny)\s+(that|the|this)\s+(plan|task|decision|it)\b",
    re.IGNORECASE,
)
_CANCEL_RE = re.compile(
    r"\b(cancel|abort|scrap|kill)\b.*\b(plan|task|objective|work|it|that)\b", re.IGNORECASE
)
_PAUSE_RE = re.compile(
    r"\b(pause|hold|suspend)\b.*\b(plan|task|objective|work|it|that)\b", re.IGNORECASE
)
_RESUME_RE = re.compile(r"\b(resume|unpause|reactivate)\b", re.IGNORECASE)
_LINK_RE = re.compile(r"\b(attach|link|connect)\b.+\bto\b", re.IGNORECASE)
_UNLINK_RE = re.compile(r"\b(unlink|detach|disconnect)\b", re.IGNORECASE)
_REPRIORITIZE_RE = re.compile(
    r"\b(prioriti[sz]e|deprioriti[sz]e|bump|raise|lower)\b.*\b(priority|first|top)\b|\bpriority\b.*\b(up|down|high|low)\b",
    re.IGNORECASE,
)
_REORDER_RE = re.compile(
    r"\b(reorder|resequence)\b|\b(move|put)\b.+\b(before|after)\b|\bdepends?\s+on\b", re.IGNORECASE
)
_EXECUTE_RE = re.compile(
    r"\b(execute|run|start|kick\s*off|launch)\b.*\b(plan|packet|task|work|it)\b", re.IGNORECASE
)
_QUERY_RE = re.compile(
    r"^\s*(what|where|when|who|how|why|show|list|status|is|are|do|does|did)\b", re.IGNORECASE
)
_REVISION_RE = re.compile(
    r"\b(add|remove|drop|delete|rename|retitle|change|swap|replace|instead|also include|move)\b",
    re.IGNORECASE,
)
_VAGUE_REF_RE = re.compile(r"\b(that|this|it|the plan|the task|the objective)\b", re.IGNORECASE)
_PLAN_ID_RE = re.compile(r"\bopr-[0-9a-f]{6,}\b", re.IGNORECASE)
_GOAL_ID_RE = re.compile(r"\bgoal-[0-9a-f]{6,}\b", re.IGNORECASE)

_PORTFOLIO_SIGNALS = re.compile(
    r"\b(portfolio|every\s+(company|venture|projection)|company-?wide|all\s+(companies|ventures|projections)|institution|empire)\b",
    re.IGNORECASE,
)
_PROGRAM_SIGNALS = re.compile(
    r"\b(program|multi-?phase|roadmap|across\s+\w+\s+and\s+\w+|end[- ]to[- ]end)\b", re.IGNORECASE
)

_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")
_STOP = frozenset(
    "the and for with that this from into all our your are was to of in on a an".split()
)
_LIST_SIGNAL_RE = re.compile(r"\b\w+\b(?:\s*,\s*\b\w+\b){2,}")
_FILE_ID_RE = re.compile(r"[A-Za-z0-9_]+(?:[./][A-Za-z0-9_]+)+")
_OBJECTIVE_WORD_RE = re.compile(r"\bobjective\b", re.IGNORECASE)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP)


def _similarity(a: str, b: str) -> float:
    """Overlap coefficient — catches a short reference contained in a longer
    objective statement, which plain Jaccard under-scores."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _looks_atomic(text: str) -> bool:
    """One bounded target, no breadth signals → capture as a single Task."""
    if _LIST_SIGNAL_RE.search(text):
        return False
    if _PORTFOLIO_SIGNALS.search(text) or _PROGRAM_SIGNALS.search(text):
        return False
    if len(_FILE_ID_RE.findall(text)) > 1:
        return False
    return len(text.split()) <= 14


_RESTATEMENT_THRESHOLD = 0.75
_ALTERNATIVE_THRESHOLD = 0.40


def planning_operation_key(tenant_id: str, conversation_id: str, client_message_id: str) -> str:
    """§23.2 — the retry-idempotency key for one planning operation."""
    digest = hashlib.sha256(
        f"{tenant_id}|{conversation_id}|{client_message_id}".encode()
    ).hexdigest()
    return f"plnop-{digest[:16]}"


# ── The protocol ─────────────────────────────────────────────────────────────


class OperatorIntentProtocol:
    """The canonical intent seam. Deterministic spine; injectable governance."""

    def __init__(
        self,
        store: PlanningStore | None = None,
        goal_registry: Any | None = None,
        event_spine: Any | None = None,
        mutation_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._store = store or PlanningStore()
        self._goal_registry = goal_registry
        self._event_spine = event_spine
        self._mutation_runner = mutation_runner

    # ── Lazy canonical collaborators ────────────────────────────────────

    def _goals(self) -> Any:
        if self._goal_registry is None:
            from substrate.organism.strategic_gap_engine import GoalRegistry

            self._goal_registry = GoalRegistry()
        return self._goal_registry

    def _spine(self) -> Any:
        if self._event_spine is None:
            from substrate.organism.event_spine import get_shared_event_spine

            self._event_spine = get_shared_event_spine()
        return self._event_spine

    def _runner(self) -> Callable[..., Any]:
        if self._mutation_runner is not None:
            return self._mutation_runner
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        return _substrate_native_governed_mutation

    def _emit(
        self,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str,
    ) -> None:
        try:
            from substrate.organism.event_spine import EventDomain

            self._spine().emit(
                domain=EventDomain.OPERATOR,
                event_type=event_type,
                source="operator_intent_protocol",
                data=data,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            logger.debug("attribution event emit failed (%s): %s", event_type, exc)

    # ── Resolution (pure of stores; reads only the frame) ───────────────

    def resolve(
        self,
        text: str,
        principal: PrincipalContext,
        work_scope: WorkScope,
        frame: ContextFrame,
        client_message_id: str = "",
    ) -> IntentResolution:
        """Deterministically resolve one operator turn to an IntentResolution."""
        text = (text or "").strip()
        spec = IntentSpec.from_intent(
            text, org_id=work_scope.legacy_org_id or None, user_id=principal.principal_id or None
        )
        resolution = IntentResolution(
            intent_id=spec.intent_id,
            principal_context=principal.to_dict(),
            work_scope=work_scope.to_dict(),
            compat_spec=spec.to_dict(),
            risk_level=spec.risk_level,
            correlation_id=planning_operation_key(
                work_scope.tenant_id, frame.conversation_id, client_message_id
            ),
        )

        references = self._resolve_references(text, frame)
        resolution.reference_resolution = references.to_dict()

        intent_class = self._classify(text, spec, frame, references)
        resolution.intent_class = intent_class.value

        # CROSS-CONVERSATION scope discipline: pending-decision plans enter a
        # fresh conversation's frame for DECISION resolution (§5 "pending
        # Decisions"), but a deictic reference ("cancel it") from another
        # thread must NEVER bind to them for any other lifecycle op without
        # an EXPLICIT id — field run 20260722T213321Z: the pending plan made
        # "Cancel it." resolvable and s11's guaranteed clarification vanished.
        if intent_class != IntentClass.PROVIDE_DECISION:
            demoted = [
                c
                for c in references.candidates
                if c.get("cross_conversation") and c.get("match") != "explicit_id"
            ]
            if demoted:
                references.candidates = [c for c in references.candidates if c not in demoted]
                if references.selected in demoted:
                    references.selected = {}
                    references.confidence = 0.0
                references.rejected.extend(
                    {
                        "plan_record_id": c.get("plan_record_id", ""),
                        "reason": "cross-conversation deictic binding refused (non-decision op)",
                    }
                    for c in demoted
                )
                resolution.reference_resolution = references.to_dict()

        existing = self._resolve_existing_work(text, intent_class, frame, references)
        resolution.existing_work_resolution = existing.to_dict()
        if existing.relationship == "restatement_of_existing":
            # Restatement resolves the EXISTING work — never new artifacts.
            resolution.intent_class = IntentClass.QUERY_STATE.value
            intent_class = IntentClass.QUERY_STATE
        elif existing.relationship == "revision_of_plan" and intent_class in (
            IntentClass.CREATE_OBJECTIVE,
            IntentClass.CREATE_TASK,
        ):
            resolution.intent_class = IntentClass.MODIFY_PLAN.value
            intent_class = IntentClass.MODIFY_PLAN

        resolution.planning_scale = self._scale_for(intent_class, text).value
        resolution.decision_requirement = (
            DecisionRequirement.REQUIRED.value
            if intent_class in (IntentClass.CREATE_OBJECTIVE, IntentClass.MODIFY_PLAN)
            else DecisionRequirement.NOT_REQUIRED.value
        )

        self._apply_ambiguity_policy(resolution, intent_class, text, references, frame)

        if intent_class == IntentClass.CREATE_OBJECTIVE and not resolution.clarification_required:
            self._apply_objective_assessment(resolution, text, spec)

        self._emit(
            "planning.intent_resolved",
            {
                "tenant_id": work_scope.tenant_id,
                "principal_id": principal.principal_id,
                "membership_id": principal.membership_id,
                "conversation_id": frame.conversation_id,
                "client_message_id": client_message_id,
                "intent_id": resolution.intent_id,
                "intent_class": resolution.intent_class,
                "planning_scale": resolution.planning_scale,
            },
            resolution.correlation_id,
        )
        return resolution

    def _classify(
        self,
        text: str,
        spec: IntentSpec,
        frame: ContextFrame,
        references: ReferenceResolution,
    ) -> IntentClass:
        # Clarification response: an open session is waiting on this conversation.
        try:
            active = self._store.find_active_session(frame.conversation_id)
        except Exception as exc:
            logger.debug("find_active_session failed (treated as none): %s", exc)
            active = None
        if active is not None and active.stage == "awaiting_clarification":
            return IntentClass.CLARIFICATION_RESPONSE

        if _DECISION_RE.search(text):
            return IntentClass.PROVIDE_DECISION
        if _CANCEL_RE.search(text):
            return IntentClass.CANCEL_WORK
        if _PAUSE_RE.search(text):
            return IntentClass.PAUSE_WORK
        if _RESUME_RE.search(text):
            return IntentClass.RESUME_WORK
        if _UNLINK_RE.search(text):
            return IntentClass.UNLINK_WORK
        if _LINK_RE.search(text) and references.candidates:
            return IntentClass.LINK_WORK
        if _REPRIORITIZE_RE.search(text):
            return IntentClass.REPRIORITIZE_WORK
        if _REORDER_RE.search(text) and references.candidates:
            return IntentClass.REORDER_DEPENDENCIES
        if _EXECUTE_RE.search(text):
            return IntentClass.REQUEST_EXECUTION
        if _REVISION_RE.search(text) and (references.selected or references.candidates):
            return IntentClass.MODIFY_PLAN

        from substrate.execution.planning.objective_classifier import is_objective

        if is_objective(text):
            # The deterministic objective detector fires on any concrete
            # directive; a single bounded target stays an atomic Task.
            if _looks_atomic(text):
                return IntentClass.CREATE_TASK
            return IntentClass.CREATE_OBJECTIVE
        if spec.is_directive:
            # Breadth signals make a directive an Objective even without the
            # detector's concreteness signal: portfolio/program/explicit word,
            # or a multi-part scope (enumerated list + non-atomic length).
            if (
                _PORTFOLIO_SIGNALS.search(text)
                or _PROGRAM_SIGNALS.search(text)
                or _OBJECTIVE_WORD_RE.search(text)
                or (_LIST_SIGNAL_RE.search(text) and not _looks_atomic(text))
            ):
                return IntentClass.CREATE_OBJECTIVE
            return IntentClass.CREATE_TASK
        if _QUERY_RE.search(text) or spec.intent_type == "observation":
            return IntentClass.QUERY_STATE
        return IntentClass.COMMUNICATE

    def _scale_for(self, intent_class: IntentClass, text: str) -> PlanningScale:
        if intent_class == IntentClass.CREATE_TASK:
            return PlanningScale.ATOMIC_TASK
        if intent_class not in (IntentClass.CREATE_OBJECTIVE, IntentClass.MODIFY_PLAN):
            return PlanningScale.NONE
        if _PORTFOLIO_SIGNALS.search(text):
            return PlanningScale.PORTFOLIO_OBJECTIVE
        if _PROGRAM_SIGNALS.search(text):
            return PlanningScale.PROGRAM_OBJECTIVE
        return PlanningScale.PROJECT_OBJECTIVE

    def _resolve_references(self, text: str, frame: ContextFrame) -> ReferenceResolution:
        resolution = ReferenceResolution()
        explicit_plan_ids = set(_PLAN_ID_RE.findall(text))
        explicit_goal_ids = set(_GOAL_ID_RE.findall(text))

        for plan in frame.current_plans:
            entry = {
                "kind": "plan",
                "plan_record_id": plan.get("plan_record_id", ""),
                "objective_id": plan.get("objective_id", ""),
                "title": plan.get("objective_text", "")[:120],
                "status": plan.get("status", ""),
                # Cross-conversation pending-decision entries are deictic-
                # bindable ONLY for PROVIDE_DECISION (resolve() demotes them
                # for every other lifecycle op unless explicitly addressed).
                "cross_conversation": bool(plan.get("cross_conversation")),
            }
            if (
                plan.get("plan_record_id") in explicit_plan_ids
                or plan.get("objective_id") in explicit_goal_ids
            ):
                resolution.candidates.insert(0, {**entry, "match": "explicit_id"})
            else:
                similarity = _similarity(text, plan.get("objective_text", ""))
                if similarity >= _ALTERNATIVE_THRESHOLD:
                    resolution.candidates.append(
                        {**entry, "match": "similarity", "confidence": round(similarity, 2)}
                    )

        # Cross-conversation durable resolution (test L): an EXPLICIT plan id
        # resolves through the store even when the plan lives in another
        # conversation. Authority holds: a plan outside the caller's tenant is
        # REJECTED, never resolved (zero leakage).
        found_ids = {c["plan_record_id"] for c in resolution.candidates}
        for plan_id in explicit_plan_ids:
            if plan_id in found_ids:
                continue
            try:
                stored = self._store.get_plan(plan_id)
            except Exception:
                stored = None
            if stored is None:
                resolution.unresolved.append(f"explicit plan id not found: {plan_id}")
                continue
            plan_tenant = (stored.work_scope or {}).get("tenant_id", "")
            if plan_tenant and frame.tenant_id and plan_tenant != frame.tenant_id:
                resolution.rejected.append(
                    {"plan_record_id": plan_id, "reason": "outside caller tenant"}
                )
                continue
            resolution.candidates.insert(
                0,
                {
                    "kind": "plan",
                    "plan_record_id": stored.plan_record_id,
                    "objective_id": stored.objective_id,
                    "title": stored.objective_text[:120],
                    "status": stored.status,
                    "match": "explicit_id",
                },
            )

        vague = bool(_VAGUE_REF_RE.search(text))
        if vague and not resolution.candidates and frame.current_plans:
            # "that plan" with exactly one live plan in context resolves to it.
            live = [
                p for p in frame.current_plans if p.get("status") not in ("cancelled", "superseded")
            ]
            if len(live) == 1:
                resolution.candidates.append(
                    {
                        "kind": "plan",
                        "plan_record_id": live[0].get("plan_record_id", ""),
                        "objective_id": live[0].get("objective_id", ""),
                        "title": live[0].get("objective_text", "")[:120],
                        "status": live[0].get("status", ""),
                        "match": "sole_live_plan",
                        "cross_conversation": bool(live[0].get("cross_conversation")),
                    }
                )

        explicit = [c for c in resolution.candidates if c.get("match") == "explicit_id"]
        if len(explicit) == 1:
            resolution.selected = explicit[0]
            resolution.confidence = 1.0
        elif len(resolution.candidates) == 1:
            resolution.selected = resolution.candidates[0]
            resolution.confidence = float(resolution.candidates[0].get("confidence", 0.8) or 0.8)
        elif vague and not resolution.candidates:
            resolution.unresolved.append("vague reference with no matching object in context")
        return resolution

    def _resolve_existing_work(
        self,
        text: str,
        intent_class: IntentClass,
        frame: ContextFrame,
        references: ReferenceResolution,
    ) -> ExistingWorkRelationshipResolution:
        resolution = ExistingWorkRelationshipResolution()
        if intent_class in (
            IntentClass.CANCEL_WORK,
            IntentClass.PAUSE_WORK,
            IntentClass.RESUME_WORK,
            IntentClass.LINK_WORK,
            IntentClass.UNLINK_WORK,
            IntentClass.REPRIORITIZE_WORK,
            IntentClass.REORDER_DEPENDENCIES,
            IntentClass.PROVIDE_DECISION,
        ):
            resolution.relationship = "lifecycle_op"
            if references.selected:
                resolution.matched_plan_record_id = references.selected.get("plan_record_id", "")
                resolution.matched_objective_id = references.selected.get("objective_id", "")
                resolution.confidence = references.confidence
            return resolution

        if intent_class not in (
            IntentClass.CREATE_OBJECTIVE,
            IntentClass.CREATE_TASK,
            IntentClass.MODIFY_PLAN,
        ):
            return resolution

        has_revision_verbs = bool(_REVISION_RE.search(text))

        # For an atomic CREATE_TASK, a rephrase must resolve against the EXISTING
        # TASK it restates — not only against plans. current_tasks carries prior
        # operator WorkPackets (populated by build_context_frame); a Task never
        # populates current_plans, so without this a rephrased task deterministic-
        # ally missed every candidate and a duplicate packet was created (field
        # run 20260723T025829Z s05: packets 10→11). Task restatement is dedup —
        # a matched task is authoritative and short-circuits before plan matching.
        if intent_class == IntentClass.CREATE_TASK and not has_revision_verbs:
            text_paths = set(_FILE_ID_RE.findall(text))
            task_best: tuple[float, dict[str, Any], str] | None = None
            for task in frame.current_tasks:
                if str(task.get("status", "")).lower() in ("cancelled", "abandoned"):
                    continue
                task_text = task.get("objective_text", "")
                similarity = _similarity(text, task_text)
                # A shared concrete file-path identifier is a high-specificity
                # duplicate signal: two task statements naming the SAME file path
                # are the same work even when surrounding-verb phrasing dilutes the
                # token-overlap coefficient below threshold (field run
                # 20260723T025829Z: "Fix the failing import in X" vs "Go patch that
                # broken import over in X so the module loads" scored 0.667 < 0.75
                # yet both name transports/api/voice.py). Require at least MODERATE
                # overlap alongside the shared path so a mere incidental path
                # mention never collapses two genuinely different tasks.
                shared_path = bool(text_paths & set(_FILE_ID_RE.findall(task_text)))
                is_restatement = similarity >= _RESTATEMENT_THRESHOLD or (
                    shared_path and similarity >= _ALTERNATIVE_THRESHOLD
                )
                reason = "shared file-path identifier" if shared_path else "high token overlap"
                if is_restatement and (task_best is None or similarity > task_best[0]):
                    task_best = (similarity, task, reason)
            if task_best is not None:
                resolution.relationship = "restatement_of_existing"
                resolution.matched_packet_id = task_best[1].get("packet_id", "")
                resolution.confidence = task_best[0]
                resolution.reasoning = f"restatement of an existing Task ({task_best[2]})"
                return resolution

        best: tuple[float, dict[str, Any]] | None = None
        for plan in frame.current_plans:
            if plan.get("status") in ("cancelled", "superseded", "rejected"):
                continue
            similarity = _similarity(text, plan.get("objective_text", ""))
            if similarity >= _ALTERNATIVE_THRESHOLD:
                entry = {
                    "plan_record_id": plan.get("plan_record_id", ""),
                    "objective_id": plan.get("objective_id", ""),
                    "title": plan.get("objective_text", "")[:120],
                    "confidence": round(similarity, 2),
                }
                resolution.alternatives.append(entry)
                if best is None or similarity > best[0]:
                    best = (similarity, entry)

        resolution.alternatives.sort(key=lambda a: a["confidence"], reverse=True)

        if best is not None and best[0] >= _RESTATEMENT_THRESHOLD and not has_revision_verbs:
            resolution.relationship = "restatement_of_existing"
            resolution.matched_plan_record_id = best[1]["plan_record_id"]
            resolution.matched_objective_id = best[1]["objective_id"]
            resolution.confidence = best[0]
            resolution.reasoning = "high-similarity restatement of an existing live plan"
        elif has_revision_verbs and (best is not None or references.selected):
            # A revision needs a resolved target: either a high-similarity
            # match or an explicitly/sole-plan-resolved reference.
            target = (
                best[1]
                if best is not None and best[0] >= _RESTATEMENT_THRESHOLD
                else (references.selected or (best[1] if best is not None else {}))
            )
            if target:
                resolution.relationship = "revision_of_plan"
                resolution.matched_plan_record_id = target.get("plan_record_id", "")
                resolution.matched_objective_id = target.get("objective_id", "")
                resolution.confidence = best[0] if best is not None else references.confidence
                resolution.reasoning = "revision verbs against a resolved existing plan"
        return resolution

    def _apply_ambiguity_policy(
        self,
        resolution: IntentResolution,
        intent_class: IntentClass,
        text: str,
        references: ReferenceResolution,
        frame: ContextFrame,
    ) -> None:
        """HIGH → proceed; MODERATE+reversible → visible assumption;
        MATERIAL → exactly one targeted clarification."""
        needs_target = intent_class in (
            IntentClass.PROVIDE_DECISION,
            IntentClass.MODIFY_PLAN,
            IntentClass.CANCEL_WORK,
            IntentClass.PAUSE_WORK,
            IntentClass.RESUME_WORK,
            IntentClass.LINK_WORK,
            IntentClass.REORDER_DEPENDENCIES,
        )
        if not needs_target:
            return
        candidates = references.candidates
        if references.selected:
            if references.confidence < 1.0:
                resolution.material_assumptions.append(
                    f"interpreting the reference as {references.selected.get('title', '')!r} "
                    f"({references.selected.get('plan_record_id', '')})"
                )
            return
        if len(candidates) > 1:
            ambiguity = MaterialAmbiguity(
                dimension="target",
                description="multiple existing plans match this reference",
                options=[
                    {"plan_record_id": c.get("plan_record_id", ""), "title": c.get("title", "")}
                    for c in candidates[:4]
                ],
                question="Which plan do you mean: "
                + " or ".join(f"{c.get('title', '')!r}" for c in candidates[:4])
                + "?",
            )
            resolution.material_ambiguities.append(ambiguity.to_dict())
            resolution.clarification_required = True
            resolution.clarification_questions = [
                {"question": ambiguity.question, "dimension": ambiguity.dimension}
            ]
            resolution.assessment_state = IntentAssessmentState.CLARIFICATION_REQUIRED.value
        elif not candidates:
            ambiguity = MaterialAmbiguity(
                dimension="target",
                description="no matching object found for the reference",
                question="Which plan or task are you referring to?",
            )
            resolution.material_ambiguities.append(ambiguity.to_dict())
            resolution.clarification_required = True
            resolution.clarification_questions = [
                {"question": ambiguity.question, "dimension": ambiguity.dimension}
            ]
            resolution.assessment_state = IntentAssessmentState.CLARIFICATION_REQUIRED.value

    def _apply_objective_assessment(
        self, resolution: IntentResolution, text: str, spec: IntentSpec
    ) -> None:
        from substrate.execution.planning.objective_classifier import assess

        assessment = assess(text, spec)
        resolution.assessment_state = assessment.state
        if assessment.state == IntentAssessmentState.CLARIFICATION_REQUIRED.value:
            resolution.clarification_required = True
            resolution.clarification_questions = list(assessment.clarification_questions)
        elif assessment.state in (
            IntentAssessmentState.UNSUPPORTED.value,
            IntentAssessmentState.PROHIBITED.value,
        ):
            resolution.decision_requirement = DecisionRequirement.NOT_REQUIRED.value

    # ── Planning unit of work (§22.2 / §23.2) ────────────────────────────

    def begin_planning_operation(
        self,
        resolution: IntentResolution,
        objective_text: str,
        conversation_id: str,
        message_id: str = "",
        client_message_id: str = "",
    ) -> PlanningSession:
        """Resolve-or-create the planning session + canonical Objective.

        One recoverable logical operation: retries keyed by
        (tenant_id, conversation_id, client_message_id) reuse the session AND
        the exact persisted objective_id; partial failure leaves the session
        at a FAILED marker (recoverable) and the Goal in its valid DRAFT
        state — never a duplicate, never a phantom "planned" render.
        Fails closed without principal+tenant+membership.
        """
        principal = PrincipalContext.from_dict(resolution.principal_context)
        principal.require_work_authority()
        scope = WorkScope.from_dict(resolution.work_scope)
        scope.validate()

        fingerprint = message_fingerprint(objective_text)
        existing = self._store.find_session_by_idempotency(
            conversation_id, client_message_id, fingerprint
        )
        if existing is not None and existing.objective_id:
            # Retry after (or during) a completed objective resolution: reuse
            # the exact objective id; emit NO duplicate creation events.
            if existing.operation_stage in (
                PlanningStageMarker.FAILED.value,
                PlanningStageMarker.RESOLVING_OBJECTIVE.value,
            ):
                existing.operation_stage = PlanningStageMarker.OBJECTIVE_RESOLVED.value
                existing.operation_error = ""
                existing.updated_at = time.time()
                self._store.update_session(existing)
            return existing

        if existing is not None:
            session = existing
        else:
            session = PlanningSession(
                conversation_id=conversation_id,
                message_id=message_id,
                client_message_id=client_message_id,
                message_fingerprint=fingerprint,
                tenant_id=scope.tenant_id,
                principal_id=principal.principal_id,
                membership_id=principal.membership_id,
                intent_id=resolution.intent_id,
                objective_text=objective_text,
                assessment={"state": resolution.assessment_state},
                stage="assessed",
                operation_stage=PlanningStageMarker.RESOLVING_OBJECTIVE.value,
            )

            def _open_session() -> tuple[str, bool]:
                self._store.append_session(session)
                return (f"planning session opened: {session.session_id}", True)

            self._governed(
                ASSESS_MUTATION_NAME,
                f"open planning session for: {objective_text[:80]}",
                _open_session,
                {"session_id": session.session_id, "tenant_id": scope.tenant_id},
            )

        # Canonical Objective identity — governed create-or-reuse (§3, §22.1).
        objective_key = fingerprint
        outcome: dict[str, Any] = {}

        def _write_goal() -> tuple[str, bool]:
            goal, created = self._goals().create_or_reuse_objective(
                tenant_id=scope.tenant_id,
                objective_key=objective_key,
                scope_hash=scope.scope_hash(),
                title=objective_text[:120],
                description=objective_text,
            )
            outcome["goal_id"] = goal.goal_id
            outcome["created"] = created
            return (f"objective {'created' if created else 'reused'}: {goal.goal_id}", True)

        try:
            response = self._governed(
                GOAL_WRITE_MUTATION_NAME,
                f"resolve canonical objective for: {objective_text[:80]}",
                _write_goal,
                {
                    "session_id": session.session_id,
                    "tenant_id": scope.tenant_id,
                    "correlation_id": resolution.correlation_id,
                },
            )
            governed_ok = bool(getattr(response, "success", False)) and "goal_id" in outcome
        except Exception as exc:
            logger.error("objective resolution failed: %s", exc)
            governed_ok = False
            session.operation_error = str(exc)

        if not governed_ok:
            session.operation_stage = PlanningStageMarker.FAILED.value
            session.operation_error = session.operation_error or "objective goal write rejected"
            session.updated_at = time.time()
            self._store.update_session(session)
            raise RuntimeError(
                f"planning operation failed at objective resolution: {session.operation_error}"
            )

        # §23.2: objective_id persists on the session BEFORE planning continues.
        session.objective_id = outcome["goal_id"]
        session.operation_stage = PlanningStageMarker.OBJECTIVE_RESOLVED.value
        session.updated_at = time.time()
        self._store.update_session(session)

        if outcome.get("created"):
            self._emit(
                "planning.objective_created",
                {
                    "tenant_id": scope.tenant_id,
                    "principal_id": principal.principal_id,
                    "membership_id": principal.membership_id,
                    "conversation_id": conversation_id,
                    "client_message_id": client_message_id,
                    "intent_id": resolution.intent_id,
                    "objective_id": session.objective_id,
                },
                resolution.correlation_id,
            )
        self._emit(
            "planning.objective_resolved",
            {
                "tenant_id": scope.tenant_id,
                "conversation_id": conversation_id,
                "intent_id": resolution.intent_id,
                "objective_id": session.objective_id,
                "reused": not outcome.get("created", False),
            },
            resolution.correlation_id,
        )
        return session

    def record_clarification(
        self,
        resolution: IntentResolution,
        objective_text: str,
        conversation_id: str,
        client_message_id: str = "",
        question: str = "",
    ) -> PlanningSession:
        """Persist the awaiting-clarification session so the operator's NEXT
        message resumes it (§5 CLARIFICATION_RESPONSE — previously a dead
        branch, adversarial-review finding). Idempotent per operation key."""
        fingerprint = message_fingerprint(objective_text)
        existing = self._store.find_session_by_idempotency(
            conversation_id, client_message_id, fingerprint
        )
        if existing is not None:
            return existing
        scope = WorkScope.from_dict(resolution.work_scope)
        session = PlanningSession(
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            message_fingerprint=fingerprint,
            tenant_id=scope.tenant_id,
            intent_id=resolution.intent_id,
            objective_text=objective_text,
            assessment={"state": resolution.assessment_state, "question": question},
            stage="awaiting_clarification",
        )

        def _open() -> tuple[str, bool]:
            self._store.append_session(session)
            return (f"clarification session opened: {session.session_id}", True)

        response = self._governed(
            ASSESS_MUTATION_NAME,
            f"hold for clarification: {question[:80]}",
            _open,
            {"session_id": session.session_id, "tenant_id": scope.tenant_id},
        )
        # Verify the governed write actually landed — matching begin_planning_
        # operation / capture_task. If governance denies the write, append_session
        # never ran; returning an unpersisted session would silently break the
        # clarification loop (the next operator message finds no active session).
        if not bool(getattr(response, "success", False)):
            raise RuntimeError(
                f"clarification hold rejected by governance: {getattr(response, 'output', '')}"
            )
        return session

    def resume_clarification(self, session: PlanningSession, answer: str) -> str:
        """Fold the operator's answer into the held objective and release the
        session. Returns the merged objective text for re-resolution."""
        merged = f"{session.objective_text}\n{answer.strip()}"
        session.clarification_history.append(
            {"question": str((session.assessment or {}).get("question", "")), "answer": answer}
        )
        session.stage = "assessed"
        session.objective_text = merged
        session.updated_at = time.time()

        def _release() -> tuple[str, bool]:
            self._store.update_session(session)
            return (f"clarification resolved: {session.session_id}", True)

        response = self._governed(
            ASSESS_MUTATION_NAME,
            f"clarification answered: {answer[:80]}",
            _release,
            {"session_id": session.session_id, "tenant_id": session.tenant_id},
        )
        # Verify the governed write landed. If governance denies it, update_session
        # never ran; returning the locally-merged text as if persisted would leave
        # a stale session and break clarification resumption on the next message.
        if not bool(getattr(response, "success", False)):
            raise RuntimeError(
                f"clarification resume rejected by governance: {getattr(response, 'output', '')}"
            )
        return merged

    def capture_task(
        self,
        resolution: IntentResolution,
        task_text: str,
        conversation_id: str,
        client_message_id: str = "",
        work_queue: Any | None = None,
    ) -> Any:
        """Capture one atomic Task as a canonical WorkPacket (§23.1).

        No Objective, no Plan, NO HUD Decision — the packet simply exists at
        most PLANNED with a non-empty approval gate (non-executable until a
        future execution-authorization decision, Wave 2). Idempotent per
        (tenant, conversation, client_message_id): a retry returns the
        existing packet. Fails closed without principal+tenant+membership.
        """
        principal = PrincipalContext.from_dict(resolution.principal_context)
        principal.require_work_authority()
        scope = WorkScope.from_dict(resolution.work_scope)
        scope.validate()

        from substrate.contracts.work_context import WorkLineageContext
        from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

        if work_queue is None:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            work_queue = UniversalWorkQueue()

        # An EMPTY client_message_id would collapse this key to a
        # per-conversation constant — the second distinct task in the same
        # conversation would silently return the first packet (adversarial-
        # review MAJOR). Fall back to the task-text fingerprint: identical
        # retries still dedupe, distinct tasks never collide.
        effective_message_id = client_message_id or message_fingerprint(task_text)
        operation_key = planning_operation_key(
            scope.tenant_id, conversation_id, effective_message_id
        )
        for existing in work_queue.all_packets():
            if existing.source_type == "operator_task" and existing.source_id == operation_key:
                return existing

        from substrate.execution.planning.archetypes import resolve_archetype

        archetype = resolve_archetype(task_text, scope)
        lineage = WorkLineageContext(
            decomposition_level=0,
            end_state_contribution=task_text[:200],
            originating_intent_id=resolution.intent_id,
            originating_conversation_id=conversation_id,
        )
        packet = WorkPacket(
            title=task_text[:120],
            user_intent=task_text[:300],
            desired_end_state=task_text[:300],
            intent_summary=f"atomic {archetype.archetype_id} task",
            domain=archetype.archetype_id,
            source_type="operator_task",
            source_id=operation_key,
            risk_class=resolution.risk_level
            if resolution.risk_level in ("low", "medium", "high")
            else "low",
            required_role_contracts=[archetype.default_role_contract_id],
            approval_gates=["execution_authorization_required"],
            work_scope=scope.to_dict(),
            lineage=lineage.to_dict(),
            requirements={
                "work_archetype_ref": f"{archetype.archetype_id}@v{archetype.archetype_version}",
                "required_skill_refs": [dict(r) for r in archetype.required_skill_refs],
            },
        )

        def _write() -> tuple[str, bool]:
            work_queue.ingest_work_packet(packet)
            work_queue.update_packet_status(
                packet.packet_id, PacketLifecycleStatus.CLASSIFIED, "operator task captured"
            )
            work_queue.update_packet_status(
                packet.packet_id,
                PacketLifecycleStatus.PLANNED,
                "captured — execution NOT authorized (no HUD decision exists)",
            )
            return (f"task captured: {packet.packet_id}", True)

        response = self._governed(
            "operator_task_capture",
            f"capture atomic operator task: {task_text[:80]}",
            _write,
            {
                "packet_id": packet.packet_id,
                "tenant_id": scope.tenant_id,
                "correlation_id": resolution.correlation_id,
            },
        )
        if not bool(getattr(response, "success", False)):
            raise RuntimeError(
                f"task capture rejected by governance: {getattr(response, 'output', '')}"
            )
        self._emit(
            "planning.task_captured",
            {
                "tenant_id": scope.tenant_id,
                "principal_id": principal.principal_id,
                "membership_id": principal.membership_id,
                "conversation_id": conversation_id,
                "client_message_id": client_message_id,
                "intent_id": resolution.intent_id,
                "task_ids": [packet.packet_id],
            },
            resolution.correlation_id,
        )
        return work_queue.get_packet(packet.packet_id)

    def link_task_to_objective(
        self,
        resolution: IntentResolution,
        packet_id: str,
        objective_id: str,
        work_queue: Any | None = None,
    ) -> Any:
        """LINK_WORK (test D): attach an existing Task to a canonical Objective.

        Lineage-only mutation — no new Task, no new Objective, no duplicate of
        either. Idempotent: linking an already-linked pair is a no-op. Fails
        closed without work authority, on an unknown packet/objective, and on
        any cross-tenant pairing (zero leakage).
        """
        principal = PrincipalContext.from_dict(resolution.principal_context)
        principal.require_work_authority()
        scope = WorkScope.from_dict(resolution.work_scope)
        scope.validate()

        if work_queue is None:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            work_queue = UniversalWorkQueue()

        packet = work_queue.get_packet(packet_id)
        if packet is None:
            raise ValueError(f"unknown task: {packet_id}")
        goal = self._goals().get(objective_id)
        if goal is None:
            raise ValueError(f"unknown objective: {objective_id}")
        packet_tenant = (packet.work_scope or {}).get("tenant_id", "")
        for name, tenant in (("task", packet_tenant), ("objective", goal.tenant_id)):
            if tenant and tenant != scope.tenant_id:
                raise ValueError(f"cross-tenant link rejected: {name} outside caller tenant")

        lineage = dict(packet.lineage or {})
        if lineage.get("objective_id") == objective_id:
            return packet  # idempotent — already attached

        def _link() -> tuple[str, bool]:
            lineage["objective_id"] = objective_id
            refs = list(lineage.get("goal_refs", []))
            if objective_id not in refs:
                refs.append(objective_id)
            lineage["goal_refs"] = refs
            packet.lineage = lineage
            work_queue._save()
            return (f"task {packet_id} linked to objective {objective_id}", True)

        response = self._governed(
            "objective_task_link",
            f"attach task {packet_id} to objective {objective_id}",
            _link,
            {
                "packet_id": packet_id,
                "objective_id": objective_id,
                "tenant_id": scope.tenant_id,
                "correlation_id": resolution.correlation_id,
            },
        )
        if not bool(getattr(response, "success", False)):
            raise RuntimeError(
                f"task link rejected by governance: {getattr(response, 'output', '')}"
            )
        self._emit(
            "planning.work_linked",
            {
                "tenant_id": scope.tenant_id,
                "packet_id": packet_id,
                "objective_id": objective_id,
                "intent_id": resolution.intent_id,
            },
            resolution.correlation_id,
        )
        return work_queue.get_packet(packet_id)

    def plan_objective(
        self,
        resolution: IntentResolution,
        objective_text: str,
        conversation_id: str,
        message_id: str = "",
        client_message_id: str = "",
        work_queue: Any | None = None,
    ) -> tuple[PlanningSession, Any]:
        """The single transport-facing planning entry: objective → committed plan.

        Runs the complete §22.2 unit of work — objective resolution, bounded
        grounding, state derivation, archetype resolution, plan compilation,
        canonical Task materialization (max PLANNED, non-executable), decision
        readiness — and returns (session, ObjectivePlanRecord). Retries are
        idempotent end-to-end.
        """
        session = self.begin_planning_operation(
            resolution,
            objective_text,
            conversation_id,
            message_id=message_id,
            client_message_id=client_message_id,
        )
        scope = WorkScope.from_dict(resolution.work_scope)

        from substrate.execution.intent.intent_spec import IntentSpec
        from substrate.execution.planning.compiler import compose_plan_for_session
        from substrate.execution.planning.grounding import build_grounding_snapshot

        if work_queue is None:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            work_queue = UniversalWorkQueue()

        spec = IntentSpec.from_dict(resolution.compat_spec)
        snapshot = build_grounding_snapshot(
            spec,
            conversation_id,
            message_id or client_message_id,
            objective_text=objective_text,
        )
        plan = compose_plan_for_session(
            session=session,
            scope=scope,
            planning_scale=resolution.planning_scale,
            snapshot=snapshot,
            store=self._store,
            work_queue=work_queue,
            mutation_runner=self._runner(),
            event_emit=lambda event_type, data: self._emit(
                event_type, data, resolution.correlation_id
            ),
        )
        return session, plan

    def _governed(
        self,
        mutation_name: str,
        intent: str,
        execute_fn: Callable[[], tuple[str, bool]],
        metadata: dict[str, Any],
    ) -> Any:
        runner = self._runner()
        return runner(
            mutation_name=mutation_name,
            intent=intent,
            execute_fn=execute_fn,
            source="operator_intent_protocol",
            metadata=metadata,
        )


# ── Legacy read adapter (§23.5 — read-only, never a write path) ─────────────


def read_legacy_intent_loops(limit: int = 50) -> list[dict[str, Any]]:
    """Compatibility READ adapter over legacy IntentLoopRecords.

    Marked with source_type so surfaces render them visually distinct. This
    module never writes IntentLoopRecords and never invokes intent_loop_*
    mutations — enforced by tests/test_wave1_intent_protocol.py (test AN).
    """
    try:
        from substrate.execution.intent.loop import IntentLoopStore

        records = IntentLoopStore().query_recent(limit=limit)
    except Exception as exc:
        logger.debug("legacy intent-loop read unavailable: %s", exc)
        return []
    return [
        {
            "source_type": "intent_loop",
            "source_record_id": r.loop_id,
            "stage": r.stage,
            "spec": r.spec,
            "draft": r.draft,
            "created_at": r.created_at,
            "compatibility": True,
        }
        for r in records
    ]


__all__ = [
    "ASSESS_MUTATION_NAME",
    "GOAL_WRITE_MUTATION_NAME",
    "DecisionRequirement",
    "ExistingWorkRelationshipResolution",
    "IntentClass",
    "IntentResolution",
    "MaterialAmbiguity",
    "OperatorIntentProtocol",
    "PlanningScale",
    "ReferenceResolution",
    "planning_operation_key",
    "read_legacy_intent_loops",
]
