"""UMH Execution Runtime — generic call lifecycle and result envelope.

Provides:
  - RuntimeResult: normalized result from any LLM/capability call
  - RateLimiter: in-memory per-org rate limiting
  - CostTable: model → cost-per-million-tokens lookup
  - calculate_cost(): USD cost for a completed call
  - execute_with_fallback(): call lifecycle with retry, timeout, rate
    limiting, cost tracking, and normalized result shape

Standalone — no umh imports. All model routing goes through
umh.adapters.model_router.

Usage:
    from umh.execution.runtime import execute_with_fallback, RuntimeResult

    result = execute_with_fallback(
        prompt="Analyze this signal...",
        task_type="analyze",
        org_id="org_123",
    )
    print(result.output, result.cost_usd)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

_log = logging.getLogger(__name__)

# ─── Result envelope ─────────────────────────────────────────────────────────


@dataclass
class RuntimeResult:
    """Normalized result from any execution call.

    ok/output/error contract. Carries cost, token, and timing metadata.
    """

    ok: bool
    output: str
    error: str | None = None
    model_used: str = "unknown"
    provider: str = "unknown"
    task_type: str = ""
    tokens_used: dict[str, int] = field(
        default_factory=lambda: {"input": 0, "output": 0, "total": 0}
    )
    cost_usd: float = 0.0
    duration_ms: int = 0
    interaction_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Cost calculation ────────────────────────────────────────────────────────

COST_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "sonar-pro": {"input": 1.00, "output": 1.00},
    "qwen2.5:0.5b": {"input": 0.0, "output": 0.0},
}

DEFAULT_COST_RATES: dict[str, float] = {"input": 3.00, "output": 15.00}


def calculate_cost(model: str, tokens_used: dict[str, int]) -> float:
    """Return USD cost for a completed API call."""
    rates = COST_PER_MILLION_TOKENS.get(model, DEFAULT_COST_RATES)
    input_cost = tokens_used.get("input", 0) / 1_000_000 * rates["input"]
    output_cost = tokens_used.get("output", 0) / 1_000_000 * rates["output"]
    return round(input_cost + output_cost, 8)


# ─── Rate limiter ────────────────────────────────────────────────────────────


class RateLimiter:
    """In-memory per-org rate limiter.

    Prevents runaway loops or malicious input from draining API credits.
    """

    _counts: dict[str, dict[str, int]] = {}

    LIMITS = {
        "per_minute": 30,
        "per_hour": 500,
    }

    @classmethod
    def check(cls, org_id: str) -> bool:
        """Return True if call is allowed."""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        hour_key = now.strftime("%Y%m%d%H")

        if org_id not in cls._counts:
            cls._counts[org_id] = {}

        counts = cls._counts[org_id]

        minute_count = counts.get(minute_key, 0)
        if minute_count >= cls.LIMITS["per_minute"]:
            _log.warning("Rate limit (minute) hit: org=%s count=%d", org_id, minute_count)
            return False

        hour_count = counts.get(hour_key, 0)
        if hour_count >= cls.LIMITS["per_hour"]:
            _log.warning("Rate limit (hour) hit: org=%s count=%d", org_id, hour_count)
            return False

        counts[minute_key] = minute_count + 1
        counts[hour_key] = hour_count + 1

        cls._counts[org_id] = {k: v for k, v in counts.items() if k in (minute_key, hour_key)}
        return True

    @classmethod
    def reset(cls) -> None:
        """Clear all rate limit state (for testing)."""
        cls._counts.clear()


# ─── Retry configuration ────────────────────────────────────────────────────

MAX_RETRIES = 4
BACKOFF_BASE = 2  # seconds — delays: 2 → 4 → 8 → 16


# ─── Observer protocol ───────────────────────────────────────────────────────


@runtime_checkable
class RuntimeObserver(Protocol):
    """Optional lifecycle callbacks for execution monitoring."""

    def on_call_start(self, prompt: str, task_type: str, org_id: str) -> None: ...

    def on_call_complete(self, result: RuntimeResult) -> None: ...

    def on_rate_limited(self, org_id: str) -> None: ...

    def on_retry(self, attempt: int, error: str) -> None: ...


class NullRuntimeObserver:
    """No-op observer — safe default."""

    def on_call_start(self, prompt: str, task_type: str, org_id: str) -> None:
        pass

    def on_call_complete(self, result: RuntimeResult) -> None:
        pass

    def on_rate_limited(self, org_id: str) -> None:
        pass

    def on_retry(self, attempt: int, error: str) -> None:
        pass


_observer: RuntimeObserver = NullRuntimeObserver()


def set_runtime_observer(obs: RuntimeObserver) -> None:
    """Inject a runtime observer for monitoring/tracing."""
    global _observer
    _observer = obs


def get_runtime_observer() -> RuntimeObserver:
    """Get the current runtime observer."""
    return _observer


# ─── Core execution function ────────────────────────────────────────────────


def execute_with_fallback(
    prompt: str,
    task_type: str = "fast_response",
    system: str | None = None,
    org_id: str = "default",
    max_tokens: int = 1024,
    observer: RuntimeObserver | None = None,
) -> RuntimeResult:
    """Execute an LLM call through UMH model router with full lifecycle.

    1. Rate limit check
    2. Route through UMH model router fallback chain
    3. Calculate cost
    4. Return normalized RuntimeResult

    Never raises — returns a failed RuntimeResult on any error.
    """
    obs = observer or _observer
    start = time.time()

    try:
        obs.on_call_start(prompt, task_type, org_id)
    except Exception:
        pass

    if not RateLimiter.check(org_id):
        try:
            obs.on_rate_limited(org_id)
        except Exception:
            pass
        return RuntimeResult(
            ok=False,
            output="Rate limit reached. Please wait a moment.",
            error="rate_limited",
            model_used="rate_limiter",
            task_type=task_type,
        )

    from umh.execution.engine import lightweight_execute

    try:
        exec_result = lightweight_execute(
            operation=task_type,
            prompt=prompt,
            system=system,
            task_type=task_type,
        )

        duration_ms = int((time.time() - start) * 1000)
        output_text = exec_result.outputs.get("text", "")

        if exec_result.status.value != "succeeded" or not output_text:
            result = RuntimeResult(
                ok=False,
                output=output_text or "All providers exhausted.",
                error=exec_result.error or "all_providers_failed",
                task_type=task_type,
                duration_ms=duration_ms,
            )
        else:
            tokens = exec_result.tokens_used or {"input": 0, "output": 0, "total": 0}
            if "total" not in tokens:
                tokens["total"] = tokens.get("input", 0) + tokens.get("output", 0)
            cost = exec_result.cost_usd or calculate_cost(
                exec_result.model_used or "unknown", tokens
            )

            result = RuntimeResult(
                ok=True,
                output=output_text,
                model_used=exec_result.model_used or "unknown",
                task_type=task_type,
                tokens_used=tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
            )

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        _log.error("execute_with_fallback failed: %s", exc)
        result = RuntimeResult(
            ok=False,
            output=str(exc),
            error=str(exc),
            task_type=task_type,
            duration_ms=duration_ms,
        )

    try:
        obs.on_call_complete(result)
    except Exception:
        pass

    return result
