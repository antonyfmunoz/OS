"""SubstrateGateway — unified SignalEnvelope interface over the legacy gateway.

Convergence P2 bridge: accepts SignalEnvelope, delegates to
EntrepreneurOSGateway.handle(), returns ExecutionResult.

This lets transports program against the canonical substrate types
while the legacy gateway still does all the actual work (context
enrichment, agent routing, cognitive loop, quality gates).

Once feature parity is proven, the internals can be replaced
without changing the interface.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    GovernanceDecision,
    RiskClass,
    SignalEnvelope,
    SignalSource,
    TraceEventType,
    TraceRecord,
)

logger = logging.getLogger(__name__)


class SubstrateGateway:
    """Wraps EntrepreneurOSGateway with SignalEnvelope I/O.

    Thread-safe: delegates to the singleton gateway which is
    already thread-safe.
    """

    def __init__(self) -> None:
        from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway

        self._gateway = EntrepreneurOSGateway()

    def handle(self, signal: SignalEnvelope) -> ExecutionResult:
        """Route a SignalEnvelope through the full gateway lifecycle.

        Converts SignalEnvelope → dict request → gateway.handle() →
        dict result → ExecutionResult.
        """
        start = time.monotonic()
        trace = TraceRecord(signal_id=signal.id)
        trace.add_event(
            TraceEventType.SIGNAL_RECEIVED,
            f"SubstrateGateway: source={signal.source.value}",
        )

        request = self._envelope_to_request(signal)
        result_dict = self._gateway.handle(request)
        result = self._response_to_result(signal, result_dict, start, trace)

        trace.complete(success=result.is_success())
        return result

    def classify_intent(self, text: str) -> str:
        """Expose intent classification for transports that need it."""
        return self._gateway.classify_intent(text)

    def _envelope_to_request(self, signal: SignalEnvelope) -> dict[str, Any]:
        """Convert a SignalEnvelope into the dict format Gateway expects."""
        meta = signal.metadata

        request: dict[str, Any] = {
            "type": meta.get("request_type", "agent_task"),
            "prompt": signal.content,
            "venture_id": signal.venture_id,
            "username": meta.get("username", ""),
            "channel": meta.get("channel", ""),
            "session_id": meta.get("session_id"),
        }

        if meta.get("team"):
            request["team"] = meta["team"]
        if meta.get("sub_agent"):
            request["sub_agent"] = meta["sub_agent"]
        if meta.get("task_type"):
            request["task_type"] = meta["task_type"]
        if meta.get("known_person"):
            request["known_person"] = meta["known_person"]
            request["person_context"] = meta.get("person_context", "")

        return request

    def _response_to_result(
        self,
        signal: SignalEnvelope,
        response: dict[str, Any],
        start: float,
        trace: TraceRecord,
    ) -> ExecutionResult:
        """Convert a Gateway response dict into an ExecutionResult."""
        status = response.get("status", "error")
        duration_ms = (time.monotonic() - start) * 1000

        if status == "pending":
            trace.add_event(TraceEventType.GOVERNANCE_DECIDED, "Pending approval")
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.BLOCKED,
                governance_decision=GovernanceDecision.DEFER,
                output=response.get("message", "Queued for approval"),
                duration_ms=duration_ms,
            )

        if status == "error":
            error_msg = response.get("error", "Unknown error")
            trace.add_event(TraceEventType.ERROR, error_msg[:300])
            return ExecutionResult(
                signal_id=signal.id,
                trace_id=trace.id,
                outcome=ExecutionOutcome.FAILURE,
                error=error_msg,
                duration_ms=duration_ms,
            )

        output = response.get("output", "")
        trace.add_event(
            TraceEventType.EXECUTION_COMPLETED,
            f"Output: {len(output)} chars, model={response.get('model', 'unknown')}",
        )

        return ExecutionResult(
            signal_id=signal.id,
            trace_id=trace.id,
            outcome=ExecutionOutcome.SUCCESS,
            output=output,
            provider=response.get("model", ""),
            model=response.get("model", ""),
            duration_ms=duration_ms,
            governance_decision=GovernanceDecision.APPROVE,
        )


def create_signal_from_discord(
    text: str,
    channel_name: str,
    username: str,
    org_id: str,
    venture_id: str | None = None,
    session_id: str | None = None,
    team: str | None = None,
    sub_agent: str | None = None,
    guild_id: str | None = None,
    channel_id: str | None = None,
) -> SignalEnvelope:
    """Factory: build a SignalEnvelope from Discord message context.

    Used by transports/presence/handlers/intent_handler.py when
    EOS_SUBSTRATE_ROUTING=1 is set.
    """
    return SignalEnvelope(
        source=SignalSource.USER,
        content=text,
        user_id=username,
        organization_id=org_id,
        venture_id=venture_id,
        metadata={
            "channel": f"discord_{channel_name}",
            "channel_name": channel_name,
            "username": username,
            "session_id": session_id,
            "team": team,
            "sub_agent": sub_agent,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "request_type": "agent_task",
        },
    )
