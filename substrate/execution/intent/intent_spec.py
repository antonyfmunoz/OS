"""IntentSpec — the typed, deterministic capture of one bounded operator intent.

P4S-31. The thinnest canonical shape for the MVP operating loop: operator raw
text → typed IntentSpec → WorkPacket draft. This module owns ONLY the typed
records (IntentSpec + WorkPacketDraft); the classification it depends on is the
existing deterministic ``substrate.operator.intent_router.IntentRouter`` and the
existing risk table ``substrate.workstation.intent_contract.extract_intent_risk``.
It defines NO new classifier and NO new risk vocabulary.

Deterministic-first (stop-condition enforced): ``IntentSpec.from_intent`` is a
pure function of the raw text plus runtime context — regex/keyword routing and a
lookup risk table, no LLM, no network. "All LLM providers down" still yields a
full IntentSpec and WorkPacketDraft.

Instance-agnostic: tenant/org identity is passed in from runtime context
(``substrate.state.context.context``), never a literal. The module carries no
founder/company/product string.

UMH substrate subsystem.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from substrate.operator.intent_router import IntentRouter, RouteType
from substrate.types import WorkPacketPriority, WorkPacketStatus
from substrate.workstation.intent_contract import extract_intent_risk


class IntentLoopStage(str, Enum):
    """The MVP operating-loop state machine stages.

    The gate HOLDS at AWAITING_APPROVAL: the loop never auto-advances to
    PROOF_RECORDED. Only an explicit governed approval moves it forward.
    """

    SUBMITTED = "submitted"
    SPEC_PARSED = "spec_parsed"
    PACKET_DRAFTED = "packet_drafted"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROOF_RECORDED = "proof_recorded"


# The bounded set of intent shapes this skeleton accepts. Anything that does not
# route to a directive-like RouteType is captured as OBSERVATION (a read/status
# intent) or CONVERSATION and produces a draft that is explicitly non-actionable
# — the skeleton never fabricates a work packet for pure chat.
_DIRECTIVE_ROUTES = frozenset({RouteType.WORK_PACKET, RouteType.HYBRID})


class IntentKind(str, Enum):
    """Bounded taxonomy of what the MVP loop accepts, derived deterministically
    from the existing router's RouteType — NOT a parallel classifier."""

    DIRECTIVE = "directive"  # work_packet / hybrid — produces an actionable draft
    OBSERVATION = "observation"  # status/read intent — draft is non-actionable
    CONVERSATION = "conversation"  # chat — draft is non-actionable
    APPROVAL = "approval"  # approve/reject an existing packet

    @classmethod
    def from_route(cls, route: RouteType) -> IntentKind:
        if route in _DIRECTIVE_ROUTES:
            return cls.DIRECTIVE
        if route == RouteType.OBSERVATION:
            return cls.OBSERVATION
        if route == RouteType.APPROVAL:
            return cls.APPROVAL
        return cls.CONVERSATION


_RISK_TO_PRIORITY: dict[str, WorkPacketPriority] = {
    "low": WorkPacketPriority.LOW,
    "medium": WorkPacketPriority.NORMAL,
    "high": WorkPacketPriority.HIGH,
}


@dataclass
class WorkPacketDraft:
    """A typed *draft* packet — the loop's proposed unit of work.

    This is deliberately NOT the heavy runtime ``substrate.types.WorkPacket``
    (which requires a governance_verdict_id / capability_id / trace_id it does
    not have yet). It is the pre-governance draft that the approval gate governs;
    it reuses ``WorkPacketStatus`` / ``WorkPacketPriority`` so its lifecycle
    vocabulary is the canonical one, not a parallel enum.
    """

    draft_id: str
    intent_id: str
    description: str
    status: str = WorkPacketStatus.PENDING.value
    priority: str = WorkPacketPriority.NORMAL.value
    risk_level: str = "medium"
    actionable: bool = True
    input_data: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkPacketDraft:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class IntentSpec:
    """Typed capture of one bounded operator intent.

    Built deterministically by :meth:`from_intent`. ``org_id`` / ``user_id`` come
    from runtime context passed by the caller — never a literal in this module.
    """

    intent_id: str
    raw_text: str
    intent_type: str
    route_type: str
    risk_level: str
    confidence: float
    org_id: str | None = None
    user_id: str | None = None
    extracted_entities: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""
    stage: str = IntentLoopStage.SPEC_PARSED.value
    created_at: float = field(default_factory=time.time)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentSpec:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def is_directive(self) -> bool:
        return self.intent_type == IntentKind.DIRECTIVE.value

    @classmethod
    def from_intent(
        cls,
        raw_text: str,
        org_id: str | None = None,
        user_id: str | None = None,
        router: IntentRouter | None = None,
    ) -> IntentSpec:
        """Deterministically parse raw operator text into a typed IntentSpec.

        Pure function of (raw_text, context): the existing IntentRouter does the
        regex/keyword routing (no LLM for clear intents; its optional classifier
        refinement is also deterministic) and extract_intent_risk does the risk
        lookup. No network, no provider call. Same input → same IntentSpec.
        """
        router = router or IntentRouter()
        classification = router.classify(raw_text)
        route = classification.route_type
        intent_type = IntentKind.from_route(route)

        # Risk: prefer the router's refined risk_class when it is non-default,
        # otherwise the deterministic verb table. Both are lookup-only.
        risk = classification.risk_class or "medium"
        if risk in ("", "low", "medium") and route in _DIRECTIVE_ROUTES:
            risk = extract_intent_risk(raw_text)

        return cls(
            intent_id=f"intent_{uuid.uuid4().hex[:12]}",
            raw_text=raw_text.strip(),
            intent_type=intent_type.value,
            route_type=route.value,
            risk_level=risk,
            confidence=classification.confidence,
            org_id=org_id,
            user_id=user_id,
            extracted_entities=dict(classification.extracted_entities),
            reasoning=classification.reasoning,
        )

    def to_draft(self) -> WorkPacketDraft:
        """Produce the typed WorkPacket draft for this intent.

        Directive intents produce an actionable draft; observation/conversation
        intents produce an explicitly non-actionable draft (actionable=False) so
        the skeleton never fabricates work for pure chat/status text.
        """
        priority = _RISK_TO_PRIORITY.get(self.risk_level, WorkPacketPriority.NORMAL)
        actionable = self.is_directive
        return WorkPacketDraft(
            draft_id=f"draft_{uuid.uuid4().hex[:12]}",
            intent_id=self.intent_id,
            description=self.raw_text[:300],
            status=WorkPacketStatus.PENDING.value,
            priority=priority.value,
            risk_level=self.risk_level,
            actionable=actionable,
            input_data={
                "intent_type": self.intent_type,
                "route_type": self.route_type,
                "extracted_entities": self.extracted_entities,
            },
        )


__all__ = [
    "IntentLoopStage",
    "IntentKind",
    "IntentSpec",
    "WorkPacketDraft",
]
