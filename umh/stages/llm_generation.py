"""Stage 4: LLM generation — the core external I/O stage."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMGenerationStage:
    name: str = "llm_generation"
    description: str = "Call LLM via model_router.call_with_fallback"
    dependencies: tuple[str, ...] = ("prompt_enhancement", "context_assembly")
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        try:
            from umh.runtime_engine.model_router import call_with_fallback

            routing_result = call_with_fallback(
                prompt=context.message,
                system=context.system_prompt or None,
                agent_type=context.agent_type,
                task_type=context.task_type,
            )
            context.response = routing_result.output if routing_result else ""
            if routing_result:
                context.model_used = f"{routing_result.provider}/{routing_result.model}"
                context.tokens_used = {
                    "input": routing_result.input_tokens,
                    "output": routing_result.output_tokens,
                    "total": routing_result.tokens_used,
                }
                context.cost_usd = routing_result.cost_usd
                context.latency_ms = routing_result.latency_ms
            if not context.response:
                context.response = "[ExecutionSpine] No response from model chain."
        except Exception as e:
            _log.error("LLM call failed: %s", e)
            context.response = f"I encountered an error processing your request: {e}"
        return context
