"""LLMAdapter — wraps model_router.call_with_fallback() as a substrate Adapter.

Does NOT modify model_router internals. Pure wrapper that translates
between substrate types and the existing routing infrastructure.
"""

from __future__ import annotations

import time
from uuid import UUID, uuid4

from adapters.protocol import Adapter
from substrate.types import AdapterRequest, AdapterResponse


class LLMAdapter:
    """Wraps model_router as a substrate-compliant adapter."""

    def __init__(self) -> None:
        self.adapter_id: UUID = uuid4()
        self.adapter_type: str = "llm"
        self.name: str = "model_router"

    async def execute(self, request: AdapterRequest) -> AdapterResponse:
        """Execute an LLM request through model_router.

        Expected payload keys:
            prompt (str): The text prompt to send.
            system (str, optional): System message.
            task_type (str, optional): Routing hint (default "fast_response").
            agent_type (str, optional): Agent type for CEO routing.
            force_opus (bool, optional): Force best model.
        """
        start = time.monotonic()
        prompt = request.payload.get("prompt", "")
        system = request.payload.get("system")
        task_type = request.payload.get("task_type", "fast_response")
        agent_type = request.payload.get("agent_type")
        force_opus = request.payload.get("force_opus", False)

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=prompt,
                system=system,
                task_type=task_type,
                agent_type=agent_type,
                force_opus=force_opus,
            )
            latency = (time.monotonic() - start) * 1000

            if result and result.output and result.output.strip():
                return AdapterResponse(
                    adapter_id=self.adapter_id,
                    success=True,
                    output=result.output.strip(),
                    provider=result.provider,
                    model=result.model,
                    latency_ms=latency,
                    tokens_used=result.tokens_used,
                    cost_usd=result.cost_usd,
                )
            else:
                return AdapterResponse(
                    adapter_id=self.adapter_id,
                    success=False,
                    error="Empty response from model_router",
                    latency_ms=latency,
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return AdapterResponse(
                adapter_id=self.adapter_id,
                success=False,
                error=str(e)[:300],
                latency_ms=latency,
            )

    async def health_check(self) -> bool:
        """Check if model_router is importable."""
        try:
            from adapters.models.model_router import call_with_fallback  # noqa: F401

            return True
        except Exception:
            return False

    def capabilities(self) -> list[str]:
        """Return the list of capabilities this adapter supports."""
        return ["text_generation", "conversation", "analysis", "summarization"]
