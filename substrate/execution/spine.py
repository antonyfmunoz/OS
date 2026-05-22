"""ExecutionSpine — the 8-stage execution pipeline.

Stages: interpret → recall → lookup → compose → route → execute → trace → feedback

Deterministic-first: every LLM call has a deterministic fallback.
If all providers fail, returns a heuristic response based on intent classification.

Source mapping:
- cognitive_loop.py (1,448 lines) → 8 stages
- execution_spine.py → thin execution
- pipeline.py → 10-stage pipeline
"""

from __future__ import annotations

import re
import time
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from substrate.types import (
    ExecutionContext,
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    GovernanceVerdict,
    MemoryQuery,
    RiskClass,
    SignalEnvelope,
    TraceEventType,
    TraceRecord,
)


@runtime_checkable
class ExecutionSpine(Protocol):
    """Protocol for the execution pipeline."""

    async def execute(
        self,
        signal: SignalEnvelope,
        context: ExecutionContext,
        verdict: GovernanceVerdict,
    ) -> ExecutionResult: ...


# ─── Deterministic intent classification ────────────────────────────────────

_INTENT_PATTERNS: dict[str, re.Pattern] = {
    "greeting": re.compile(r"\b(hi|hello|hey|good morning|good evening)\b", re.I),
    "question": re.compile(r"\?$|^(what|how|why|when|where|who|can you)\b", re.I),
    "command": re.compile(r"^(do|make|create|build|run|start|stop|send|update|delete)\b", re.I),
    "status": re.compile(r"\b(status|progress|update|report)\b", re.I),
    "analysis": re.compile(r"\b(analyze|assess|evaluate|review|check)\b", re.I),
}

_DETERMINISTIC_RESPONSES: dict[str, str] = {
    "greeting": "Hello! I'm here and ready to help. What would you like to work on?",
    "question": "I understand your question. Let me think about this systematically.",
    "command": "I'll process that request. Working on it now.",
    "status": "Let me check the current status for you.",
    "analysis": "I'll analyze that for you. Let me review the relevant information.",
    "unknown": "I've received your message and I'm processing it.",
}


class ConcreteExecutionSpine:
    """8-stage execution pipeline with deterministic-first fallback.

    Stages:
        0. Governance check (pre-gate)
        1. Interpret — deterministic intent classification via regex
        2. Recall — memory search for relevant context
        3. Lookup — find capable adapters in registry
        4. Compose — build prompt with assembled context
        5. Route — select provider (deterministic: model_router chain)
        6. Execute — call provider, fall back to heuristic response
        7. Trace — record execution trace
        8. Feedback — capture quality signal for learning loop
    """

    def __init__(
        self,
        memory: Any = None,
        registry: Any = None,
        trace_recorder: Any = None,
        feedback_capture: Any = None,
    ) -> None:
        self._memory = memory
        self._registry = registry
        self._trace = trace_recorder
        self._feedback = feedback_capture

    async def execute(
        self,
        signal: SignalEnvelope,
        context: ExecutionContext,
        verdict: GovernanceVerdict,
    ) -> ExecutionResult:
        """Execute the full 8-stage pipeline for a signal."""
        start = time.monotonic()
        trace = TraceRecord(signal_id=signal.id)

        # Stage 0: Governance gate
        if not verdict.is_executable():
            trace.add_event(
                TraceEventType.GOVERNANCE_DECIDED,
                f"Blocked: {verdict.rationale}",
            )
            trace.complete(success=True)
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.BLOCKED,
                risk_class=verdict.risk_class,
                governance_decision=verdict.decision,
                output=verdict.rationale,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            # Stage 1: Interpret — deterministic intent classification
            intent = self._classify_intent(signal.content)
            trace.add_event(TraceEventType.SIGNAL_RECEIVED, f"Intent: {intent}")

            # Stage 2: Recall — memory search
            memories = []
            if self._memory:
                try:
                    query = MemoryQuery(query_text=signal.content, limit=5)
                    memories = await self._memory.recall(query)
                    trace.add_event(
                        TraceEventType.MEMORY_RECALLED,
                        f"Recalled {len(memories)} memories",
                    )
                except Exception:
                    trace.add_event(
                        TraceEventType.MEMORY_RECALLED,
                        "Memory recall failed, continuing",
                    )

            # Stage 3: Lookup — find capable adapters
            adapters = []
            if self._registry:
                try:
                    from substrate.types import ComponentType

                    adapters = await self._registry.lookup(component_type=ComponentType.ADAPTER)
                    trace.add_event(
                        TraceEventType.ADAPTER_CALLED,
                        f"Found {len(adapters)} adapters",
                    )
                except Exception:
                    pass

            # Stage 4: Compose — build prompt with context
            memory_context = "\n".join(m.content for m in memories[:3]) if memories else ""
            prompt = self._compose_prompt(signal.content, context, memory_context, intent)
            trace.add_event(
                TraceEventType.PLAN_COMPOSED,
                f"Prompt composed ({len(prompt)} chars)",
            )

            # Stage 5-6: Route + Execute — try LLM, fall back to deterministic
            output = ""
            provider = "deterministic"
            model = "heuristic"

            try:
                import sys

                sys.path.insert(0, "/opt/OS")
                from adapters.models.model_router import call_with_fallback

                llm_response = call_with_fallback(prompt)
                if llm_response and llm_response.strip():
                    output = llm_response.strip()
                    provider = "model_router"
                    model = "auto"
                    trace.add_event(
                        TraceEventType.ADAPTER_RESPONDED,
                        f"LLM response: {len(output)} chars",
                    )
                else:
                    raise ValueError("Empty LLM response")
            except Exception:
                output = _DETERMINISTIC_RESPONSES.get(intent, _DETERMINISTIC_RESPONSES["unknown"])
                trace.add_event(
                    TraceEventType.ADAPTER_RESPONDED,
                    f"Deterministic fallback: {intent}",
                )

            # Stage 7: Trace
            duration = (time.monotonic() - start) * 1000
            trace.add_event(
                TraceEventType.EXECUTION_COMPLETED,
                f"Duration: {duration:.0f}ms",
            )
            trace.complete(success=True)

            result = ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.SUCCESS,
                output=output,
                provider=provider,
                model=model,
                duration_ms=duration,
                risk_class=verdict.risk_class,
                governance_decision=verdict.decision,
            )

            # Stage 8: Feedback
            if self._feedback:
                try:
                    feedback = await self._feedback.capture(trace, result)
                    await self._feedback.persist(feedback)
                    trace.add_event(TraceEventType.FEEDBACK_CAPTURED, "Feedback captured")
                except Exception:
                    pass

            # Persist trace
            if self._trace:
                try:
                    await self._trace.persist(trace)
                except Exception:
                    pass

            return result

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            trace.add_event(TraceEventType.ERROR, str(e)[:300])
            trace.complete(success=False)
            if self._trace:
                try:
                    await self._trace.persist(trace)
                except Exception:
                    pass
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.FAILURE,
                error=str(e)[:300],
                duration_ms=duration,
            )

    def _classify_intent(self, content: str) -> str:
        """Deterministic intent classification via regex patterns."""
        for intent, pattern in _INTENT_PATTERNS.items():
            if pattern.search(content):
                return intent
        return "unknown"

    def _compose_prompt(
        self,
        content: str,
        context: ExecutionContext,
        memory_context: str,
        intent: str,
    ) -> str:
        """Build the execution prompt with full context."""
        parts = [
            f"You are {context.identity.ai_name}, an AI operating in "
            f"{context.identity.business_stage} stage.",
            f"Personality: {context.identity.ai_personality}",
        ]
        if memory_context:
            parts.append(f"\nRelevant context:\n{memory_context}")
        parts.append(f"\nIntent detected: {intent}")
        parts.append(f"\nUser message: {content}")
        parts.append("\nRespond helpfully and concisely.")
        return "\n".join(parts)
