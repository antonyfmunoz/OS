"""ExecutionSpine — the 8-stage execution pipeline.

Stages: interpret → recall → lookup → compose → route → execute → trace → feedback

Deterministic-first: every LLM call has a deterministic fallback.
If all providers fail, returns a heuristic response based on intent classification.

Source mapping:
- cognitive_loop.py (1,448 lines) → 8 stages
- gateway.py (2,063 lines) → intent classification, routing, fix-forever
- intent_handler.py (410 lines) → deterministic intent patterns
- capability_router.py (610 lines) → capability selection
- execution_spine.py → thin execution
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
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
# Merged from gateway.py, intent_handler.py, and cognitive_loop.py.
# Order matters: more specific patterns first, general patterns last.

_INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(schedule|book|calendar|meeting|appointment|remind)\b", re.I), "schedule"),
    (re.compile(r"\b(send|email|message|notify|alert|dm)\b", re.I), "send"),
    (re.compile(r"\b(status|progress|update|report|check|pipeline|dashboard)\b", re.I), "status"),
    (
        re.compile(r"\b(analy[sz]e|assess|evaluate|review|research|investigate|compare)\b", re.I),
        "analysis",
    ),
    (
        re.compile(
            r"\?$|^(what|how|why|when|where|who|can you|could you|is there|are there)\b", re.I
        ),
        "question",
    ),
    (
        re.compile(
            r"^(do|make|create|build|run|start|stop|deploy|fix|update|delete|add|remove|set)\b",
            re.I,
        ),
        "command",
    ),
    (
        re.compile(r"\b(hi|hello|hey|good morning|good evening|good afternoon|yo|sup)\b", re.I),
        "greeting",
    ),
]

_DETERMINISTIC_RESPONSES: dict[str, str] = {
    "greeting": "Hello! I'm here and ready to help. What would you like to work on?",
    "question": "I understand your question. Let me think about this systematically.",
    "command": "I'll process that request. Working on it now.",
    "status": "Let me check the current status for you.",
    "analysis": "I'll analyze that for you. Let me review the relevant information.",
    "schedule": "I'll help you schedule that. Let me check availability.",
    "send": "I'll prepare that communication. Let me draft it for your review.",
    "unknown": "I've received your message and I'm processing it.",
}


# ─── Fix-forever error recording ───────────────────────────────────────────

from substrate.observability.error_recorder import record_error as _record_error


# ─── Concrete execution spine ──────────────────────────────────────────────


class ConcreteExecutionSpine:
    """8-stage execution pipeline with deterministic-first + AI enhancement.

    Stages:
        0. Governance check (pre-gate)
        1. Interpret — deterministic intent classification via regex
        2. Recall — memory search for relevant context
        3. Lookup — find capable adapters in registry
        4. Compose — build prompt with identity, memory, conversation history
        5. Route — select provider (deterministic: model_router chain)
        6. Execute — call provider, fall back to heuristic response
        7. Trace — record execution trace
        8. Feedback — capture quality signal for learning loop

    Deterministic-first principle: always produce a deterministic response
    first, then try AI enhancement. If AI produces a better result, use it.
    If AI fails, the deterministic result is already available.
    """

    _SIMULATION_RISK_CLASSES = frozenset(
        {
            RiskClass.HIGH,
            RiskClass.CRITICAL,
        }
    )

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
        self._simulation = None

    def _get_simulation(self):
        if self._simulation is None:
            try:
                from substrate.reality_model.simulation import SimulationReality

                self._simulation = SimulationReality()
            except Exception:
                pass
        return self._simulation

    async def execute(
        self,
        signal: SignalEnvelope,
        context: ExecutionContext,
        verdict: GovernanceVerdict,
        *,
        trace: TraceRecord | None = None,
    ) -> ExecutionResult:
        """Execute the full 8-stage pipeline for a signal.

        When called from the router, pass the router's trace to avoid
        double-persistence. The spine populates the trace but does NOT
        persist it — the caller is responsible for persistence.
        """
        start = time.monotonic()
        owns_trace = trace is None
        if trace is None:
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
            # Stage 0b: Simulation dry-run for risky actions
            if verdict.risk_class in self._SIMULATION_RISK_CLASSES:
                sim = self._get_simulation()
                if sim:
                    try:
                        sim_result = sim.simulate(signal.content)
                        trace.add_event(
                            TraceEventType.PLAN_COMPOSED,
                            f"Simulation: safe={sim_result.safe_to_execute}, "
                            f"confidence={sim_result.overall_confidence:.2f}, "
                            f"risks={len(sim_result.diff.risk_factors)}",
                        )
                        if not sim_result.safe_to_execute:
                            trace.complete(success=True)
                            return ExecutionResult(
                                signal_id=signal.id,
                                trace_id=trace.id,
                                outcome=ExecutionOutcome.BLOCKED,
                                risk_class=verdict.risk_class,
                                governance_decision=verdict.decision,
                                output=(
                                    f"Simulation blocked execution: "
                                    f"{', '.join(sim_result.diff.risk_factors[:3])}"
                                ),
                                duration_ms=(time.monotonic() - start) * 1000,
                            )
                    except Exception as sim_err:
                        _record_error(
                            "spine.simulation",
                            str(sim_err),
                            {"signal_id": str(signal.id)},
                        )

            # Stage 0c: DeliberationCouncil for high-risk signals
            if verdict.risk_class in self._SIMULATION_RISK_CLASSES:
                try:
                    from substrate.understanding.deliberation.council import (
                        DeliberationCouncil,
                        Verdict,
                    )

                    council = DeliberationCouncil()
                    delib = council.deliberate(
                        signal.content, context={"domain": "execution"}
                    )
                    trace.add_event(
                        TraceEventType.GOVERNANCE_DECIDED,
                        f"Council: {delib.final_verdict.value} "
                        f"(confidence={delib.overall_confidence:.2f})",
                    )
                    if delib.final_verdict == Verdict.REJECT:
                        trace.complete(success=True)
                        return ExecutionResult(
                            signal_id=signal.id,
                            trace_id=trace.id,
                            outcome=ExecutionOutcome.BLOCKED,
                            risk_class=verdict.risk_class,
                            governance_decision=verdict.decision,
                            output=(
                                f"Council rejected: "
                                f"{delib.synthesis.rationale if delib.synthesis else 'no rationale'}"
                            ),
                            duration_ms=(time.monotonic() - start) * 1000,
                        )
                except Exception as council_err:
                    _record_error(
                        "spine.council",
                        str(council_err),
                        {"signal_id": str(signal.id)},
                    )

            # Stage 1: Interpret — deterministic intent classification
            intent = self._classify_intent(signal.content)
            trace.add_event(TraceEventType.SIGNAL_RECEIVED, f"Intent: {intent}")

            # Stage 2: Recall — memory search
            memories: list[Any] = []
            if self._memory:
                try:
                    query = MemoryQuery(query_text=signal.content, limit=5)
                    memories = await self._memory.recall(query)
                    trace.add_event(
                        TraceEventType.MEMORY_RECALLED,
                        f"Recalled {len(memories)} memories",
                    )
                except Exception as e:
                    _record_error("spine.recall", str(e), {"signal_id": str(signal.id)})
                    trace.add_event(
                        TraceEventType.MEMORY_RECALLED,
                        "Memory recall failed, continuing",
                    )

            # Stage 3: Lookup — find capable adapters
            adapters: list[Any] = []
            if self._registry:
                try:
                    from substrate.types import ComponentType

                    adapters = await self._registry.lookup(
                        component_type=ComponentType.ADAPTER,
                    )
                    trace.add_event(
                        TraceEventType.ADAPTER_CALLED,
                        f"Found {len(adapters)} adapters",
                    )
                except Exception:
                    pass

            # Stage 4: Compose — build prompt with full context
            memory_context = "\n".join(m.content for m in memories[:3]) if memories else ""
            prompt = self._compose_prompt(
                signal.content,
                context,
                memory_context,
                intent,
            )
            trace.add_event(
                TraceEventType.PLAN_COMPOSED,
                f"Prompt composed ({len(prompt)} chars)",
            )

            # Stage 5-6: Route + Execute — deterministic result THEN AI enhancement
            deterministic_output = _DETERMINISTIC_RESPONSES.get(
                intent,
                _DETERMINISTIC_RESPONSES["unknown"],
            )
            output = deterministic_output
            provider = "deterministic"
            model = "heuristic"

            try:
                import sys

                sys.path.insert(0, "/opt/OS")
                from adapters.models.model_router import call_with_fallback

                llm_response = await asyncio.to_thread(call_with_fallback, prompt)
                if llm_response and hasattr(llm_response, "output") and llm_response.output.strip():
                    output = llm_response.output.strip()
                    provider = llm_response.provider
                    model = llm_response.model
                elif isinstance(llm_response, str) and llm_response.strip():
                    output = llm_response.strip()
                    provider = "model_router"
                    model = "auto"

                trace.add_event(
                    TraceEventType.ADAPTER_RESPONDED,
                    f"AI response: {len(output)} chars via {provider}",
                )
            except Exception as e:
                _record_error(
                    "spine.execute",
                    str(e),
                    {"signal_id": str(signal.id), "intent": intent},
                )
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

            # Stage 8a: Knowledge gap detection → composition trigger
            try:
                from substrate.composition.knowledge_gap_trigger import KnowledgeGapTrigger

                _gap_trigger = KnowledgeGapTrigger()
                _gap_trigger.check_execution_outcome(
                    input_signal=signal.content,
                    intent=intent,
                    output=output,
                    success=True,
                    pattern_confidence=0.5,
                    skill_matched=(provider != "deterministic"),
                )
            except Exception as gap_err:
                _record_error("spine.gap_trigger", str(gap_err), {"signal_id": str(signal.id)})

            # Stage 8b: Mandatory memory writes (conversation + interaction)
            try:
                from substrate.state.context.context import load_context_from_env
                from substrate.state.memory.memory import ConversationMemory, AgentMemory

                _ctx = load_context_from_env()
                _session_id = context.session_id or str(signal.id)

                cm = ConversationMemory(_ctx)
                cm.store(
                    session_id=_session_id,
                    role="user",
                    content=signal.content[:10000],
                    channel=signal.metadata.get("channel_id", "substrate"),
                    agent=context.identity.ai_name,
                )
                cm.store(
                    session_id=_session_id,
                    role="assistant",
                    content=output[:10000],
                    channel=signal.metadata.get("channel_id", "substrate"),
                    agent=context.identity.ai_name,
                )

                mem = AgentMemory()
                from substrate.execution.runtime.agent_runtime import AgentResult

                _agent_result = AgentResult(
                    output=output[:2000],
                    model_used=model,
                    tokens_used={"input": 0, "output": 0, "total": 0},
                    skill_used=None,
                )
                mem.log(
                    agent_result=_agent_result,
                    venture_id=signal.venture_id,
                    input_summary=signal.content[:2000],
                    agent=context.identity.ai_name,
                    task_type=intent,
                )
            except Exception as mem_err:
                _record_error(
                    "spine.memory_write",
                    str(mem_err),
                    {"signal_id": str(signal.id)},
                )

            # Stage 8c: Feedback + trace persistence
            # Only persist when spine owns the trace (direct call, not from router).
            # When called from the router, the router handles persistence.
            if owns_trace:
                if self._feedback:
                    try:
                        feedback = await self._feedback.capture(trace, result)
                        await self._feedback.persist(feedback)
                    except Exception as e:
                        _record_error(
                            "spine.feedback",
                            str(e),
                            {"signal_id": str(signal.id)},
                        )
                if self._trace:
                    try:
                        await self._trace.persist(trace)
                    except Exception as e:
                        _record_error(
                            "spine.trace_persist",
                            str(e),
                            {"signal_id": str(signal.id)},
                        )

            return result

        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            _record_error(
                "spine.execute_outer",
                str(e),
                {"signal_id": str(signal.id)},
            )
            trace.add_event(TraceEventType.ERROR, str(e)[:300])
            trace.complete(success=False)
            if owns_trace and self._trace:
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
        """Deterministic intent classification via regex patterns.

        Patterns are ordered: specific intents first (schedule, send),
        general intents last (command, greeting). First match wins.
        """
        for pattern, intent in _INTENT_PATTERNS:
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
        """Build the execution prompt with full context.

        Includes: identity, personality, memory context,
        conversation history, detected intent, and user message.
        """
        parts = [
            f"You are {context.identity.ai_name}, an AI operating in "
            f"{context.identity.business_stage} stage.",
            f"Personality: {context.identity.ai_personality}",
        ]
        if memory_context:
            parts.append(f"\nRelevant context:\n{memory_context}")
        if context.conversation_history:
            recent = context.conversation_history[-5:]
            history = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')[:200]}" for m in recent
            )
            parts.append(f"\nRecent conversation:\n{history}")
        parts.append(f"\nIntent detected: {intent}")
        parts.append(f"\nUser message: {content}")
        parts.append("\nRespond helpfully and concisely.")
        return "\n".join(parts)
