"""
agent_harness.py — Unified execution surface for every agent in EOS.

Every agent call flows through AgentHarness. The harness owns:

  * Tools         → scripts.action_system.ActionSystem
  * Memory        → runtime.memory.AgentMemory + ConversationMemory
  * Graph access  → scripts.query_graph.GraphQuery
  * Permissions   → core.capability.CapabilityEnforcer
  * Model routing → runtime.model_router.call_with_fallback

The harness never raises from its public methods; it always returns a
HarnessResult with ok=True/False. Failures are logged; nothing bubbles up
unchecked.

Usage:
    from core.agent_harness import AgentHarness

    harness = AgentHarness()
    out = harness.run_llm(
        agent="researcher",
        prompt="summarize the graph layer",
        task_type="analysis",
    )
    print(out.output)

    out = harness.run_action(
        agent="executor",
        action_type="query_graph",
        target="state/memory/memory.py",
        payload={"question": "dependents"},
        reason="pre-refactor impact",
    )
    print(out.output)

Design constraints:
  * Lazy-import everything heavy (runtime.*, scripts.action_system) so
    importing this module is cheap enough to use in CLIs and unit tests.
  * No global state beyond a single HARNESS singleton factory.
  * Every public method takes an `agent` name — always validated against
    DEFAULT_PROFILES in core.capability.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.capability import (  # noqa: E402
    CapabilityEnforcer,
    CapabilityProfile,
    OperationKind,
    RiskTier,
    DEFAULT_PROFILES,
    get_profile,
    operation_for_action_type,
)


DATA_DIR = Path(_REPO_ROOT) / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HARNESS_LOG = DATA_DIR / "harness_log.jsonl"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class HarnessResult:
    """Canonical return value from every harness call.

    ok:            operation completed successfully
    output:        string or dict result (content + metadata)
    error:         short error string when ok=False
    provider:      model or tool name that fulfilled the call
    operation:     OperationKind value
    agent:         agent name that made the call
    duration_ms:   wall-clock duration
    metadata:      free-form extras (graph hits, action ids, etc.)
    """

    ok: bool
    output: Any
    error: str | None = None
    provider: str = ""
    operation: str = ""
    agent: str = ""
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# The harness
# ---------------------------------------------------------------------------


class AgentHarness:
    """Single execution surface. One instance per process is sufficient."""

    def __init__(
        self,
        *,
        enforcer: CapabilityEnforcer | None = None,
        profiles: dict[str, CapabilityProfile] | None = None,
        verbose: bool = False,
    ) -> None:
        self.verbose = verbose
        self.enforcer = enforcer or CapabilityEnforcer()
        self._profiles: dict[str, CapabilityProfile] = dict(
            profiles or DEFAULT_PROFILES
        )
        self._action_system: Any | None = None
        self._graph_query: Any | None = None
        self._agent_memory: Any | None = None
        self._conversation_memory: Any | None = None
        self._model_router: Callable[..., Any] | None = None
        self._lock = threading.Lock()

    # ── Profile registration ─────────────────────────────────────────────

    def register_profile(self, profile: CapabilityProfile) -> None:
        self._profiles[profile.name] = profile

    def profile(self, agent: str) -> CapabilityProfile:
        p = self._profiles.get(agent)
        if p is None:
            return get_profile(agent)  # raises with clear error
        return p

    def agents(self) -> list[str]:
        return sorted(self._profiles.keys())

    # ── Lazy dependencies ────────────────────────────────────────────────

    def _actions(self) -> Any:
        with self._lock:
            if self._action_system is None:
                from scripts.action_system import ActionSystem

                self._action_system = ActionSystem(verbose=self.verbose)
            return self._action_system

    def _graph(self) -> Any:
        with self._lock:
            if self._graph_query is None:
                try:
                    from scripts.query_graph import GraphQuery

                    self._graph_query = GraphQuery.load()
                except Exception as e:
                    if self.verbose:
                        print(f"[harness] graph load failed: {e}")
                    self._graph_query = False  # sentinel
            return self._graph_query if self._graph_query else None

    def _memory(self) -> Any:
        with self._lock:
            if self._agent_memory is None:
                try:
                    from state.memory.memory import AgentMemory

                    self._agent_memory = AgentMemory()
                except Exception as e:
                    if self.verbose:
                        print(f"[harness] memory init failed: {e}")
                    self._agent_memory = False
            return self._agent_memory if self._agent_memory else None

    def _router(self) -> Callable[..., Any] | None:
        with self._lock:
            if self._model_router is None:
                try:
                    from execution.runtime.model_router import call_with_fallback

                    self._model_router = call_with_fallback
                except Exception as e:
                    if self.verbose:
                        print(f"[harness] router import failed: {e}")
                    self._model_router = False  # type: ignore[assignment]
            return self._model_router if self._model_router else None

    # ── Public: LLM call ──────────────────────────────────────────────────

    # Hard wallclock cap for a single LLM call. The fallback chain
    # (CC SDK → Ollama) can collectively take a long time if a provider
    # hangs on retries; we never let the harness block forever.
    LLM_TIMEOUT_SEC = 45.0

    def run_llm(
        self,
        agent: str,
        prompt: str,
        *,
        system: str | None = None,
        task_type: str = "fast_response",
        trigger_source: str = "harness",
        graph_search: str | None = None,
        risk: str | RiskTier = RiskTier.NONE,
        timeout: float | None = None,
    ) -> HarnessResult:
        """Run an LLM call on behalf of an agent.

        Enforces CALL_LLM capability. Optionally enriches the prompt with
        graph search hits (only when the agent has READ_GRAPH). Returns a
        HarnessResult with output=str content.
        """
        t0 = time.monotonic()
        try:
            profile = self.profile(agent)
        except KeyError as e:
            return self._fail("run_llm", agent, str(e), t0)

        # Permission: may this agent call the LLM?
        decision = self.enforcer.may(profile, OperationKind.CALL_LLM, risk)
        if not decision.allowed:
            return self._fail("run_llm", agent, decision.reason, t0)

        # Optional graph enrichment
        enriched = prompt
        metadata: dict[str, Any] = {}
        if graph_search:
            gd = self.enforcer.may(profile, OperationKind.READ_GRAPH)
            if gd.allowed:
                hits = self.graph_search(agent, graph_search)
                if hits.ok and hits.output:
                    metadata["graph_hits"] = hits.output
                    enriched += "\n\nGraph matches:\n- " + "\n- ".join(
                        str(h) for h in hits.output[:10]
                    )

        router = self._router()
        if router is None:
            return self._fail(
                "run_llm", agent, "model_router unavailable", t0, op="call_llm"
            )

        # Run the router call on a worker thread so we can wall-clock it.
        # If the timeout fires we abandon the worker (it is a daemon and
        # will die with the process). The alternative — letting the call
        # hang forever — breaks the orchestrator's tick loop.
        is_ceo = agent == "ceo"
        budget = float(timeout if timeout is not None else self.LLM_TIMEOUT_SEC)
        box: dict[str, Any] = {}

        def _call() -> None:
            try:
                box["raw"] = router(
                    prompt=enriched or "Summarize what you know.",
                    system=system,
                    task_type=task_type,
                    trigger_source=trigger_source,
                    agent_type="ceo" if is_ceo else None,
                )
            except Exception as exc:  # noqa: BLE001 — reported via box
                box["err"] = exc

        worker = threading.Thread(
            target=_call, name=f"harness-llm-{agent}", daemon=True
        )
        worker.start()
        worker.join(timeout=budget)
        if worker.is_alive():
            return self._fail(
                "run_llm",
                agent,
                f"router: timeout after {budget:.0f}s",
                t0,
                op="call_llm",
            )
        if "err" in box:
            return self._fail(
                "run_llm", agent, f"router: {box['err']}", t0, op="call_llm"
            )
        raw = box.get("raw")

        output = _routing_output(raw)
        provider = _routing_provider(raw)

        result = HarnessResult(
            ok=True,
            output=output,
            provider=provider,
            operation=OperationKind.CALL_LLM.value,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
            metadata=metadata,
        )
        self._log(result, extra={"prompt_preview": (prompt or "")[:160]})
        return result

    # ── Public: Action dispatch ──────────────────────────────────────────

    def run_action(
        self,
        agent: str,
        action_type: str,
        target: str,
        *,
        payload: dict[str, Any] | None = None,
        reason: str = "",
        approve: bool = False,
        dry_run: bool = False,
    ) -> HarnessResult:
        """Propose + execute an action through the action system.

        Enforces capability based on (action_type, critical_hub_flag, risk).
        The action system still does its own risk assessment; this is
        defense in depth. If the agent lacks capability, nothing touches
        the filesystem.
        """
        t0 = time.monotonic()
        payload = payload or {}

        try:
            profile = self.profile(agent)
        except KeyError as e:
            return self._fail("run_action", agent, str(e), t0)

        actions = self._actions()
        try:
            from scripts.action_system import ActionType
        except Exception as e:
            return self._fail("run_action", agent, f"action import: {e}", t0)

        try:
            at_enum = ActionType(action_type)
        except ValueError:
            return self._fail(
                "run_action", agent, f"unknown action type: {action_type}", t0
            )

        # Propose first — this runs impact analysis and risk evaluation.
        try:
            action = actions.propose(
                action_type=at_enum,
                target=target,
                payload=payload,
                reason=reason or f"harness:{agent}",
            )
        except Exception as e:
            return self._fail("run_action", agent, f"propose: {e}", t0)

        # Translate to capability terms using the freshly computed impact.
        is_critical_hub = bool(
            action.impact is not None and action.impact.is_critical_hub
        )
        op_kind = operation_for_action_type(
            action_type, is_critical_hub=is_critical_hub
        )
        risk = (
            action.risk_level.value
            if hasattr(action.risk_level, "value")
            else str(action.risk_level)
        )

        decision = self.enforcer.may(profile, op_kind, risk)
        if not decision.allowed:
            return self._fail(
                "run_action",
                agent,
                decision.reason,
                t0,
                op=op_kind.value,
                extra={"action_id": action.id, "risk": risk},
            )

        # If the enforcer says approval is needed and none was passed, refuse.
        if decision.needs_approval and not approve and not dry_run:
            return self._fail(
                "run_action",
                agent,
                f"{op_kind.value} at risk={risk} needs approval",
                t0,
                op=op_kind.value,
                extra={"action_id": action.id, "risk": risk, "needs_approval": True},
            )

        # Execute through the action system (its gate also fires).
        try:
            result = actions.execute(action, dry_run=dry_run, approve=approve)
        except Exception as e:
            return self._fail(
                "run_action", agent, f"execute: {e}", t0, op=op_kind.value
            )

        status = (
            result.status.value
            if hasattr(result.status, "value")
            else str(result.status)
        )
        ok = status in ("succeeded", "skipped_dry_run")
        hr = HarnessResult(
            ok=ok,
            output={
                "action_id": action.id,
                "status": status,
                "output": result.output,
                "error": result.error,
                "risk": risk,
            },
            error=None if ok else (result.error or f"action status={status}"),
            provider="action_system",
            operation=op_kind.value,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
            metadata={
                "action_id": action.id,
                "dependents": (
                    action.impact.direct_dependents[:10] if action.impact else []
                ),
                "critical_hub": is_critical_hub,
            },
        )
        self._log(hr, extra={"target": target, "action_type": action_type})
        return hr

    # ── Public: Advisor-gated execution ─────────────────────────────────

    def run_with_advisor(
        self,
        agent: str,
        task: str,
        context: dict[str, Any],
        metadata: dict[str, Any],
        *,
        system: str | None = None,
        task_type: str = "fast_response",
        workflow_id: str | None = None,
    ) -> HarnessResult:
        """Run an LLM call with conditional advisor escalation.

        Flow:
          1. Execute task with fast model (executor)
          2. Evaluate result with escalation rules
          3. If escalated, call advisor for guidance
          4. Merge advisor output with executor result
          5. Return final HarnessResult with advisor metadata

        The advisor NEVER executes actions — it only guides.
        """
        t0 = time.monotonic()

        # Step 1: Run with executor (fast model)
        executor_result = self.run_llm(
            agent,
            task,
            system=system,
            task_type=task_type,
            trigger_source="advisor_executor",
        )

        if not executor_result.ok:
            # If executor failed, enrich context for advisor
            context = dict(context)
            context["previous_step_failed"] = True

        # Step 2+3+4: Run through advisor pipeline
        try:
            from core.advisor import run_with_advisor as _run_advisor

            advisor_output = _run_advisor(
                task=task,
                context=context,
                metadata=metadata,
                executor_result=executor_result,
                workflow_id=workflow_id,
            )
        except Exception as exc:
            # Advisor import/call failure — use executor result as-is
            executor_result.metadata["advisor_error"] = str(exc)
            executor_result.metadata["advisor_used"] = False
            executor_result.duration_ms = int((time.monotonic() - t0) * 1000)
            return executor_result

        # Step 5: Build final result
        advisor_used = advisor_output.get("advisor_used", False)
        final_output = advisor_output.get("output", executor_result.output)

        result = HarnessResult(
            ok=executor_result.ok if not advisor_output.get("merged") else True,
            output=final_output,
            error=executor_result.error if not advisor_used else None,
            provider=executor_result.provider,
            operation=OperationKind.CALL_LLM.value,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
            metadata={
                **executor_result.metadata,
                "advisor_used": advisor_used,
                "advisor_result": advisor_output.get("advisor_result"),
                "escalation_reason": advisor_output.get("escalation_reason", ""),
                "merged": advisor_output.get("merged", False),
            },
        )
        self._log(
            result,
            extra={
                "advisor_used": advisor_used,
                "escalation_reason": advisor_output.get("escalation_reason", ""),
            },
        )
        return result

    # ── Public: graph + memory helpers ───────────────────────────────────

    def graph_search(self, agent: str, term: str) -> HarnessResult:
        t0 = time.monotonic()
        try:
            profile = self.profile(agent)
        except KeyError as e:
            return self._fail("graph_search", agent, str(e), t0)

        decision = self.enforcer.may(profile, OperationKind.READ_GRAPH)
        if not decision.allowed:
            return self._fail("graph_search", agent, decision.reason, t0)

        gq = self._graph()
        if gq is None:
            return self._fail(
                "graph_search",
                agent,
                "graph unavailable",
                t0,
                op=OperationKind.READ_GRAPH.value,
            )
        try:
            hits = list(gq.search(term))[:25]
        except Exception as e:
            return self._fail(
                "graph_search",
                agent,
                f"search: {e}",
                t0,
                op=OperationKind.READ_GRAPH.value,
            )

        return HarnessResult(
            ok=True,
            output=hits,
            provider="graph",
            operation=OperationKind.READ_GRAPH.value,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    def remember(
        self,
        agent: str,
        content: str,
        *,
        task_type: str = "harness",
        venture_id: str | None = None,
    ) -> HarnessResult:
        """Write a free-form note to AgentMemory on behalf of an agent."""
        t0 = time.monotonic()
        try:
            profile = self.profile(agent)
        except KeyError as e:
            return self._fail("remember", agent, str(e), t0)

        decision = self.enforcer.may(profile, OperationKind.WRITE_MEMORY)
        if not decision.allowed:
            return self._fail("remember", agent, decision.reason, t0)

        mem = self._memory()
        if mem is None:
            # Memory unavailable is non-fatal but we still report it
            return self._fail(
                "remember",
                agent,
                "memory unavailable",
                t0,
                op=OperationKind.WRITE_MEMORY.value,
            )

        try:
            from execution.runtime.agent_runtime import AgentResult

            ar = AgentResult(
                output=content[:2000],
                model_used="harness",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used=f"harness:{agent}",
            )
            mem.log(
                agent_result=ar,
                venture_id=venture_id,
                input_summary=content[:300],
                agent=agent,
                task_type=task_type,
                lead_username=None,
            )
        except Exception as e:
            return self._fail(
                "remember",
                agent,
                f"mem.log: {e}",
                t0,
                op=OperationKind.WRITE_MEMORY.value,
            )

        return HarnessResult(
            ok=True,
            output={"bytes": len(content)},
            operation=OperationKind.WRITE_MEMORY.value,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    # ── Error + logging helpers ──────────────────────────────────────────

    def _fail(
        self,
        method: str,
        agent: str,
        reason: str,
        t0: float,
        *,
        op: str = "",
        extra: dict[str, Any] | None = None,
    ) -> HarnessResult:
        hr = HarnessResult(
            ok=False,
            output=None,
            error=reason,
            operation=op or method,
            agent=agent,
            duration_ms=int((time.monotonic() - t0) * 1000),
            metadata=dict(extra or {}),
        )
        self._log(hr, method=method)
        return hr

    def _log(
        self,
        result: HarnessResult,
        *,
        method: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        try:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "method": method or result.operation,
                "agent": result.agent,
                "operation": result.operation,
                "ok": result.ok,
                "provider": result.provider,
                "duration_ms": result.duration_ms,
                "error": result.error,
            }
            if extra:
                entry.update({k: v for k, v in extra.items() if _json_safe(v)})
            if result.metadata:
                entry["metadata"] = {
                    k: v for k, v in result.metadata.items() if _json_safe(v)
                }
            with HARNESS_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            if self.verbose:
                print(f"[harness] log write failed: {e}")


# ---------------------------------------------------------------------------
# Module-level singleton (optional convenience)
# ---------------------------------------------------------------------------


_DEFAULT: AgentHarness | None = None
_DEFAULT_LOCK = threading.Lock()


def default_harness() -> AgentHarness:
    """Return the process-wide harness. Build one on first use."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = AgentHarness()
        return _DEFAULT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _routing_output(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        return str(result.get("output") or result.get("response") or "")
    for attr in ("output", "response", "text"):
        v = getattr(result, attr, None)
        if v:
            return str(v)
    return str(result)


def _routing_provider(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        return str(result.get("provider") or result.get("model") or "")
    for attr in ("provider", "model", "model_used"):
        v = getattr(result, attr, None)
        if v:
            return str(v)
    return ""


def _json_safe(v: Any) -> bool:
    try:
        json.dumps(v, default=str)
        return True
    except Exception:
        return False


__all__ = [
    "AgentHarness",
    "HarnessResult",
    "default_harness",
]
