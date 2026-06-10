"""Trigger chain engine — deterministic event→condition→action chains.

Vision events (operator_left, unknown_person, item_moved, etc.) can
trigger governed action sequences: preset switches, mode transitions,
notifications. All chains are auditable with timestamps, confidence,
and the triggering event.

No LLM in the chain evaluation path. Chains use debounce to prevent
rapid re-firing. Chain actions are governed by risk classification.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_CHAINS = 50
MAX_ACTIONS_PER_CHAIN = 10
MAX_CONDITIONS_PER_CHAIN = 5
MAX_CHAIN_HISTORY = 100


VISION_EVENTS = [
    "operator_left_room",
    "operator_entered_room",
    "unknown_person_entered",
    "tracked_item_moved",
    "tracked_item_disappeared",
    "door_zone_motion",
    "hands_on_keyboard",
    "hands_off_keyboard",
    "face_lost",
    "camera_lost_tracking",
    "profile_changed",
    "work_loop_blocked",
]

ACTION_TYPES = [
    "camera.apply_preset",
    "camera.ptz_move",
    "mode.set",
    "tracker.enable",
    "tracker.disable",
    "notify.operator",
    "notify.log",
]

RISK_LEVELS: dict[str, str] = {
    "camera.apply_preset": "low",
    "camera.ptz_move": "low",
    "mode.set": "medium",
    "tracker.enable": "low",
    "tracker.disable": "low",
    "notify.operator": "low",
    "notify.log": "low",
}


@dataclass
class ChainCondition:
    """A condition that must be true for the chain to fire."""

    field: str
    op: str  # "eq", "neq", "in", "not_in", "gt", "lt"
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "op": self.op, "value": self.value}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChainCondition:
        return cls(field=d.get("field", ""), op=d.get("op", "eq"), value=d.get("value"))

    def evaluate(self, context: dict[str, Any]) -> bool:
        actual = context.get(self.field)
        if self.op == "eq":
            return actual == self.value
        if self.op == "neq":
            return actual != self.value
        if self.op == "in":
            return actual in (self.value or [])
        if self.op == "not_in":
            return actual not in (self.value or [])
        if self.op == "gt":
            return (actual or 0) > (self.value or 0)
        if self.op == "lt":
            return (actual or 0) < (self.value or 0)
        return False


@dataclass
class ChainAction:
    """An action to execute when the chain fires."""

    action_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.action_type, **self.params}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChainAction:
        params = {k: v for k, v in d.items() if k != "type"}
        return cls(action_type=d.get("type", ""), params=params)


@dataclass
class ChainGovernance:
    """Governance metadata for a trigger chain."""

    risk: str = "low"
    requires_approval: bool = False
    audit: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"risk": self.risk, "requires_approval": self.requires_approval, "audit": self.audit}


@dataclass
class ChainFireRecord:
    """Audit record of a chain firing."""

    chain_id: str
    fired_at: float
    event: str
    confidence: float
    frame_id: str
    actions_taken: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "fired_at": self.fired_at,
            "event": self.event,
            "confidence": self.confidence,
            "frame_id": self.frame_id,
            "actions_taken": self.actions_taken,
            "explanation": self.explanation,
        }


@dataclass
class TriggerChain:
    """A complete trigger chain definition."""

    chain_id: str
    label: str
    enabled: bool = True
    trigger_event: str = ""
    trigger_zone: str = ""
    confidence_min: float = 0.5
    debounce_seconds: float = 3.0
    conditions: list[ChainCondition] = field(default_factory=list)
    actions: list[ChainAction] = field(default_factory=list)
    governance: ChainGovernance = field(default_factory=ChainGovernance)
    last_fired: float = 0.0
    fire_count: int = 0
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "label": self.label,
            "enabled": self.enabled,
            "trigger": {
                "event": self.trigger_event,
                "zone": self.trigger_zone,
                "confidence_min": self.confidence_min,
                "debounce_seconds": self.debounce_seconds,
            },
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "governance": self.governance.to_dict(),
            "last_fired": self.last_fired,
            "fire_count": self.fire_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TriggerChain:
        trigger = d.get("trigger", {})
        return cls(
            chain_id=d.get("chain_id", ""),
            label=d.get("label", ""),
            enabled=d.get("enabled", True),
            trigger_event=trigger.get("event", ""),
            trigger_zone=trigger.get("zone", ""),
            confidence_min=trigger.get("confidence_min", 0.5),
            debounce_seconds=trigger.get("debounce_seconds", 3.0),
            conditions=[ChainCondition.from_dict(c) for c in d.get("conditions", [])],
            actions=[ChainAction.from_dict(a) for a in d.get("actions", [])],
            governance=ChainGovernance(**d.get("governance", {})),
            last_fired=d.get("last_fired", 0.0),
            fire_count=d.get("fire_count", 0),
            created_at=d.get("created_at", 0.0),
        )


class TriggerChainManager:
    """Manages trigger chains and evaluates events against them."""

    def __init__(self) -> None:
        self._chains: dict[str, TriggerChain] = {}
        self._history: list[ChainFireRecord] = []

    def create_chain(
        self,
        label: str,
        trigger_event: str,
        actions: list[dict[str, Any]],
        conditions: list[dict[str, Any]] | None = None,
        trigger_zone: str = "",
        confidence_min: float = 0.5,
        debounce_seconds: float = 3.0,
        governance: dict[str, Any] | None = None,
    ) -> TriggerChain | None:
        if len(self._chains) >= MAX_CHAINS:
            logger.warning("max chains reached (%d)", MAX_CHAINS)
            return None
        if len(actions) > MAX_ACTIONS_PER_CHAIN:
            logger.warning("too many actions (%d > %d)", len(actions), MAX_ACTIONS_PER_CHAIN)
            return None

        chain_id = f"chain_{uuid.uuid4().hex[:8]}"
        now = time.time()

        parsed_actions = []
        for a in actions:
            action = ChainAction.from_dict(a)
            if action.action_type not in ACTION_TYPES:
                logger.warning("unknown action type: %s", action.action_type)
                return None
            parsed_actions.append(action)

        parsed_conditions = [ChainCondition.from_dict(c) for c in (conditions or [])]
        if len(parsed_conditions) > MAX_CONDITIONS_PER_CHAIN:
            logger.warning("too many conditions (%d)", len(parsed_conditions))
            return None

        gov_data = governance or {}
        max_risk = max(
            (RISK_LEVELS.get(a.action_type, "low") for a in parsed_actions),
            key=lambda r: ["low", "medium", "high"].index(r) if r in ["low", "medium", "high"] else 0,
        )
        gov = ChainGovernance(
            risk=max_risk,
            requires_approval=gov_data.get("requires_approval", max_risk == "high"),
            audit=gov_data.get("audit", True),
        )

        chain = TriggerChain(
            chain_id=chain_id,
            label=label,
            trigger_event=trigger_event,
            trigger_zone=trigger_zone,
            confidence_min=confidence_min,
            debounce_seconds=debounce_seconds,
            conditions=parsed_conditions,
            actions=parsed_actions,
            governance=gov,
            created_at=now,
        )
        self._chains[chain_id] = chain
        logger.info("chain created: %s (%s → %d actions)", chain_id, trigger_event, len(parsed_actions))
        return chain

    def delete_chain(self, chain_id: str) -> bool:
        if chain_id in self._chains:
            del self._chains[chain_id]
            return True
        return False

    def enable_chain(self, chain_id: str) -> bool:
        chain = self._chains.get(chain_id)
        if not chain:
            return False
        chain.enabled = True
        return True

    def disable_chain(self, chain_id: str) -> bool:
        chain = self._chains.get(chain_id)
        if not chain:
            return False
        chain.enabled = False
        return True

    def evaluate_event(
        self,
        event: str,
        confidence: float = 1.0,
        frame_id: str = "",
        zone: str = "",
        context: dict[str, Any] | None = None,
    ) -> list[ChainFireRecord]:
        """Evaluate an event against all enabled chains. Returns list of fired chains."""
        now = time.time()
        ctx = context or {}
        fired: list[ChainFireRecord] = []

        for chain in self._chains.values():
            if not chain.enabled:
                continue
            if chain.trigger_event != event:
                continue
            if chain.trigger_zone and zone != chain.trigger_zone:
                continue
            if confidence < chain.confidence_min:
                continue
            if (now - chain.last_fired) < chain.debounce_seconds:
                continue
            if chain.governance.requires_approval:
                logger.info("chain %s requires approval — skipping auto-fire", chain.chain_id)
                continue

            conditions_met = all(c.evaluate(ctx) for c in chain.conditions)
            if not conditions_met:
                continue

            chain.last_fired = now
            chain.fire_count += 1

            action_names = [a.action_type for a in chain.actions]
            explanation = (
                f"Event '{event}' (confidence={confidence:.0%}) matched chain '{chain.label}'. "
                f"Zone: {zone or 'any'}. "
                f"Conditions: {'all met' if chain.conditions else 'none'}. "
                f"Actions: {', '.join(action_names)}."
            )

            record = ChainFireRecord(
                chain_id=chain.chain_id,
                fired_at=now,
                event=event,
                confidence=confidence,
                frame_id=frame_id,
                actions_taken=action_names,
                explanation=explanation,
            )
            self._history.append(record)
            if len(self._history) > MAX_CHAIN_HISTORY:
                self._history = self._history[-MAX_CHAIN_HISTORY:]

            fired.append(record)
            logger.info(
                "chain fired: %s (%s → %s)",
                chain.chain_id, event, ", ".join(action_names),
            )

        return fired

    def explain_last_fire(self, chain_id: str = "") -> str:
        """Explain why the last (or specified) chain fired."""
        if chain_id:
            for record in reversed(self._history):
                if record.chain_id == chain_id:
                    return record.explanation
            return f"No fire record found for chain {chain_id}."

        if self._history:
            return self._history[-1].explanation
        return "No trigger chains have fired."

    def get_chain(self, chain_id: str) -> TriggerChain | None:
        return self._chains.get(chain_id)

    def list_chains(self) -> list[TriggerChain]:
        return list(self._chains.values())

    def get_recent_fires(self, limit: int = 10) -> list[ChainFireRecord]:
        return self._history[-limit:]

    def get_state_summary(self) -> dict[str, Any]:
        return {
            "chains": {k: v.to_dict() for k, v in self._chains.items()},
            "chain_count": len(self._chains),
            "enabled_count": sum(1 for c in self._chains.values() if c.enabled),
            "recent_fires": [r.to_dict() for r in self._history[-5:]],
        }


_chain_mgr: TriggerChainManager | None = None


def get_chain_manager() -> TriggerChainManager:
    global _chain_mgr
    if _chain_mgr is None:
        _chain_mgr = TriggerChainManager()
    return _chain_mgr
