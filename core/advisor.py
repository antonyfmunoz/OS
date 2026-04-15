"""
advisor.py — Conditional intelligence layer for the EOS AI OS.

The Advisor Strategy introduces two model roles:

  Executor  — fast/cheap model, default for all operations
  Advisor   — high-capability model, invoked only on escalation

The advisor NEVER executes actions or side effects. It only returns
structured guidance (approve / modify / reject) that the caller
merges into the executor's result.

Escalation is governed by deterministic rules evaluated by
``needs_advisor()``. The rules cover:

  1. Confidence-based   — low-confidence or ambiguous executor output
  2. Graph-based        — operations on high-centrality nodes
  3. Risk-based         — HIGH or CRITICAL actions
  4. Failure-based      — retries triggered, previous step failed
  5. Complexity-based   — multi-step reasoning, planning-heavy tasks
  6. Explicit triggers  — step/task marked requires_advisor

Performance safeguards:
  - Max advisor calls per workflow (default 5)
  - Per-call timeout (default 30s)
  - Rate limiting (max 10 calls per 60s window)
  - Graceful fallback if advisor fails (use executor result as-is)

This module is import-safe: it depends only on core.capability (pure)
and standard library. Heavy imports (harness, router) are lazy.

Usage:
    from core.advisor import needs_advisor, call_advisor, AdvisorResult

    if needs_advisor(executor_output, context, metadata):
        advice = call_advisor(task, executor_output, context, metadata)
        if advice.decision == "modify":
            final = advice.suggested_changes
        elif advice.decision == "reject":
            raise WorkflowError(advice.reasoning)
"""

from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.capability import RiskTier, coerce_risk  # noqa: E402


DATA_DIR = Path(_REPO_ROOT) / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ADVISOR_LOG = DATA_DIR / "advisor_log.jsonl"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class AdvisorDecision(str, Enum):
    """What the advisor recommends."""

    APPROVE = "approve"  # executor result is good, use as-is
    MODIFY = "modify"  # refine executor result with suggested_changes
    REJECT = "reject"  # halt or reroute workflow


@dataclass
class AdvisorResult:
    """Structured output from an advisor call.

    decision:          approve / modify / reject
    reasoning:         why the advisor made this decision
    suggested_changes: concrete refinements (only meaningful for MODIFY)
    modifications:     list form of suggested_changes (canonical schema)
    confidence:        0.0–1.0 advisor's self-assessed confidence
    advisor_model:     which model served the advisor call
    latency_ms:        wall-clock time for the advisor call
    escalation_reason: which rule triggered the escalation
    """

    decision: str = AdvisorDecision.APPROVE.value
    reasoning: str = ""
    suggested_changes: str = ""
    modifications: list[str] = field(default_factory=list)
    confidence: float = 1.0
    advisor_model: str = ""
    latency_ms: int = 0
    escalation_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_canonical(self) -> dict[str, Any]:
        """Return the canonical schema: {decision, reason, modifications}.

        This is the shape that callers and the optimizer expect. Always
        returns valid structured output regardless of LLM response quality.
        """
        mods = list(self.modifications)
        if not mods and self.suggested_changes:
            mods = [line.strip() for line in self.suggested_changes.split("\n")
                    if line.strip()]
        return {
            "decision": self.decision,
            "reason": self.reasoning,
            "modifications": mods,
        }


class EscalationReason(str, Enum):
    """Why the advisor was triggered."""

    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_OUTPUT = "ambiguous_output"
    INCOMPLETE_OUTPUT = "incomplete_output"
    HIGH_CENTRALITY = "high_centrality"
    LARGE_DEPENDENCY_IMPACT = "large_dependency_impact"
    HIGH_RISK_ACTION = "high_risk_action"
    CRITICAL_RISK_ACTION = "critical_risk_action"
    RETRY_TRIGGERED = "retry_triggered"
    PREVIOUS_STEP_FAILED = "previous_step_failed"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    PLANNING_TASK = "planning_task"
    EXPLICIT_REQUIRES_ADVISOR = "explicit_requires_advisor"
    ADVISOR_ON_FAILURE = "advisor_on_failure"
    ADVISOR_ON_RISK = "advisor_on_risk"


# ---------------------------------------------------------------------------
# Escalation config — tunable thresholds
# ---------------------------------------------------------------------------


@dataclass
class EscalationConfig:
    """All tunable parameters for escalation decisions."""

    # Confidence thresholds
    min_confidence: float = 0.40
    ambiguity_markers: tuple[str, ...] = (
        "I'm not sure",
        "I think",
        "maybe",
        "possibly",
        "it depends",
        "unclear",
        "I don't know",
        "hard to say",
        "not certain",
    )
    min_output_length: int = 20  # outputs shorter than this are suspect

    # Graph thresholds
    critical_hub_rank: int = 20
    max_safe_dependents: int = 5

    # Risk thresholds (actions at or above this trigger advisor)
    min_risk_for_advisor: RiskTier = RiskTier.HIGH

    # Complexity markers in task descriptions
    complexity_markers: tuple[str, ...] = (
        "plan",
        "architect",
        "design",
        "strategy",
        "multi-step",
        "coordinate",
        "migrate",
        "refactor",
    )

    # Performance safeguards
    max_advisor_calls_per_workflow: int = 5
    advisor_timeout_sec: float = 30.0
    rate_limit_max_calls: int = 10
    rate_limit_window_sec: float = 60.0


DEFAULT_CONFIG = EscalationConfig()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self, max_calls: int, window_sec: float) -> None:
        self._max = max_calls
        self._window = window_sec
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            # Evict old entries
            while self._calls and (now - self._calls[0]) > self._window:
                self._calls.popleft()
            if len(self._calls) >= self._max:
                return False
            self._calls.append(now)
            return True

    def count(self) -> int:
        now = time.monotonic()
        with self._lock:
            while self._calls and (now - self._calls[0]) > self._window:
                self._calls.popleft()
            return len(self._calls)


_RATE_LIMITER = _RateLimiter(
    DEFAULT_CONFIG.rate_limit_max_calls,
    DEFAULT_CONFIG.rate_limit_window_sec,
)


# ---------------------------------------------------------------------------
# Workflow-level call counter
# ---------------------------------------------------------------------------


_workflow_call_counts: dict[str, int] = {}
_wf_lock = threading.Lock()


def _check_workflow_budget(workflow_id: str | None, config: EscalationConfig) -> bool:
    """Return True if this workflow still has advisor budget."""
    if not workflow_id:
        return True
    with _wf_lock:
        count = _workflow_call_counts.get(workflow_id, 0)
        return count < config.max_advisor_calls_per_workflow


def _increment_workflow_count(workflow_id: str | None) -> None:
    if not workflow_id:
        return
    with _wf_lock:
        _workflow_call_counts[workflow_id] = (
            _workflow_call_counts.get(workflow_id, 0) + 1
        )


def reset_workflow_count(workflow_id: str) -> None:
    """Call when a workflow completes to free its budget."""
    with _wf_lock:
        _workflow_call_counts.pop(workflow_id, None)


# ---------------------------------------------------------------------------
# needs_advisor() — the core escalation function
# ---------------------------------------------------------------------------


def needs_advisor(
    result: Any,
    context: dict[str, Any],
    metadata: dict[str, Any],
    *,
    config: EscalationConfig | None = None,
) -> tuple[bool, str]:
    """Evaluate whether an executor result should be escalated to the advisor.

    Args:
        result:   the executor's output (string or HarnessResult-like)
        context:  dict with optional keys: graph_hits, step_type, task_description,
                  workflow_id, previous_step_failed, attempts, centrality_rank,
                  dependent_count, is_critical_hub
        metadata: dict with optional keys: risk, requires_advisor,
                  advisor_on_failure, advisor_on_risk, task_type

    Returns:
        (should_escalate, reason) tuple
    """
    cfg = config or DEFAULT_CONFIG

    # 0. Explicit trigger — always wins
    if metadata.get("requires_advisor"):
        return (True, EscalationReason.EXPLICIT_REQUIRES_ADVISOR.value)

    # 1. Failure-based: advisor_on_failure + previous step failed
    if metadata.get("advisor_on_failure") and context.get("previous_step_failed"):
        return (True, EscalationReason.ADVISOR_ON_FAILURE.value)

    # 2. Failure-based: retry triggered
    attempts = context.get("attempts", 0)
    if attempts >= 2:
        return (True, EscalationReason.RETRY_TRIGGERED.value)

    # 3. Previous step failed
    if context.get("previous_step_failed"):
        return (True, EscalationReason.PREVIOUS_STEP_FAILED.value)

    # 4. Risk-based
    risk = coerce_risk(metadata.get("risk"))
    if metadata.get("advisor_on_risk") and risk.rank >= RiskTier.MEDIUM.rank:
        return (True, EscalationReason.ADVISOR_ON_RISK.value)
    if risk.rank >= RiskTier.CRITICAL.rank:
        return (True, EscalationReason.CRITICAL_RISK_ACTION.value)
    if risk.rank >= cfg.min_risk_for_advisor.rank:
        return (True, EscalationReason.HIGH_RISK_ACTION.value)

    # 5. Graph-based
    if context.get("is_critical_hub"):
        return (True, EscalationReason.HIGH_CENTRALITY.value)
    dep_count = context.get("dependent_count", 0)
    if dep_count > cfg.max_safe_dependents:
        return (True, EscalationReason.LARGE_DEPENDENCY_IMPACT.value)

    # 6. Confidence-based (analyze the executor output)
    output_text = _extract_output_text(result)

    if len(output_text) < cfg.min_output_length and output_text.strip():
        return (True, EscalationReason.INCOMPLETE_OUTPUT.value)

    lowered = output_text.lower()
    for marker in cfg.ambiguity_markers:
        if marker.lower() in lowered:
            return (True, EscalationReason.AMBIGUOUS_OUTPUT.value)

    # 7. Complexity-based
    task_desc = (
        metadata.get("task_description", "")
        or context.get("task_description", "")
        or ""
    ).lower()
    task_type = str(metadata.get("task_type", "")).lower()

    if task_type in ("strategic", "plan", "coordinate"):
        return (True, EscalationReason.PLANNING_TASK.value)

    for marker in cfg.complexity_markers:
        if marker in task_desc:
            return (True, EscalationReason.MULTI_STEP_REASONING.value)

    return (False, "")


# ---------------------------------------------------------------------------
# call_advisor() — invoke the advisor model
# ---------------------------------------------------------------------------


def call_advisor(
    task: str,
    executor_output: str,
    context: dict[str, Any],
    metadata: dict[str, Any],
    *,
    config: EscalationConfig | None = None,
    escalation_reason: str = "",
    workflow_id: str | None = None,
) -> AdvisorResult:
    """Call the advisor model for guidance on an executor result.

    The advisor receives:
      - the original task
      - the executor's output
      - graph context (centrality, dependents)
      - risk metadata
      - the escalation reason

    The advisor returns structured guidance: approve, modify, or reject.
    If the advisor fails or times out, returns APPROVE with a note.
    """
    cfg = config or DEFAULT_CONFIG
    t0 = time.monotonic()

    # Budget check
    if not _check_workflow_budget(workflow_id, cfg):
        return AdvisorResult(
            decision=AdvisorDecision.APPROVE.value,
            reasoning="advisor budget exhausted for this workflow; using executor result",
            escalation_reason=escalation_reason,
        )

    # Rate limit check
    if not _RATE_LIMITER.allow():
        return AdvisorResult(
            decision=AdvisorDecision.APPROVE.value,
            reasoning="advisor rate limit reached; using executor result",
            escalation_reason=escalation_reason,
        )

    # Build the advisor prompt
    prompt = _build_advisor_prompt(
        task, executor_output, context, metadata, escalation_reason
    )

    # Call the advisor model via the harness (lazy import to avoid circulars)
    try:
        from core.agent_harness import default_harness

        harness = default_harness()
        llm_result = harness.run_llm(
            "advisor",
            prompt,
            system=_ADVISOR_SYSTEM_PROMPT,
            task_type="strategic",
            trigger_source="advisor",
            risk="none",
            timeout=cfg.advisor_timeout_sec,
        )
    except Exception as exc:
        result = AdvisorResult(
            decision=AdvisorDecision.APPROVE.value,
            reasoning=f"advisor call failed: {exc}; using executor result",
            escalation_reason=escalation_reason,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        _log_advisor_call(task, escalation_reason, result, workflow_id)
        return result

    latency = int((time.monotonic() - t0) * 1000)

    if not llm_result.ok:
        result = AdvisorResult(
            decision=AdvisorDecision.APPROVE.value,
            reasoning=f"advisor LLM failed: {llm_result.error}; using executor result",
            escalation_reason=escalation_reason,
            latency_ms=latency,
        )
        _log_advisor_call(task, escalation_reason, result, workflow_id)
        return result

    # Parse the advisor's structured response
    result = _parse_advisor_response(
        str(llm_result.output),
        llm_result.provider,
        latency,
        escalation_reason,
    )

    _increment_workflow_count(workflow_id)
    _log_advisor_call(task, escalation_reason, result, workflow_id)
    return result


# ---------------------------------------------------------------------------
# run_with_advisor() — the unified execution interface
# ---------------------------------------------------------------------------


def run_with_advisor(
    task: str,
    context: dict[str, Any],
    metadata: dict[str, Any],
    *,
    executor_fn: Callable[..., Any] | None = None,
    executor_result: Any = None,
    config: EscalationConfig | None = None,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Unified execution interface with conditional advisor escalation.

    Flow:
      1. If executor_result not provided, call executor_fn(task, context)
      2. Evaluate result with needs_advisor()
      3. If escalation triggered, call advisor
      4. Merge advisor output with executor result
      5. Return final result

    Args:
        task:             the task description / prompt
        context:          execution context (graph, step info, etc.)
        metadata:         risk, flags, task_type, etc.
        executor_fn:      callable that produces the executor result
                          (receives task, context as args)
        executor_result:  pre-computed executor result (skips executor_fn)
        config:           escalation config overrides
        workflow_id:      for per-workflow budget tracking

    Returns:
        dict with keys: output, advisor_used, advisor_result, executor_output,
        escalation_reason, merged
    """
    cfg = config or DEFAULT_CONFIG

    # Step 1: Get executor output
    if executor_result is not None:
        exec_output = executor_result
    elif executor_fn is not None:
        try:
            exec_output = executor_fn(task, context)
        except Exception as exc:
            exec_output = f"executor failed: {exc}"
            # Failure always triggers advisor
            metadata = dict(metadata)
            metadata["advisor_on_failure"] = True
            context = dict(context)
            context["previous_step_failed"] = True
    else:
        raise ValueError("must provide executor_fn or executor_result")

    exec_text = _extract_output_text(exec_output)

    # Step 2: Check escalation
    should_escalate, reason = needs_advisor(exec_output, context, metadata, config=cfg)

    if not should_escalate:
        return {
            "output": exec_text,
            "advisor_used": False,
            "advisor_result": None,
            "executor_output": exec_text,
            "escalation_reason": "",
            "merged": False,
        }

    # Step 3: Call advisor
    advice = call_advisor(
        task,
        exec_text,
        context,
        metadata,
        config=cfg,
        escalation_reason=reason,
        workflow_id=workflow_id,
    )

    # Step 4: Merge based on decision
    if advice.decision == AdvisorDecision.APPROVE.value:
        final_output = exec_text
        merged = False
    elif advice.decision == AdvisorDecision.MODIFY.value:
        final_output = (
            advice.suggested_changes if advice.suggested_changes else exec_text
        )
        merged = True
    elif advice.decision == AdvisorDecision.REJECT.value:
        final_output = f"ADVISOR_REJECTED: {advice.reasoning}"
        merged = True
    else:
        final_output = exec_text
        merged = False

    return {
        "output": final_output,
        "advisor_used": True,
        "advisor_result": advice.to_dict(),
        "advisor_canonical": advice.to_canonical(),
        "executor_output": exec_text,
        "escalation_reason": reason,
        "merged": merged,
    }


# ---------------------------------------------------------------------------
# Advisor prompt construction
# ---------------------------------------------------------------------------


_ADVISOR_SYSTEM_PROMPT = (
    "You are the Advisor — a high-capability model that reviews executor "
    "outputs for correctness, completeness, and safety. You NEVER execute "
    "actions or produce side effects. You ONLY provide structured guidance.\n\n"
    "Respond in EXACTLY this JSON format (no markdown, no extra text):\n"
    "{\n"
    '  "decision": "approve" | "modify" | "reject",\n'
    '  "reasoning": "why you made this decision",\n'
    '  "modifications": ["list", "of", "concrete", "changes"],\n'
    '  "confidence": 0.0 to 1.0\n'
    "}\n\n"
    "Rules:\n"
    "- approve: executor result is correct and complete, modifications=[]\n"
    "- modify: executor result needs refinement; list modifications\n"
    "- reject: executor result is wrong or dangerous; explain in reasoning\n"
    "- Be concise. No preamble. JSON only. No markdown code fences."
)


def _build_advisor_prompt(
    task: str,
    executor_output: str,
    context: dict[str, Any],
    metadata: dict[str, Any],
    escalation_reason: str,
) -> str:
    """Build the prompt sent to the advisor model."""
    parts = [
        f"TASK: {task}",
        f"\nEXECUTOR OUTPUT:\n{executor_output[:3000]}",
        f"\nESCALATION REASON: {escalation_reason}",
    ]

    # Add graph context if available
    if context.get("is_critical_hub"):
        parts.append(
            f"\nGRAPH: This targets a critical hub (rank {context.get('centrality_rank', '?')})"
        )
    dep_count = context.get("dependent_count", 0)
    if dep_count > 0:
        parts.append(f"\nDEPENDENTS: {dep_count} files depend on the target")

    # Add risk context
    risk = metadata.get("risk", "none")
    if risk and risk != "none":
        parts.append(f"\nRISK LEVEL: {risk}")

    # Add failure context
    if context.get("previous_step_failed"):
        parts.append("\nCONTEXT: The previous step in this workflow FAILED")
    attempts = context.get("attempts", 0)
    if attempts > 1:
        parts.append(f"\nRETRIES: This is attempt #{attempts}")

    parts.append("\n\nReview the executor output and provide your assessment as JSON.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_advisor_response(
    raw: str,
    provider: str,
    latency_ms: int,
    escalation_reason: str,
) -> AdvisorResult:
    """Parse the advisor's JSON response into an AdvisorResult."""
    # Try to extract JSON from the response
    text = raw.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON within the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return AdvisorResult(
                    decision=AdvisorDecision.APPROVE.value,
                    reasoning=f"advisor response not parseable; raw: {raw[:200]}",
                    advisor_model=provider,
                    latency_ms=latency_ms,
                    escalation_reason=escalation_reason,
                )
        else:
            return AdvisorResult(
                decision=AdvisorDecision.APPROVE.value,
                reasoning=f"advisor response not parseable; raw: {raw[:200]}",
                advisor_model=provider,
                latency_ms=latency_ms,
                escalation_reason=escalation_reason,
            )

    # Validate decision
    decision = str(data.get("decision", "approve")).lower()
    if decision not in (d.value for d in AdvisorDecision):
        decision = AdvisorDecision.APPROVE.value

    confidence = data.get("confidence", 0.8)
    if not isinstance(confidence, (int, float)):
        confidence = 0.8
    confidence = max(0.0, min(1.0, float(confidence)))

    # Extract modifications — accept list or string from LLM
    raw_mods = data.get("modifications") or data.get("suggested_changes") or ""
    if isinstance(raw_mods, list):
        modifications = [str(m) for m in raw_mods if m]
    elif isinstance(raw_mods, str) and raw_mods.strip():
        modifications = [line.strip() for line in raw_mods.split("\n")
                         if line.strip()]
    else:
        modifications = []

    suggested_changes = str(data.get("suggested_changes", ""))

    # Accept 'reason' as alias for 'reasoning' (LLMs use both)
    reasoning = str(data.get("reasoning") or data.get("reason") or "")

    return AdvisorResult(
        decision=decision,
        reasoning=reasoning,
        suggested_changes=suggested_changes,
        modifications=modifications,
        confidence=confidence,
        advisor_model=provider,
        latency_ms=latency_ms,
        escalation_reason=escalation_reason,
    )


# ---------------------------------------------------------------------------
# Output extraction helper
# ---------------------------------------------------------------------------


def _extract_output_text(result: Any) -> str:
    """Extract a string from various result types."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("output", "summary", "content", "response", "text"):
            v = result.get(key)
            if v:
                return str(v)
        return str(result)
    # HarnessResult-like
    for attr in ("output", "response", "text"):
        v = getattr(result, attr, None)
        if v:
            return str(v)
    return str(result)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log_advisor_call(
    task: str,
    escalation_reason: str,
    result: AdvisorResult,
    workflow_id: str | None = None,
) -> None:
    """Append an entry to the advisor log."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "task_preview": task[:200],
            "escalation_reason": escalation_reason,
            "decision": result.decision,
            "reasoning": result.reasoning[:300],
            "confidence": result.confidence,
            "advisor_model": result.advisor_model,
            "latency_ms": result.latency_ms,
            "workflow_id": workflow_id,
        }
        with ADVISOR_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Stats helper (used by observability + CLI)
# ---------------------------------------------------------------------------


def advisor_stats(limit: int = 500) -> dict[str, Any]:
    """Compute stats from the advisor log."""
    if not ADVISOR_LOG.exists():
        return {
            "total_calls": 0,
            "decisions": {},
            "escalation_reasons": {},
            "avg_latency_ms": 0,
            "avg_confidence": 0.0,
        }

    rows: list[dict[str, Any]] = []
    try:
        with ADVISOR_LOG.open("r", encoding="utf-8") as f:
            for line in f.readlines()[-limit:]:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        pass

    if not rows:
        return {
            "total_calls": 0,
            "decisions": {},
            "escalation_reasons": {},
            "avg_latency_ms": 0,
            "avg_confidence": 0.0,
        }

    decisions: dict[str, int] = {}
    reasons: dict[str, int] = {}
    total_latency = 0
    total_confidence = 0.0

    for r in rows:
        d = r.get("decision", "unknown")
        decisions[d] = decisions.get(d, 0) + 1
        reason = r.get("escalation_reason", "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
        total_latency += r.get("latency_ms", 0)
        total_confidence += r.get("confidence", 0.0)

    n = len(rows)
    return {
        "total_calls": n,
        "decisions": decisions,
        "escalation_reasons": reasons,
        "avg_latency_ms": round(total_latency / n) if n else 0,
        "avg_confidence": round(total_confidence / n, 3) if n else 0.0,
    }


def recent_advisor_calls(n: int = 10) -> list[dict[str, Any]]:
    """Return the last N advisor log entries."""
    if not ADVISOR_LOG.exists():
        return []
    try:
        with ADVISOR_LOG.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        out: list[dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out
    except Exception:
        return []


__all__ = [
    "AdvisorDecision",
    "AdvisorResult",
    "DEFAULT_CONFIG",
    "EscalationConfig",
    "EscalationReason",
    "advisor_stats",
    "call_advisor",
    "needs_advisor",
    "recent_advisor_calls",
    "reset_workflow_count",
    "run_with_advisor",
]
