"""
Operator trace — structured observability for orchestration runs.

Produces a OperatorTrace from a completed scheduler drain, summarizing:
- Ingress source and transport
- Intent ID and type
- Selected plan / variant ID
- Whether a mutated variant was chosen
- Memory block / competition / scoring result
- Terminal outcome (completed, failed, rejected)
- Key reason fields on failure

This is NOT a dashboard.  It is a structured data object that can be:
- Logged to stderr
- Formatted for Discord reply
- Written to event spine
- Serialized to JSON for audit

Design constraints:
    - Reads from RuntimeStateStore (read-only)
    - Reads from scheduler drain RunResult (read-only)
    - No side effects
    - No hot-path imports
    - Deterministic: same state always produces same trace

Usage:
    from umh.substrate.operator_trace import (
        OperatorTrace,
        build_trace_from_drain,
        format_trace_for_discord,
        format_trace_for_log,
    )

    trace = build_trace_from_drain(run_result, store)
    print(format_trace_for_log(trace))
    discord_text = format_trace_for_discord(trace)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from umh.substrate.event_scheduler import RunResult
from umh.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.operator_trace]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ── OperatorTrace ──────────────────────────────────────────────────────


@dataclass
class OperatorTrace:
    """Structured observability record for one orchestration run.

    All fields are plain types (str, int, float, dict, list) for
    JSON serialization.  No domain objects.
    """

    # Ingress
    ingress_source: str = ""
    ingress_transport: str = ""
    ingress_text: str = ""
    operator_id: str = ""

    # Intent
    intent_id: str = ""
    intent_type: str = ""
    intent_status: str = ""

    # Plan selection
    plan_id: str = ""
    variant_id: str = ""
    is_mutated_variant: bool = False

    # Scoring / memory
    plan_score: float | None = None
    plan_success_count: int = 0
    plan_failure_count: int = 0
    competition_result: str = ""
    memory_block_key: str = ""

    # Execution
    steps_total: int = 0
    steps_executed: int = 0

    # Terminal outcome
    terminal_status: str = ""
    terminal_reason: str = ""

    # Scheduler stats
    events_processed: int = 0
    mutations_applied: int = 0

    # Raw event log (event_type list for audit)
    event_types_processed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation."""
        return {
            "ingress": {
                "source": self.ingress_source,
                "transport": self.ingress_transport,
                "text": self.ingress_text[:200],
                "operator_id": self.operator_id,
            },
            "intent": {
                "intent_id": self.intent_id,
                "intent_type": self.intent_type,
                "status": self.intent_status,
            },
            "plan": {
                "plan_id": self.plan_id,
                "variant_id": self.variant_id,
                "is_mutated_variant": self.is_mutated_variant,
                "score": self.plan_score,
                "success_count": self.plan_success_count,
                "failure_count": self.plan_failure_count,
                "competition_result": self.competition_result,
            },
            "execution": {
                "steps_total": self.steps_total,
                "steps_executed": self.steps_executed,
            },
            "outcome": {
                "terminal_status": self.terminal_status,
                "terminal_reason": self.terminal_reason,
            },
            "scheduler": {
                "events_processed": self.events_processed,
                "mutations_applied": self.mutations_applied,
                "event_types": self.event_types_processed,
            },
        }


# ── Builder: extract trace from drain result + store ───────────────────


def build_trace_from_drain(
    run_result: RunResult,
    store: RuntimeStateStore,
    ingress_context: dict[str, Any] | None = None,
) -> OperatorTrace:
    """Build an OperatorTrace from a completed scheduler drain.

    Args:
        run_result: The RunResult from EventScheduler.run() or .drain().
        store: The RuntimeStateStore after drain completed.
        ingress_context: Optional ingress context dict (from IngressResult).

    Returns:
        OperatorTrace with all available fields populated.
    """
    trace = OperatorTrace(
        events_processed=run_result.events_processed,
        mutations_applied=run_result.total_mutations_applied,
    )

    # Extract event type sequence from route results if available
    if hasattr(run_result, "route_results") and run_result.route_results:
        for rr in run_result.route_results:
            if hasattr(rr, "event") and rr.event:
                trace.event_types_processed.append(rr.event.event_type)

    # Populate ingress context if provided
    ctx = ingress_context or {}
    ingress = ctx.get("ingress", {})
    trace.ingress_source = ingress.get("source", ctx.get("adapter", ""))
    trace.ingress_transport = ingress.get("transport", "")
    trace.ingress_text = ingress.get("text", "")
    trace.operator_id = ingress.get("operator_id", "")

    # Scan store for the most recent intent
    snapshot = store.snapshot()
    _populate_intent_from_snapshot(trace, snapshot)

    return trace


def _populate_intent_from_snapshot(
    trace: OperatorTrace,
    snapshot: dict[str, Any],
) -> None:
    """Extract intent/plan/scoring data from a state snapshot."""
    # Find intent keys (intent:{id})
    intent_keys = [k for k in snapshot if k.startswith("intent:")]
    if not intent_keys:
        return

    # Take the most recently created intent (by created_at or last key)
    latest_key = intent_keys[-1]
    intent_data = snapshot.get(latest_key, {})
    if not isinstance(intent_data, dict):
        return

    trace.intent_id = intent_data.get("intent_id", "")
    trace.intent_type = intent_data.get("intent_type", "")
    trace.intent_status = intent_data.get("status", "")
    trace.steps_total = intent_data.get("total_steps", 0)
    trace.steps_executed = intent_data.get("current_step", 0)

    # Plan metadata
    meta = intent_data.get("metadata", {})
    trace.plan_id = meta.get("plan_id", "")
    trace.variant_id = meta.get("variant_id", "")
    trace.is_mutated_variant = meta.get("is_mutated", False)

    # Terminal status
    status = intent_data.get("status", "")
    if status in ("completed", "failed"):
        trace.terminal_status = status
        trace.terminal_reason = meta.get("terminal_reason", "")

    # Scoring from plan memory (if present in snapshot)
    _extract_scoring(trace, snapshot)


def _extract_scoring(
    trace: OperatorTrace,
    snapshot: dict[str, Any],
) -> None:
    """Extract plan scoring/memory data from snapshot."""
    # Plan memory keys: plan_memory.{variant_id}
    for key, value in snapshot.items():
        if not key.startswith("plan_memory."):
            continue
        if not isinstance(value, dict):
            continue
        # Match to the trace's variant_id if we have one
        if trace.variant_id and trace.variant_id in key:
            trace.plan_score = value.get("score")
            trace.plan_success_count = value.get("success_count", 0)
            trace.plan_failure_count = value.get("failure_count", 0)
            trace.competition_result = value.get("competition_result", "")
            trace.memory_block_key = key
            break

    # Score meta keys: score_meta.{scope}
    for key, value in snapshot.items():
        if not key.startswith("score_meta."):
            continue
        if not isinstance(value, dict):
            continue
        if trace.plan_score is None:
            trace.plan_score = value.get("failure_penalty_weight")
        break


# ── Formatters ─────────────────────────────────────────────────────────


def format_trace_for_log(trace: OperatorTrace) -> str:
    """Format trace for stderr/log output.  One-line structured summary."""
    parts = [
        f"intent={trace.intent_id or '(none)'}",
        f"type={trace.intent_type or '(none)'}",
        f"status={trace.terminal_status or trace.intent_status or '(pending)'}",
    ]

    if trace.variant_id:
        parts.append(f"variant={trace.variant_id}")
    if trace.is_mutated_variant:
        parts.append("mutated=yes")
    if trace.plan_score is not None:
        parts.append(f"score={trace.plan_score:.3f}")

    parts.append(f"steps={trace.steps_executed}/{trace.steps_total}")
    parts.append(f"events={trace.events_processed}")

    if trace.terminal_reason:
        parts.append(f"reason={trace.terminal_reason}")

    return f"{_LOG_PREFIX} trace: {' | '.join(parts)}"


def format_trace_for_discord(trace: OperatorTrace) -> str:
    """Format trace for Discord reply.  Markdown block."""
    lines: list[str] = []

    # Header
    status_emoji = {
        "completed": "✅",
        "failed": "❌",
        "pending": "⏳",
        "active": "🔄",
    }.get(trace.terminal_status or trace.intent_status, "❓")

    lines.append(
        f"{status_emoji} **Orchestration Result** — `{trace.intent_type or 'unknown'}`"
    )
    lines.append("")

    # Intent
    if trace.intent_id:
        lines.append(f"**Intent:** `{trace.intent_id[:16]}...`")
    if trace.ingress_transport:
        lines.append(f"**Source:** {trace.ingress_transport}")

    # Plan
    if trace.variant_id:
        variant_label = trace.variant_id
        if trace.is_mutated_variant:
            variant_label += " (mutated)"
        lines.append(f"**Plan:** `{variant_label}`")

    # Scoring
    if trace.plan_score is not None:
        lines.append(
            f"**Score:** {trace.plan_score:.3f} "
            f"(✓{trace.plan_success_count} ✗{trace.plan_failure_count})"
        )

    # Execution
    if trace.steps_total > 0:
        lines.append(f"**Steps:** {trace.steps_executed}/{trace.steps_total}")

    # Outcome
    if trace.terminal_status:
        lines.append(f"**Outcome:** {trace.terminal_status}")
    if trace.terminal_reason:
        lines.append(f"**Reason:** {trace.terminal_reason}")

    # Stats
    lines.append(
        f"**Events:** {trace.events_processed} processed, "
        f"{trace.mutations_applied} mutations"
    )

    return "\n".join(lines)
