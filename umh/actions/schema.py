"""ActionSchema — universal execution contract for UMH.

Normalizes domain-specific ActionPlans into a single ExecutableAction
shape that downstream routing/execution can consume without knowing
the originating domain.

DecisionOutput → DomainAdapter/ActionPlan → ActionSchema → Execution Router

Pure functions only. No side effects. No API calls. No I/O.
Deterministic: same input always produces the same output.

Usage::

    from umh.actions.schema import to_executable_action, to_action_batch

    result = to_executable_action(action_plan, domain="business", confidence=0.8)
    action = result.executable_action
    batch = to_action_batch((action,), domain="business")
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum


# ─── Action types ────────────────────────────────────────────────


class ActionType(str, Enum):
    API_CALL = "API_CALL"
    MESSAGE = "MESSAGE"
    TASK = "TASK"
    HUMAN_INSTRUCTION = "HUMAN_INSTRUCTION"
    NO_OP = "NO_OP"


# ─── Classification rules ───────────────────────────────────────
# Longest-first keyword matching, same pattern as intent_compiler.

_MESSAGE_KEYWORDS: tuple[str, ...] = (
    "send message",
    "send email",
    "send dm",
    "notify team",
    "notify",
    "message",
    "email",
    "send",
    "dm",
)

_API_CALL_KEYWORDS: tuple[str, ...] = (
    "update crm",
    "create record",
    "sync data",
    "call api",
    "post to",
    "update",
    "sync",
    "post",
)

_HUMAN_INSTRUCTION_KEYWORDS: tuple[str, ...] = (
    "manually review",
    "talk to",
    "reflect on",
    "discuss",
    "decide",
    "reflect",
    "journal",
)

_TASK_KEYWORDS: tuple[str, ...] = (
    "create task",
    "follow up",
    "analyze",
    "review",
    "draft",
    "plan",
    "test",
)


def classify_action_type(instruction: str, domain: str = "") -> ActionType:
    """Classify an action instruction into a universal ActionType.

    Uses deterministic keyword matching with longest-match priority.
    Falls back to TASK for recognized-but-ambiguous instructions,
    NO_OP for empty/unrecognizable ones.
    """
    if not instruction or not instruction.strip():
        return ActionType.NO_OP

    text = instruction.lower().strip()

    for kw in _MESSAGE_KEYWORDS:
        if kw in text:
            return ActionType.MESSAGE

    for kw in _HUMAN_INSTRUCTION_KEYWORDS:
        if kw in text:
            return ActionType.HUMAN_INSTRUCTION

    # TASK before API_CALL: "post" in API_CALL would match nouns like "posts"
    for kw in _TASK_KEYWORDS:
        if kw in text:
            return ActionType.TASK

    for kw in _API_CALL_KEYWORDS:
        if kw in text:
            return ActionType.API_CALL

    # Fallback: if there's text but no keyword match, classify as TASK
    return ActionType.TASK


# ─── Target extraction ──────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

_PLATFORM_KEYWORDS: tuple[str, ...] = (
    "instagram",
    "twitter",
    "linkedin",
    "youtube",
    "tiktok",
    "discord",
    "slack",
    "telegram",
    "facebook",
    "crm",
    "notion",
    "calendar",
)

_ENTITY_KEYWORDS: tuple[str, ...] = (
    "team",
    "customer",
    "lead",
    "prospect",
    "client",
    "audience",
    "subscriber",
)


def _extract_target(instruction: str) -> str | None:
    """Extract the most specific target from an instruction string."""
    if not instruction:
        return None

    text = instruction.lower()

    email = _EMAIL_RE.search(instruction)
    if email:
        return email.group(0)

    for platform in _PLATFORM_KEYWORDS:
        if platform in text:
            return platform

    for entity in _ENTITY_KEYWORDS:
        if entity in text:
            return entity

    if "self" in text.split():
        return "self"

    return None


# ─── Data models ────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutableAction:
    """Canonical execution contract for downstream routing."""

    action_id: str
    action_type: str
    action_name: str
    target: str | None
    intent: str
    payload: dict[str, float | int | str | bool | None]
    constraints: dict[str, float | int | str | bool | None]
    priority: float
    confidence: float
    domain: str
    trace_id: str | None
    explanation: str | None

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "action_name": self.action_name,
            "target": self.target,
            "intent": self.intent,
            "payload": dict(self.payload),
            "constraints": dict(self.constraints),
            "priority": round(self.priority, 4),
            "confidence": round(self.confidence, 4),
            "domain": self.domain,
            "trace_id": self.trace_id,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExecutableAction:
        return cls(
            action_id=d["action_id"],
            action_type=d["action_type"],
            action_name=d["action_name"],
            target=d.get("target"),
            intent=d["intent"],
            payload=d.get("payload", {}),
            constraints=d.get("constraints", {}),
            priority=d.get("priority", 0.5),
            confidence=d.get("confidence", 0.5),
            domain=d.get("domain", ""),
            trace_id=d.get("trace_id"),
            explanation=d.get("explanation"),
        )


@dataclass(frozen=True)
class ActionBatch:
    """Groups multiple ExecutableActions for downstream routing."""

    actions: tuple[ExecutableAction, ...]
    batch_id: str
    domain: str
    count: int

    def to_dict(self) -> dict:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "batch_id": self.batch_id,
            "domain": self.domain,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ActionBatch:
        actions = tuple(ExecutableAction.from_dict(a) for a in d.get("actions", []))
        return cls(
            actions=actions,
            batch_id=d["batch_id"],
            domain=d.get("domain", ""),
            count=d.get("count", len(actions)),
        )


@dataclass(frozen=True)
class ActionNormalizationResult:
    """Captures the result of normalizing an ActionStep into an ExecutableAction."""

    executable_action: ExecutableAction
    warnings: tuple[str, ...]
    normalized_from: str

    def to_dict(self) -> dict:
        return {
            "executable_action": self.executable_action.to_dict(),
            "warnings": list(self.warnings),
            "normalized_from": self.normalized_from,
        }


# ─── Stable action ID ──────────────────────────────────────────


def _compute_action_id(
    action_type: str,
    action_name: str,
    target: str | None,
    payload: dict,
    constraints: dict,
    domain: str,
) -> str:
    """Deterministic action ID from canonical fields.

    Same normalized action always produces the same ID.
    Does not depend on dict insertion order.
    """
    canonical = json.dumps(
        {
            "action_type": action_type,
            "action_name": action_name,
            "target": target,
            "payload": sorted(payload.items()) if payload else [],
            "constraints": sorted(constraints.items()) if constraints else [],
            "domain": domain,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ─── Action name normalization ──────────────────────────────────


def _normalize_action_name(raw: str) -> str:
    """Normalize an action name to lowercase_snake_case."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", raw.strip().lower())
    parts = cleaned.split()
    if not parts:
        return "unknown_action"
    return "_".join(parts)[:80]


# ─── Intent template ────────────────────────────────────────────


def _build_intent(
    action_name: str, action_type: str, domain: str, target: str | None
) -> str:
    """Build a deterministic semantic intent string."""
    target_phrase = f" targeting {target}" if target else ""
    return f"{action_type.lower()}: {action_name.replace('_', ' ')}{target_phrase} in {domain} domain"


# ─── Payload / constraint extraction ────────────────────────────

_CONSTRAINT_KEYS: frozenset[str] = frozenset(
    {
        "max_retries",
        "review_required",
        "safe_mode",
        "budget_limit",
        "channel",
        "deadline",
        "approval_required",
        "risk_threshold",
    }
)


def _extract_payload_and_constraints(
    step: object,
    action_plan: object,
) -> tuple[dict, dict]:
    """Extract structured payload and constraints from action step + plan context."""
    payload: dict[str, float | int | str | bool | None] = {}
    constraints: dict[str, float | int | str | bool | None] = {}

    instruction = getattr(step, "instruction", "")
    category = getattr(step, "category", "")
    source_keyword = getattr(step, "source_keyword", "")

    payload["instruction"] = instruction
    payload["category"] = category
    payload["source_keyword"] = source_keyword

    plan_confidence = getattr(action_plan, "confidence", None)
    if plan_confidence is not None:
        payload["plan_confidence"] = round(float(plan_confidence), 4)

    plan_risk = getattr(action_plan, "risk_score", None)
    if plan_risk is not None:
        payload["plan_risk_score"] = round(float(plan_risk), 4)

    # Constraints from step metadata if present
    step_dict = {}
    if hasattr(step, "to_dict"):
        step_dict = step.to_dict()

    for key in _CONSTRAINT_KEYS:
        val = step_dict.get(key)
        if val is not None:
            constraints[key] = val

    return payload, constraints


# ─── Core normalization ─────────────────────────────────────────


def to_executable_action(
    action_plan: object,
    domain: str,
    confidence: float,
    trace_id: str | None = None,
    step_index: int = 0,
) -> ActionNormalizationResult:
    """Translate one ActionPlan step into an ExecutableAction.

    Normalizes action name, classifies type, extracts target/payload/constraints,
    and generates a stable action_id.

    When step_index is provided, normalizes that specific step. Default is
    the first (highest priority) step.

    Returns ActionNormalizationResult with any warnings about ambiguity.
    """
    warnings: list[str] = []
    steps = getattr(action_plan, "steps", ())

    if not steps:
        return _build_no_op(
            domain=domain,
            confidence=confidence,
            trace_id=trace_id,
            reason="empty action plan — no steps to normalize",
        )

    if step_index >= len(steps):
        return _build_no_op(
            domain=domain,
            confidence=confidence,
            trace_id=trace_id,
            reason=f"step_index {step_index} out of range ({len(steps)} steps)",
        )

    step = steps[step_index]
    instruction = getattr(step, "instruction", "")
    source_keyword = getattr(step, "source_keyword", "")

    if not instruction.strip():
        return _build_no_op(
            domain=domain,
            confidence=confidence,
            trace_id=trace_id,
            reason="empty instruction in action step",
        )

    # Normalize
    raw_name = source_keyword if source_keyword else instruction
    action_name = _normalize_action_name(raw_name)
    action_type = classify_action_type(instruction, domain)
    target = _extract_target(instruction)

    if target is None:
        warnings.append(f"no target extracted from: {instruction[:60]}")

    if action_type == ActionType.TASK and source_keyword:
        # Check if this was a fallback classification
        text_lower = instruction.lower()
        matched_any = False
        for kw_list in (
            _MESSAGE_KEYWORDS,
            _API_CALL_KEYWORDS,
            _HUMAN_INSTRUCTION_KEYWORDS,
            _TASK_KEYWORDS,
        ):
            for kw in kw_list:
                if kw in text_lower:
                    matched_any = True
                    break
            if matched_any:
                break
        if not matched_any:
            warnings.append(f"unknown action mapped to TASK fallback: {source_keyword}")

    payload, constraints = _extract_payload_and_constraints(step, action_plan)

    # Priority: use step priority normalized to [0,1], default 0.5
    raw_priority = getattr(step, "priority", 5)
    priority = max(0.0, min(1.0, 1.0 - (raw_priority - 1) / 9.0))

    confidence = max(0.0, min(1.0, float(confidence)))

    action_id = _compute_action_id(
        action_type=action_type.value,
        action_name=action_name,
        target=target,
        payload=payload,
        constraints=constraints,
        domain=domain,
    )

    raw_action = getattr(action_plan, "raw_action", "")
    explanation = f"Normalized from '{source_keyword}' in {domain} domain."
    if raw_action:
        explanation += f" Original: {raw_action[:100]}"

    action = ExecutableAction(
        action_id=action_id,
        action_type=action_type.value,
        action_name=action_name,
        target=target,
        intent=_build_intent(action_name, action_type.value, domain, target),
        payload=payload,
        constraints=constraints,
        priority=priority,
        confidence=confidence,
        domain=domain,
        trace_id=trace_id,
        explanation=explanation,
    )

    return ActionNormalizationResult(
        executable_action=action,
        warnings=tuple(warnings),
        normalized_from=source_keyword or instruction,
    )


def _build_no_op(
    domain: str,
    confidence: float,
    trace_id: str | None,
    reason: str,
) -> ActionNormalizationResult:
    """Construct a safe NO_OP ExecutableAction."""
    action_id = _compute_action_id(
        action_type=ActionType.NO_OP.value,
        action_name="no_op",
        target=None,
        payload={},
        constraints={},
        domain=domain,
    )

    action = ExecutableAction(
        action_id=action_id,
        action_type=ActionType.NO_OP.value,
        action_name="no_op",
        target=None,
        intent=f"no_op: {reason}",
        payload={},
        constraints={},
        priority=0.0,
        confidence=max(0.0, min(1.0, float(confidence))),
        domain=domain,
        trace_id=trace_id,
        explanation=reason,
    )

    return ActionNormalizationResult(
        executable_action=action,
        warnings=(reason,),
        normalized_from="no_op",
    )


# ─── Batch support ──────────────────────────────────────────────


def to_action_batch(
    actions: tuple[ExecutableAction, ...],
    domain: str,
) -> ActionBatch:
    """Construct a deterministic ActionBatch from a tuple of ExecutableActions."""
    action_ids = tuple(a.action_id for a in actions)
    batch_canonical = json.dumps(
        {"action_ids": action_ids, "domain": domain},
        sort_keys=True,
        separators=(",", ":"),
    )
    batch_id = hashlib.sha256(batch_canonical.encode("utf-8")).hexdigest()[:16]

    return ActionBatch(
        actions=actions,
        batch_id=batch_id,
        domain=domain,
        count=len(actions),
    )


# ─── Multi-step plan normalization ──────────────────────────────


def normalize_full_plan(
    action_plan: object,
    domain: str,
    confidence: float,
    trace_id: str | None = None,
) -> tuple[ActionNormalizationResult, ...]:
    """Normalize every step in an ActionPlan into ExecutableActions."""
    steps = getattr(action_plan, "steps", ())
    if not steps:
        return (
            _build_no_op(
                domain=domain,
                confidence=confidence,
                trace_id=trace_id,
                reason="empty action plan — no steps to normalize",
            ),
        )

    results: list[ActionNormalizationResult] = []
    for i in range(len(steps)):
        results.append(
            to_executable_action(
                action_plan=action_plan,
                domain=domain,
                confidence=confidence,
                trace_id=trace_id,
                step_index=i,
            )
        )
    return tuple(results)


if __name__ == "__main__":
    print("action_schema import OK")
