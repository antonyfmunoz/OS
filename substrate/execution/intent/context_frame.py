"""ContextFrame — the bounded interpretation context for one conversation turn.

Canonical Operator Intent Protocol input (plan §5): ONLY what can alter the
interpretation of the operator's message — principal/tenant identity, the
active conversation and its recent planning sessions, current Plans and Tasks
(bounded), pending Decisions, and bounded external-reality evidence. Never a
repository crawl, never cross-tenant retrieval (everything read here is
filtered by tenant_id when one is present).

Deterministic and failure-tolerant: every collector failure degrades to an
empty section — a missing section is recorded state, never an exception.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RECENT_TURNS = 12
_MAX_PLANS = 10
_MAX_TASKS = 25
_MAX_DECISIONS = 10
_MAX_EVIDENCE = 8


@dataclass
class ContextFrame:
    """Bounded, typed interpretation context for one operator turn."""

    tenant_id: str = ""
    principal_id: str = ""
    membership_id: str = ""
    conversation_id: str = ""
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    active_objects: list[dict[str, Any]] = field(default_factory=list)
    current_plans: list[dict[str, Any]] = field(default_factory=list)
    current_tasks: list[dict[str, Any]] = field(default_factory=list)
    pending_decisions: list[dict[str, Any]] = field(default_factory=list)
    memory_refs: list[dict[str, Any]] = field(default_factory=list)
    external_evidence: list[dict[str, Any]] = field(default_factory=list)
    truncated_sections: list[str] = field(default_factory=list)
    built_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextFrame:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def build_context_frame(
    tenant_id: str,
    principal_id: str,
    conversation_id: str,
    membership_id: str = "",
    recent_turns: list[dict[str, Any]] | None = None,
    active_objects: list[dict[str, Any]] | None = None,
    external_evidence: list[dict[str, Any]] | None = None,
    planning_store: Any | None = None,
    work_queue: Any | None = None,
) -> ContextFrame:
    """Assemble the bounded frame. Sections that fail to load stay empty.

    ``recent_turns`` / ``active_objects`` / ``external_evidence`` are provided
    by the transport (it owns conversation history and UI selection state);
    this builder bounds them and adds the substrate-owned planning sections.
    """
    frame = ContextFrame(
        tenant_id=tenant_id,
        principal_id=principal_id,
        membership_id=membership_id,
        conversation_id=conversation_id,
    )

    turns = list(recent_turns or [])
    if len(turns) > _MAX_RECENT_TURNS:
        frame.truncated_sections.append("recent_turns")
        turns = turns[-_MAX_RECENT_TURNS:]
    frame.recent_turns = turns

    frame.active_objects = list(active_objects or [])[:_MAX_TASKS]

    evidence = list(external_evidence or [])
    if len(evidence) > _MAX_EVIDENCE:
        frame.truncated_sections.append("external_evidence")
        evidence = evidence[:_MAX_EVIDENCE]
    frame.external_evidence = evidence

    # Current Plans for this conversation's tenant (bounded, newest first).
    try:
        if planning_store is None:
            from substrate.execution.planning.store import PlanningStore

            planning_store = PlanningStore()
        plans = planning_store.load_plans()
        scoped = []
        for plan in reversed(plans):
            d = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
            cross_conversation = False
            if conversation_id and d.get("conversation_id") not in ("", conversation_id):
                # PENDING-DECISION plans are tenant-visible frame context
                # regardless of conversation — §5 lists "pending Decisions"
                # as a frame section in their own right. Without this,
                # "Approve that plan." in a NEW thread had zero candidates
                # and the rail asked "which plan?" while exactly one
                # decidable plan existed (field run 20260722T205034Z).
                # Everything else stays conversation-scoped. Entries are
                # TAGGED so reference resolution refuses deictic binding for
                # non-decision lifecycle ops (protocol.resolve demotion —
                # field run 20260722T213321Z: "Cancel it." must still ask).
                if d.get("status") != "awaiting_approval":
                    continue
                cross_conversation = True
            # Tenant isolation (adversarial-review MAJOR): a plan from another
            # tenant must never enter this frame — reference/existing-work
            # resolution would otherwise match it by similarity.
            plan_tenant = (d.get("work_scope") or {}).get("tenant_id", "")
            if tenant_id and plan_tenant and plan_tenant != tenant_id:
                continue
            scoped.append(
                {
                    "plan_record_id": d.get("plan_record_id", ""),
                    "objective_id": d.get("objective_id", ""),
                    "objective_text": d.get("objective_text", ""),
                    "status": d.get("status", ""),
                    "graph_version": d.get("graph_version", 1),
                    "conversation_id": d.get("conversation_id", ""),
                    "workpacket_ids": list(d.get("workpacket_ids", [])),
                    "cross_conversation": cross_conversation,
                }
            )
            if len(scoped) >= _MAX_PLANS:
                frame.truncated_sections.append("current_plans")
                break
        frame.current_plans = scoped
    except Exception as exc:
        logger.debug("context frame: plan section unavailable: %s", exc)

    # Current Tasks (atomic operator WorkPackets) for this conversation's tenant,
    # bounded and newest-first. Without this, a rephrased task had NO existing
    # task to resolve against — task-restatement dedup could only match the plan
    # section (which a simple Task never populates), so a rephrase created a
    # duplicate packet nondeterministically (field run 20260723T025829Z s05:
    # packets 10→11). Existing-work resolution needs the prior task in the frame.
    try:
        if work_queue is None:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            work_queue = UniversalWorkQueue()
        task_rows: list[dict[str, Any]] = []
        for packet in reversed(list(work_queue.all_packets())):
            if getattr(packet, "source_type", "") != "operator_task":
                continue
            pscope = getattr(packet, "work_scope", {}) or {}
            ptenant = pscope.get("tenant_id", "") if isinstance(pscope, dict) else ""
            # Tenant isolation — a task from another tenant must never enter the
            # frame (same rule the plan section enforces).
            if tenant_id and ptenant and ptenant != tenant_id:
                continue
            task_rows.append(
                {
                    "packet_id": getattr(packet, "packet_id", ""),
                    # objective_text is the field existing-work resolution reads;
                    # a Task carries its intent in user_intent/title.
                    "objective_text": getattr(packet, "user_intent", "")
                    or getattr(packet, "title", ""),
                    "status": getattr(packet, "status", ""),
                    "conversation_id": (
                        pscope.get("conversation_id", "") if isinstance(pscope, dict) else ""
                    ),
                    "source_id": getattr(packet, "source_id", ""),
                }
            )
            if len(task_rows) >= _MAX_TASKS:
                frame.truncated_sections.append("current_tasks")
                break
        frame.current_tasks = task_rows
    except Exception as exc:
        logger.debug("context frame: task section unavailable: %s", exc)

    return frame


__all__ = ["ContextFrame", "build_context_frame"]
