"""Embodiment Runtime — natural language intent becomes governed work.

Composes Persona, IntentRuntime, CommandRuntime, AgentFleetRuntime (W3),
MetaIDERuntime (W2), CapabilityRuntime, OperationalizationRuntime, and
CompoundingEngine into a unified intent-to-action surface.

Campaign invariant: eliminates operator need for prompt engineering.
Natural language → deterministic classification → context assembly →
route to correct subsystem → persona-shaped response.

W4. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IntentType(str, Enum):
    WORK = "work"
    DEVELOPMENT = "development"
    QUERY = "query"
    COMMAND = "command"
    CONVERSATION = "conversation"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class IntentClassification:
    """Deterministic classification of operator intent."""

    intent_type: IntentType = IntentType.CONVERSATION
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    subsystem_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "confidence": self.confidence,
            "matched_keywords": list(self.matched_keywords),
            "subsystem_target": self.subsystem_target,
        }


@dataclass
class EmbodimentContext:
    """Current context assembled from fleet + IDE + recent intents."""

    fleet_active: int = 0
    ide_active_streams: int = 0
    pending_reviews: int = 0
    recent_intents: list[dict[str, Any]] = field(default_factory=list)
    capabilities_available: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fleet_active": self.fleet_active,
            "ide_active_streams": self.ide_active_streams,
            "pending_reviews": self.pending_reviews,
            "recent_intents": list(self.recent_intents),
            "capabilities_available": list(self.capabilities_available),
        }


@dataclass
class EmbodimentResponse:
    """Result of processing an intent through the embodiment layer."""

    response_id: str = field(default_factory=lambda: f"er-{uuid4().hex[:8]}")
    intent_classification: IntentClassification = field(default_factory=IntentClassification)
    subsystem_result: dict[str, Any] = field(default_factory=dict)
    shaped_response: str = ""
    lineage_id: str = ""
    processed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "intent_classification": self.intent_classification.to_dict(),
            "subsystem_result": self.subsystem_result,
            "shaped_response": self.shaped_response,
            "lineage_id": self.lineage_id,
            "processed_at": self.processed_at,
        }


@dataclass
class ProcessedIntent:
    """Historical record of a processed intent."""

    intent_id: str = field(default_factory=lambda: f"pi-{uuid4().hex[:8]}")
    text: str = ""
    classification: IntentClassification = field(default_factory=IntentClassification)
    response_id: str = ""
    processed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "text": self.text,
            "classification": self.classification.to_dict(),
            "response_id": self.response_id,
            "processed_at": self.processed_at,
        }


@dataclass
class RoutingAccuracyReport:
    """Self-assessment of deterministic routing accuracy."""

    total_processed: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    low_confidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "by_type": dict(self.by_type),
            "avg_confidence": round(self.avg_confidence, 3),
            "low_confidence_count": self.low_confidence_count,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Embodiment Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EmbodimentRuntime:
    """Natural language intent → governed work without prompt engineering.

    Composes:
      - Persona — AI identity (name, voice, style) loaded at runtime
      - IntentRuntime (Gate 4) — canonical intent preservation
      - CommandRuntime — deterministic command classification
      - AgentFleetRuntime (W3) — agent assignment + dispatch
      - MetaIDERuntime (W2) — unified development surface
      - CapabilityRuntime (Gate 5) — what the organism can do
      - OperationalizationRuntime (Gate 6) — skill/template registry
      - CompoundingEngine (Gate 9) — learning from outcomes
    """

    def __init__(
        self,
        persona: Any | None = None,
        intent_runtime: Any | None = None,
        command_runtime: Any | None = None,
        agent_fleet: Any | None = None,
        meta_ide: Any | None = None,
        capability_runtime: Any | None = None,
        operationalization_runtime: Any | None = None,
        compounding_engine: Any | None = None,
    ) -> None:
        self._persona = persona
        self._intent_runtime = intent_runtime
        self._command_runtime = command_runtime
        self._agent_fleet = agent_fleet
        self._meta_ide = meta_ide
        self._capability_runtime = capability_runtime
        self._operationalization_runtime = operationalization_runtime
        self._compounding_engine = compounding_engine

        self._history: list[ProcessedIntent] = []

    # ── Core: intent → action ────────────────────────────────────

    def process_intent(
        self, text: str, context: dict[str, Any] | None = None
    ) -> EmbodimentResponse:
        """Full pipeline: classify → assemble context → route → shape response."""
        classification = self.classify_intent(text)

        result: dict[str, Any] = {}
        lineage_id = ""

        if classification.intent_type == IntentType.WORK:
            result, lineage_id = self._route_work(text, classification)
        elif classification.intent_type == IntentType.DEVELOPMENT:
            result, lineage_id = self._route_development(text, classification)
        elif classification.intent_type == IntentType.QUERY:
            result = self._route_query(text, classification)
        elif classification.intent_type == IntentType.COMMAND:
            result = self._route_command(text, classification)
        else:
            result = {"type": "conversation", "text": text}

        shaped = self.shape_response(result, classification.intent_type)

        response = EmbodimentResponse(
            intent_classification=classification,
            subsystem_result=result,
            shaped_response=shaped,
            lineage_id=lineage_id,
        )

        record = ProcessedIntent(
            text=text,
            classification=classification,
            response_id=response.response_id,
        )
        self._history.append(record)

        return response

    # ── Classification (deterministic) ───────────────────────────

    _WORK_KEYWORDS: list[str] = [
        "assign", "dispatch", "execute", "run", "process", "handle",
        "schedule", "queue",
    ]

    _DEV_KEYWORDS: list[str] = [
        "build", "implement", "add", "create", "fix", "refactor",
        "test", "deploy", "ship", "write code", "review", "merge",
        "feature", "bug", "pr", "pull request",
    ]

    _QUERY_KEYWORDS: list[str] = [
        "what is", "what's", "how is", "show me", "status",
        "list", "get", "report", "where", "who", "which",
        "tell me", "describe",
    ]

    _COMMAND_KEYWORDS: list[str] = [
        "switch", "mode", "navigate", "open", "close", "start",
        "stop", "restart", "shutdown", "startup",
    ]

    def classify_intent(self, text: str) -> IntentClassification:
        """Deterministic-first intent classification via keyword tables."""
        lower = text.lower()

        scores: dict[IntentType, tuple[float, list[str]]] = {}
        for intent_type, keywords in [
            (IntentType.WORK, self._WORK_KEYWORDS),
            (IntentType.DEVELOPMENT, self._DEV_KEYWORDS),
            (IntentType.QUERY, self._QUERY_KEYWORDS),
            (IntentType.COMMAND, self._COMMAND_KEYWORDS),
        ]:
            matched = [kw for kw in keywords if kw in lower]
            if matched:
                score = min(1.0, len(matched) / max(3.0, len(keywords) * 0.3))
                scores[intent_type] = (score, matched)

        if not scores:
            return IntentClassification(
                intent_type=IntentType.CONVERSATION,
                confidence=0.5,
                subsystem_target="conversation",
            )

        best_type = max(scores, key=lambda t: scores[t][0])
        confidence, matched = scores[best_type]

        target_map = {
            IntentType.WORK: "agent_fleet",
            IntentType.DEVELOPMENT: "meta_ide",
            IntentType.QUERY: "read_only",
            IntentType.COMMAND: "command_runtime",
        }

        return IntentClassification(
            intent_type=best_type,
            confidence=round(confidence, 3),
            matched_keywords=matched,
            subsystem_target=target_map.get(best_type, ""),
        )

    # ── Routing ──────────────────────────────────────────────────

    def _route_work(
        self, text: str, classification: IntentClassification
    ) -> tuple[dict[str, Any], str]:
        """Route WORK intents through AgentFleetRuntime."""
        if self._agent_fleet is None:
            return {"routed": False, "reason": "agent_fleet unavailable"}, ""

        try:
            assignment = self._agent_fleet.assign(
                capabilities_required=["execution"],
                risk_class="low",
            )
            dispatch = self._agent_fleet.dispatch(
                assignment, description=text,
            )
            return {
                "routed": True,
                "subsystem": "agent_fleet",
                "dispatch_id": dispatch.dispatch_id,
                "agent_type": assignment.agent_type,
            }, dispatch.dispatch_id
        except Exception as exc:
            logger.debug("work routing failed: %s", exc)
            return {"routed": False, "error": str(exc)}, ""

    def _route_development(
        self, text: str, classification: IntentClassification
    ) -> tuple[dict[str, Any], str]:
        """Route DEVELOPMENT intents through MetaIDERuntime."""
        if self._meta_ide is None:
            return {"routed": False, "reason": "meta_ide unavailable"}, ""

        try:
            plan = self._meta_ide.plan_from_intent(text)
            return {
                "routed": True,
                "subsystem": "meta_ide",
                "plan_id": plan.plan_id,
                "tasks": len(plan.tasks),
                "risk_class": plan.risk_class,
            }, plan.plan_id
        except Exception as exc:
            logger.debug("development routing failed: %s", exc)
            return {"routed": False, "error": str(exc)}, ""

    def _route_query(
        self, text: str, classification: IntentClassification
    ) -> dict[str, Any]:
        """Route QUERY intents to read-only subsystem queries."""
        results: dict[str, Any] = {"routed": True, "subsystem": "read_only", "data": {}}

        if self._agent_fleet is not None:
            try:
                status = self._agent_fleet.fleet_status()
                results["data"]["fleet"] = {
                    "active_dispatches": status.active_dispatches,
                }
            except Exception:
                pass

        if self._meta_ide is not None:
            try:
                ide_status = self._meta_ide.ide_status()
                results["data"]["ide"] = ide_status.to_dict()
            except Exception:
                pass

        return results

    def _route_command(
        self, text: str, classification: IntentClassification
    ) -> dict[str, Any]:
        """Route COMMAND intents through CommandRuntime."""
        if self._command_runtime is None:
            return {"routed": False, "reason": "command_runtime unavailable"}

        try:
            result = self._command_runtime.classify(text)
            return {
                "routed": True,
                "subsystem": "command_runtime",
                "command_intent": result.value if hasattr(result, "value") else str(result),
            }
        except Exception as exc:
            logger.debug("command routing failed: %s", exc)
            return {"routed": False, "error": str(exc)}

    # ── Persona ──────────────────────────────────────────────────

    def persona_info(self) -> dict[str, Any]:
        """Current persona configuration."""
        if self._persona is None:
            return {"name": "UMH", "style": "tactical"}
        return {
            "name": self._persona.display_name if hasattr(self._persona, "display_name") else str(self._persona.name),
            "voice": {
                "tone": self._persona.voice_profile.tone,
                "pace": self._persona.voice_profile.pace,
                "formality": self._persona.voice_profile.formality,
            } if hasattr(self._persona, "voice_profile") else {},
            "style": self._persona.presentation_style.value if hasattr(self._persona, "presentation_style") else "tactical",
        }

    def update_persona(self, **kwargs: Any) -> dict[str, Any]:
        """Update persona attributes at runtime."""
        if self._persona is None:
            return {"error": "no persona configured"}
        for key, value in kwargs.items():
            if hasattr(self._persona, key):
                setattr(self._persona, key, value)
        return self.persona_info()

    # ── Response shaping ─────────────────────────────────────────

    _RESPONSE_TEMPLATES: dict[str, str] = {
        "work": "Work dispatched: {summary}",
        "development": "Development plan created: {summary}",
        "query": "Status: {summary}",
        "command": "Command routed: {summary}",
        "conversation": "{summary}",
    }

    def shape_response(self, result: dict[str, Any], intent_type: IntentType) -> str:
        """Shape raw subsystem result through persona voice."""
        template = self._RESPONSE_TEMPLATES.get(intent_type.value, "{summary}")

        if result.get("routed") is False:
            summary = result.get("reason", result.get("error", "unavailable"))
        elif "dispatch_id" in result:
            summary = f"dispatch {result['dispatch_id']} to {result.get('agent_type', 'agent')}"
        elif "plan_id" in result:
            summary = f"plan {result['plan_id']} ({result.get('tasks', 0)} tasks, risk={result.get('risk_class', 'low')})"
        elif "data" in result:
            data = result["data"]
            parts = []
            if "fleet" in data:
                parts.append(f"fleet: {data['fleet'].get('active_dispatches', 0)} active")
            if "ide" in data:
                parts.append(f"ide: {data['ide'].get('active_streams', 0)} streams")
            summary = "; ".join(parts) if parts else "no data"
        elif "command_intent" in result:
            summary = result["command_intent"]
        else:
            summary = str(result.get("text", "acknowledged"))

        persona_name = "UMH"
        if self._persona and hasattr(self._persona, "display_name"):
            persona_name = self._persona.display_name or "UMH"

        return template.format(summary=summary)

    # ── History ──────────────────────────────────────────────────

    def intent_history(self, limit: int = 50) -> list[ProcessedIntent]:
        """Recent processed intents."""
        return list(reversed(self._history[-limit:]))

    # ── Accuracy ─────────────────────────────────────────────────

    def routing_accuracy(self) -> RoutingAccuracyReport:
        """Self-assessment of deterministic routing quality."""
        if not self._history:
            return RoutingAccuracyReport()

        by_type: dict[str, int] = {}
        total_conf = 0.0
        low_conf = 0

        for h in self._history:
            t = h.classification.intent_type.value
            by_type[t] = by_type.get(t, 0) + 1
            total_conf += h.classification.confidence
            if h.classification.confidence < 0.5:
                low_conf += 1

        return RoutingAccuracyReport(
            total_processed=len(self._history),
            by_type=by_type,
            avg_confidence=total_conf / len(self._history),
            low_confidence_count=low_conf,
        )

    # ── Context ──────────────────────────────────────────────────

    def current_context(self) -> EmbodimentContext:
        """Assemble current context from fleet + IDE + recent intents."""
        fleet_active = 0
        if self._agent_fleet is not None:
            try:
                status = self._agent_fleet.fleet_status()
                fleet_active = status.active_dispatches
            except Exception:
                pass

        ide_streams = 0
        pending_reviews = 0
        if self._meta_ide is not None:
            try:
                ide_s = self._meta_ide.ide_status()
                ide_streams = ide_s.active_streams
                pending_reviews = ide_s.pending_reviews
            except Exception:
                pass

        caps: list[str] = []
        if self._capability_runtime is not None:
            try:
                all_caps = self._capability_runtime.query()
                caps = [c.name if hasattr(c, "name") else str(c) for c in all_caps[:20]]
            except Exception:
                pass

        recent = [h.to_dict() for h in self._history[-5:]]

        return EmbodimentContext(
            fleet_active=fleet_active,
            ide_active_streams=ide_streams,
            pending_reviews=pending_reviews,
            recent_intents=recent,
            capabilities_available=caps,
        )
