"""
WorkflowEngine — goal-driven, graph-aware, agent-executed workflows.

Built on top of the existing EOS cognition + execution stack. This engine does
NOT replace:
  - runtime/workflow_engine.py (skill-sequence + AgentWorkflow/Run model)
  - core/execution_contract.py (single-message execution pipeline)
  - scripts/action_system.py  (propose → assess → execute → log for actions)

It composes them into a new surface: given a goal, decompose into steps,
assign each step to an agent with bounded capabilities, resolve dependencies
via topological sort, execute in order, log every outcome, and store the
final result back into memory so future workflows can learn from it.

Four internal agent roles collaborate here (mirroring the task brief):
  1. WORKFLOW DESIGNER  — creates workflow + step graph from a goal template
  2. AGENT SYSTEM       — registers agents, enforces capability whitelists
  3. EXECUTOR           — runs each step via LLM (model_router) or ActionSystem
  4. VERIFIER           — pre-exec validation + post-exec result checks

Contract:
  * Never raises from run_workflow(); always returns a WorkflowResult dict.
  * Every step produces an Outcome row in data/workflow_log.jsonl.
  * Final workflow result is logged to AgentMemory so `semantic_search()`
    surfaces prior outcomes.
  * Dry-run mode traces the plan and skips all side effects (LLM + actions).

Usage:
    python3 scripts/workflow_engine.py list
    python3 scripts/workflow_engine.py run research --goal "How does our graph layer work?" --dry-run
    python3 scripts/workflow_engine.py run content --goal "Write a tweet about Initiate Arena"
    python3 scripts/workflow_engine.py run refactor --goal "Simplify scripts/eos_status.py"

Programmatic:
    from scripts.workflow_engine import WorkflowEngine, build_research_workflow

    engine = WorkflowEngine()
    wf = build_research_workflow("How does the palace get rebuilt?")
    result = engine.run_workflow(wf, dry_run=False)
    print(result["status"], result["result"])
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# ── Repo root on sys.path (EOS convention) ────────────────────────────────
import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── Paths ──────────────────────────────────────────────────────────────────
# These module-level constants are the PRODUCTION defaults. The
# WorkflowEngine uses its own instance-level paths derived from the
# environment passed in at construction time, so sandbox runs land in
# data/sandboxes/<name>/logs/ without touching production.
DATA_DIR = Path(_REPO_ROOT) / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOW_LOG = DATA_DIR / "workflow_log.jsonl"
WORKFLOW_STATE_DIR = DATA_DIR / "workflow_state"
WORKFLOW_STATE_DIR.mkdir(parents=True, exist_ok=True)

from core.environment import Environment  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 1. DATA MODEL  (WORKFLOW DESIGN AGENT)
# ═══════════════════════════════════════════════════════════════════════════


class StepType(str, Enum):
    RESEARCH = "research"  # query graph / memory / LLM summarization
    WRITE = "write"  # generate new content via LLM
    EXECUTE = "execute"  # dispatch an Action through ActionSystem
    DECISION = "decision"  # LLM classifies inputs → choose a branch result


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"  # dry-run or dependency failure
    RETRIED = "retried"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass
class Step:
    """A single unit of work in a workflow.

    dependencies: list of step ids that must succeed before this step runs.
    assigned_agent: name of a registered Agent (see AgentRegistry).
    input: dict with step-type-specific keys. Common:
        - prompt         (research, write, decision)
        - action_type    (execute)  one of ActionSystem.ActionType values
        - target         (execute)  file path or command
        - payload        (execute)  dict for the action
        - choices        (decision) list[str] to classify into
    output: populated after the step runs; shape depends on type.
    """

    id: str
    type: StepType
    input: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str = "generalist"
    status: StepStatus = StepStatus.PENDING
    output: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 2
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    # Advisor flags — step-level overrides for escalation
    requires_advisor: bool = False
    advisor_on_failure: bool = False
    advisor_on_risk: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        d["status"] = self.status.value
        return d


@dataclass
class Workflow:
    """Top-level goal + step graph."""

    id: str
    name: str
    goal: str
    steps: list[Step] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "steps": [s.to_dict() for s in self.steps],
        }

    def step(self, step_id: str) -> Step | None:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 2. AGENT SYSTEM  (AGENT SYSTEM AGENT)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class Agent:
    """A bounded capability unit that can execute a step.

    capabilities     — set of StepType values this agent can run
    allowed_actions  — set of ActionType values (only meaningful for EXECUTE)
    memory_access    — "read" | "write" | "none"
    graph_access     — bool: may call scripts/query_graph.py
    model_task_type  — which model_router TaskType to use for LLM calls
    """

    name: str
    capabilities: set[StepType]
    allowed_actions: set[str] = field(default_factory=set)
    memory_access: str = "read"
    graph_access: bool = True
    model_task_type: str = "fast_response"
    is_ceo: bool = False

    def can_handle(self, step: Step) -> tuple[bool, str]:
        if step.type not in self.capabilities:
            return (False, f"{self.name} lacks capability {step.type.value}")
        if step.type == StepType.EXECUTE:
            at = (step.input or {}).get("action_type", "")
            if at and self.allowed_actions and at not in self.allowed_actions:
                return (False, f"{self.name} not allowed to run action {at}")
        return (True, "")


class AgentRegistry:
    """Lookup table + default roster.

    Keep the roster small and explicit. Adding an agent = adding a role, not
    a whim. Each agent here is a real capability boundary the executor trusts.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Researcher: read-only, graph + memory + LLM summarization
        self.register(
            Agent(
                name="researcher",
                capabilities={StepType.RESEARCH, StepType.DECISION},
                memory_access="read",
                graph_access=True,
                model_task_type="analysis",
            )
        )
        # Writer: produces new text content
        self.register(
            Agent(
                name="writer",
                capabilities={StepType.WRITE, StepType.DECISION},
                memory_access="read",
                graph_access=False,
                model_task_type="generate",
            )
        )
        # Executor: runs actions — intentionally constrained to safer types
        self.register(
            Agent(
                name="executor",
                capabilities={StepType.EXECUTE, StepType.RESEARCH},
                allowed_actions={
                    "query_graph",
                    "edit_file",
                    "write_file",
                    "run_command",
                    "run_script",
                },
                memory_access="write",
                graph_access=True,
                model_task_type="code",
            )
        )
        # Generalist: fallback when no specialized agent is assigned
        self.register(
            Agent(
                name="generalist",
                capabilities={
                    StepType.RESEARCH,
                    StepType.WRITE,
                    StepType.DECISION,
                },
                memory_access="read",
                graph_access=True,
                model_task_type="fast_response",
            )
        )
        # CEO: overrides economy mode for strategic decisions
        self.register(
            Agent(
                name="ceo",
                capabilities={StepType.DECISION, StepType.RESEARCH},
                memory_access="read",
                graph_access=True,
                model_task_type="strategic",
                is_ceo=True,
            )
        )

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        if name not in self._agents:
            raise KeyError(f"unknown agent: {name!r}")
        return self._agents[name]

    def names(self) -> list[str]:
        return sorted(self._agents.keys())


# ═══════════════════════════════════════════════════════════════════════════
# 3. VERIFICATION  (VERIFICATION AGENT)
# ═══════════════════════════════════════════════════════════════════════════


class Verifier:
    """Pre-flight and post-flight safety checks.

    Pre-flight (validate_workflow):
      - IDs unique, dependencies point to real steps, DAG (no cycles)
      - every assigned agent can handle its step
      - EXECUTE steps have action_type + target

    Post-flight (verify_step_output):
      - output dict is non-empty on success
      - failed action results mark the step as FAILED even if no exception
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def validate_workflow(self, wf: Workflow) -> list[str]:
        errors: list[str] = []
        ids = [s.id for s in wf.steps]
        if len(ids) != len(set(ids)):
            errors.append("duplicate step ids")

        id_set = set(ids)
        for s in wf.steps:
            for dep in s.dependencies:
                if dep not in id_set:
                    errors.append(f"step {s.id!r} depends on unknown {dep!r}")
            try:
                agent = self.registry.get(s.assigned_agent)
            except KeyError as e:
                errors.append(str(e))
                continue
            ok, why = agent.can_handle(s)
            if not ok:
                errors.append(f"step {s.id!r}: {why}")
            if s.type == StepType.EXECUTE:
                inp = s.input or {}
                if "action_type" not in inp or "target" not in inp:
                    errors.append(
                        f"step {s.id!r} is execute but missing action_type/target"
                    )

        # Cycle detection via Kahn's algorithm; runs even if other errors
        # above were found so the caller sees cycles explicitly.
        try:
            topological_order(wf.steps)
        except ValueError as e:
            errors.append(str(e))

        return errors

    def verify_step_output(self, step: Step) -> tuple[bool, str]:
        if step.status != StepStatus.SUCCEEDED:
            return (False, f"step status is {step.status.value}")
        if not step.output:
            return (False, "empty output")
        # Execute-type: trust the ActionSystem result embedded in output
        if step.type == StepType.EXECUTE:
            action_status = step.output.get("action_status", "")
            if action_status not in ("succeeded", "skipped_dry_run"):
                return (False, f"action finished with {action_status!r}")
        return (True, "")


# ═══════════════════════════════════════════════════════════════════════════
# 4. DEPENDENCY RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════


def topological_order(steps: list[Step]) -> list[str]:
    """Kahn's algorithm. Returns step ids in a valid execution order.

    Raises ValueError("cycle detected: ...") if the dependency graph is not
    a DAG. We want to fail early, not halfway through a workflow.
    """
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, list[str]] = defaultdict(list)
    all_ids = {s.id for s in steps}
    for s in steps:
        incoming.setdefault(s.id, 0)
        for dep in s.dependencies:
            if dep not in all_ids:
                # validate_workflow reports this; skip here to avoid dupes
                continue
            outgoing[dep].append(s.id)
            incoming[s.id] += 1

    ready: deque[str] = deque(sid for sid, n in incoming.items() if n == 0)
    order: list[str] = []
    while ready:
        sid = ready.popleft()
        order.append(sid)
        for nxt in outgoing[sid]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nxt)

    if len(order) != len(all_ids):
        remaining = sorted(all_ids - set(order))
        raise ValueError(f"cycle detected among steps: {remaining}")
    return order


# ═══════════════════════════════════════════════════════════════════════════
# 5. EXECUTOR  (EXECUTION AGENT)
# ═══════════════════════════════════════════════════════════════════════════


class StepExecutor:
    """Dispatches a Step to its concrete side-effect, using agent constraints.

    Real integration points:
      - RESEARCH → model_router.call_with_fallback (+ optional graph query)
      - WRITE    → model_router.call_with_fallback
      - DECISION → model_router.call_with_fallback with choices in prompt
      - EXECUTE  → scripts.action_system.ActionSystem.propose/execute
    """

    def __init__(
        self,
        registry: AgentRegistry,
        *,
        verbose: bool = False,
        env: Environment | None = None,
    ) -> None:
        self.registry = registry
        self.verbose = verbose
        self.env = env
        self._action_system: Any | None = None  # lazy

    # ── Lazy imports so `--help` and dry-run don't require full env ──────
    def _router_call(self) -> Callable[..., Any]:
        from substrate.execution.runtime.model_router import call_with_fallback

        return call_with_fallback

    def _graph_search(self, term: str) -> list[str]:
        try:
            from scripts.query_graph import GraphQuery  # type: ignore
        except Exception:
            return []
        try:
            gq = GraphQuery.load()
            return list(gq.search(term))[:20]
        except Exception:
            return []

    def _actions(self) -> Any:
        if self._action_system is None:
            from scripts.action_system import ActionSystem

            self._action_system = ActionSystem(verbose=self.verbose, env=self.env)
        return self._action_system

    # ── Per-type handlers ────────────────────────────────────────────────

    def run(self, step: Step, context: dict[str, Any], *, dry_run: bool) -> dict:
        agent = self.registry.get(step.assigned_agent)
        ok, why = agent.can_handle(step)
        if not ok:
            raise PermissionError(why)

        # Inject upstream outputs into the prompt/payload
        prompt = self._expand_prompt(step.input.get("prompt", ""), context)

        if dry_run:
            return {
                "dry_run": True,
                "agent": agent.name,
                "would_run": step.type.value,
                "prompt_preview": prompt[:200],
                "input": step.input,
                "advisor_flags": {
                    "requires_advisor": step.requires_advisor,
                    "advisor_on_failure": step.advisor_on_failure,
                    "advisor_on_risk": step.advisor_on_risk,
                },
            }

        # Dispatch to type-specific handler
        if step.type == StepType.RESEARCH:
            result = self._run_research(agent, step, prompt)
        elif step.type == StepType.WRITE:
            result = self._run_write(agent, step, prompt)
        elif step.type == StepType.DECISION:
            result = self._run_decision(agent, step, prompt)
        elif step.type == StepType.EXECUTE:
            result = self._run_execute(agent, step, context)
        else:
            raise ValueError(f"unknown step type: {step.type}")

        # Advisor gate — evaluate whether this result needs advisor review
        if self._should_use_advisor(step):
            result = self._apply_advisor(step, prompt, result, context)

        return result

    def _should_use_advisor(self, step: Step) -> bool:
        """Check if this step has any advisor flags set."""
        return step.requires_advisor or step.advisor_on_failure or step.advisor_on_risk

    def _apply_advisor(
        self,
        step: Step,
        task: str,
        executor_result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the advisor pipeline on an executor result.

        Non-fatal: if the advisor module fails to import or call,
        returns the executor result unchanged.
        """
        try:
            from core.advisor import run_with_advisor

            advisor_context = {
                "step_type": step.type.value,
                "attempts": step.attempts,
                "previous_step_failed": context.get("previous_step_failed", False),
                "dependent_count": context.get("dependent_count", 0),
                "is_critical_hub": context.get("is_critical_hub", False),
            }
            advisor_metadata = {
                "requires_advisor": step.requires_advisor,
                "advisor_on_failure": step.advisor_on_failure,
                "advisor_on_risk": step.advisor_on_risk,
                "task_type": step.input.get("task_type", ""),
                "risk": context.get("risk", "none"),
            }
            workflow_id = context.get("workflow_id")
            result = run_with_advisor(
                task=task,
                context=advisor_context,
                metadata=advisor_metadata,
                executor_result=executor_result,
                workflow_id=workflow_id,
            )
            # Merge advisor output into the step result
            executor_result["advisor_used"] = result.get("advisor_used", False)
            executor_result["advisor_result"] = result.get("advisor_result")
            executor_result["escalation_reason"] = result.get("escalation_reason", "")
            if result.get("merged") and result.get("output"):
                executor_result["advisor_refined_output"] = result["output"]
        except Exception as exc:
            executor_result["advisor_error"] = str(exc)
        return executor_result

    # ── Handler: RESEARCH ────────────────────────────────────────────────

    def _run_research(self, agent: Agent, step: Step, prompt: str) -> dict:
        graph_hits: list[str] = []
        if agent.graph_access and step.input.get("graph_search"):
            graph_hits = self._graph_search(step.input["graph_search"])

        enriched = prompt
        if graph_hits:
            enriched += "\n\nGraph matches:\n- " + "\n- ".join(graph_hits[:10])

        result = self._router_call()(
            prompt=enriched or "Summarize what you know.",
            task_type=agent.model_task_type,
            trigger_source="workflow",
            agent_type="ceo" if agent.is_ceo else None,
        )
        return {
            "summary": _routing_output(result),
            "provider": _routing_provider(result),
            "graph_hits": graph_hits,
        }

    # ── Handler: WRITE ───────────────────────────────────────────────────

    def _run_write(self, agent: Agent, step: Step, prompt: str) -> dict:
        system = step.input.get("system") or (
            "You are a concise, high-signal writer. Produce the requested "
            "content with zero preamble."
        )
        result = self._router_call()(
            prompt=prompt or "Write the requested content.",
            system=system,
            task_type=agent.model_task_type,
            trigger_source="workflow",
            agent_type="ceo" if agent.is_ceo else None,
        )
        return {
            "content": _routing_output(result),
            "provider": _routing_provider(result),
        }

    # ── Handler: DECISION ────────────────────────────────────────────────

    def _run_decision(self, agent: Agent, step: Step, prompt: str) -> dict:
        choices: list[str] = step.input.get("choices") or []
        if not choices:
            raise ValueError("decision step requires input.choices")
        prompt_with = (
            f"{prompt}\n\n"
            f"Pick exactly ONE of: {', '.join(choices)}.\n"
            f"Respond with only the chosen value, nothing else."
        )
        result = self._router_call()(
            prompt=prompt_with,
            task_type=agent.model_task_type,
            trigger_source="workflow",
            agent_type="ceo" if agent.is_ceo else None,
        )
        raw = _routing_output(result).strip().splitlines()[0].strip()
        # Exact match first, then substring
        choice = next((c for c in choices if c.lower() == raw.lower()), None)
        if choice is None:
            choice = next((c for c in choices if c.lower() in raw.lower()), None)
        if choice is None:
            raise ValueError(f"decision output {raw!r} not in {choices}")
        return {
            "choice": choice,
            "raw": raw,
            "provider": _routing_provider(result),
        }

    # ── Handler: EXECUTE ─────────────────────────────────────────────────

    def _run_execute(self, agent: Agent, step: Step, context: dict) -> dict:
        from scripts.action_system import ActionType

        inp = step.input or {}
        action_type = ActionType(inp["action_type"])
        target = self._expand_prompt(str(inp["target"]), context)
        payload = dict(inp.get("payload") or {})
        # Expand template strings inside payload values
        for k, v in payload.items():
            if isinstance(v, str):
                payload[k] = self._expand_prompt(v, context)
        reason = inp.get("reason") or f"workflow:{step.id}"

        acts = self._actions()
        action = acts.propose(
            action_type=action_type,
            target=target,
            payload=payload,
            reason=reason,
        )
        approve = bool(inp.get("approve", False))
        result = acts.execute(action, dry_run=False, approve=approve)
        return {
            "action_id": action.id,
            "action_status": result.status.value,
            "action_output": result.output,
            "action_error": result.error,
            "risk_level": action.risk_level.value,
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _expand_prompt(tmpl: str, context: dict) -> str:
        """Replace {step_id.key} tokens with upstream step outputs.

        Intentionally minimal. No full Jinja. If a token doesn't resolve,
        it's left as-is so the prompt still makes sense to the LLM.
        """
        if not tmpl or "{" not in tmpl:
            return tmpl
        out = tmpl
        for sid, outputs in context.items():
            if not isinstance(outputs, dict):
                continue
            for k, v in outputs.items():
                token = f"{{{sid}.{k}}}"
                if token in out:
                    out = out.replace(token, str(v))
        return out


def _routing_output(result: Any) -> str:
    """call_with_fallback returns RoutingResult or dict depending on path."""
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


# ═══════════════════════════════════════════════════════════════════════════
# 6. THE ENGINE
# ═══════════════════════════════════════════════════════════════════════════


class WorkflowEngine:
    """Runs workflows end-to-end. One engine per process is enough.

    Environment-aware: pass `env=make_sandbox(...)` to redirect log +
    state writes and any downstream ActionSystem edits into an isolated
    tree. Default is production.
    """

    def __init__(
        self,
        *,
        verbose: bool = False,
        env: Environment | None = None,
    ) -> None:
        self.verbose = verbose
        self.env = env or Environment.production()
        self.registry = AgentRegistry()
        self.verifier = Verifier(self.registry)
        self.executor = StepExecutor(self.registry, verbose=verbose, env=self.env)

        # Instance-level log + state paths. Production defaults match
        # the module-level constants; sandbox runs land inside the env.
        self._workflow_log: Path = self.env.workflow_log_path
        self._state_dir: Path = self.env.workflow_state_dir
        self._workflow_log.parent.mkdir(parents=True, exist_ok=True)
        self._state_dir.mkdir(parents=True, exist_ok=True)

    # ── Public: the whole ride ──────────────────────────────────────────

    def run_workflow(self, wf: Workflow, *, dry_run: bool = False) -> dict:
        errors = self.verifier.validate_workflow(wf)
        if errors:
            wf.status = WorkflowStatus.FAILED
            wf.result = {"error": "validation_failed", "details": errors}
            self._emit("workflow_invalid", wf, extra={"errors": errors})
            return self._finalize(wf)

        order = topological_order(wf.steps)
        wf.status = WorkflowStatus.DRY_RUN if dry_run else WorkflowStatus.RUNNING
        self._emit("workflow_started", wf, extra={"dry_run": dry_run})
        self._save_state(wf)

        context: dict[str, dict[str, Any]] = {}
        any_failed = False

        for sid in order:
            step = wf.step(sid)
            if step is None:
                continue

            # Short-circuit: if any dep failed, mark skipped
            failed_deps = [
                d
                for d in step.dependencies
                if wf.step(d) and wf.step(d).status == StepStatus.FAILED
            ]
            if failed_deps:
                step.status = StepStatus.SKIPPED
                step.error = f"upstream failed: {failed_deps}"
                self._emit("step_skipped", wf, step=step)
                continue

            self._run_step_with_retry(wf, step, context, dry_run=dry_run)
            if step.status == StepStatus.SUCCEEDED:
                context[step.id] = step.output
            elif step.status == StepStatus.FAILED:
                any_failed = True
            self._save_state(wf)

        # Aggregate result
        wf.status = (
            WorkflowStatus.DRY_RUN
            if dry_run
            else (WorkflowStatus.FAILED if any_failed else WorkflowStatus.COMPLETED)
        )
        wf.result = self._aggregate(wf)
        self._emit("workflow_finished", wf)
        self._save_state(wf)
        self._log_to_memory(wf)
        return self._finalize(wf)

    # ── Step execution with retry ───────────────────────────────────────

    def _run_step_with_retry(
        self,
        wf: Workflow,
        step: Step,
        context: dict,
        *,
        dry_run: bool,
    ) -> None:
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(timezone.utc).isoformat()
        self._emit("step_started", wf, step=step)

        last_error: str | None = None
        while step.attempts < step.max_attempts:
            step.attempts += 1
            try:
                out = self.executor.run(step, context, dry_run=dry_run)
                step.output = out or {}
                step.status = StepStatus.SKIPPED if dry_run else StepStatus.SUCCEEDED
                step.error = None
                ok, why = (
                    self.verifier.verify_step_output(step)
                    if not dry_run
                    else (True, "")
                )
                if not ok:
                    last_error = f"verifier: {why}"
                    step.status = StepStatus.FAILED
                    step.error = last_error
                    self._emit("step_verify_failed", wf, step=step)
                    if step.attempts < step.max_attempts:
                        step.status = StepStatus.RETRIED
                        time.sleep(0.5 * step.attempts)
                        continue
                    break
                break
            except Exception as exc:  # noqa: BLE001 — top-level guard
                last_error = f"{type(exc).__name__}: {exc}"
                step.error = last_error
                if self.verbose:
                    traceback.print_exc()
                if step.attempts < step.max_attempts:
                    step.status = StepStatus.RETRIED
                    self._emit("step_retry", wf, step=step)
                    time.sleep(0.5 * step.attempts)
                    continue
                step.status = StepStatus.FAILED
                break

        step.finished_at = datetime.now(timezone.utc).isoformat()
        self._emit("step_finished", wf, step=step)

    # ── Result aggregation ──────────────────────────────────────────────

    def _aggregate(self, wf: Workflow) -> dict:
        # Pick the most-downstream succeeded step's output as the "result"
        final: dict[str, Any] = {}
        for s in reversed(wf.steps):
            if s.status == StepStatus.SUCCEEDED and s.output:
                final = s.output
                break
        return {
            "final": final,
            "steps": {s.id: s.status.value for s in wf.steps},
        }

    # ── Logging + state ─────────────────────────────────────────────────

    def _emit(
        self,
        event: str,
        wf: Workflow,
        *,
        step: Step | None = None,
        extra: dict | None = None,
    ) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "workflow_id": wf.id,
            "workflow_name": wf.name,
            "workflow_status": wf.status.value,
            "env": self.env.label,
        }
        if step is not None:
            entry["step_id"] = step.id
            entry["step_type"] = step.type.value
            entry["step_status"] = step.status.value
            entry["attempts"] = step.attempts
            if step.error:
                entry["error"] = step.error
        if extra:
            entry.update(extra)
        try:
            with self._workflow_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            if self.verbose:
                print(f"[workflow] log write failed: {e}")
        if self.verbose:
            print(f"[workflow] {event} {entry.get('step_id', '')}".rstrip())

    def _save_state(self, wf: Workflow) -> None:
        try:
            p = self._state_dir / f"{wf.id}.json"
            p.write_text(json.dumps(wf.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            if self.verbose:
                print(f"[workflow] state save failed: {e}")

    def _log_to_memory(self, wf: Workflow) -> None:
        """Persist the final outcome to AgentMemory so future workflows can
        semantic-search prior runs. Non-blocking on failure.

        Skipped in sandbox mode — sandbox outcomes must not pollute the
        production memory store.
        """
        if wf.status == WorkflowStatus.DRY_RUN:
            return
        if not self.env.is_production:
            return
        try:
            from substrate.execution.runtime.agent_runtime import AgentResult
            from substrate.state.memory.memory import AgentMemory

            summary_bits = []
            for s in wf.steps:
                summary_bits.append(f"{s.id}:{s.status.value}")
            output_summary = (
                f"goal={wf.goal[:200]} | steps={','.join(summary_bits)} "
                f"| status={wf.status.value}"
            )
            ar = AgentResult(
                output=output_summary,
                model_used="workflow_engine",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used=f"workflow:{wf.name}",
            )
            AgentMemory().log(
                agent_result=ar,
                venture_id=None,
                input_summary=wf.goal[:300],
                agent="workflow_engine",
                task_type="workflow",
                lead_username=None,
            )
        except Exception as e:
            if self.verbose:
                print(f"[workflow] memory log failed: {e}")

    def _finalize(self, wf: Workflow) -> dict:
        wf.finished_at = datetime.now(timezone.utc).isoformat()
        return {
            "id": wf.id,
            "name": wf.name,
            "status": wf.status.value,
            "result": wf.result,
            "ok": wf.status in (WorkflowStatus.COMPLETED, WorkflowStatus.DRY_RUN),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 7. EXAMPLE WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def build_research_workflow(goal: str) -> Workflow:
    """Research a topic: graph-scan → summarize → classify confidence."""
    wf_id = _new_id("wf-research")
    steps = [
        Step(
            id="scan",
            type=StepType.RESEARCH,
            assigned_agent="researcher",
            input={
                "prompt": f"Research this question: {goal}",
                "graph_search": goal.split()[0] if goal else "eos",
            },
        ),
        Step(
            id="summarize",
            type=StepType.RESEARCH,
            assigned_agent="researcher",
            dependencies=["scan"],
            input={
                "prompt": (
                    "Given this prior research, write a 5-bullet summary.\n\n"
                    "Prior research: {scan.summary}\n"
                    "Graph hits: {scan.graph_hits}"
                ),
            },
        ),
        Step(
            id="confidence",
            type=StepType.DECISION,
            assigned_agent="researcher",
            dependencies=["summarize"],
            input={
                "prompt": (
                    "Rate your confidence in the following summary.\n\n"
                    "Summary: {summarize.summary}"
                ),
                "choices": ["high", "medium", "low"],
            },
        ),
    ]
    return Workflow(id=wf_id, name="research", goal=goal, steps=steps)


def build_content_workflow(goal: str) -> Workflow:
    """Content creation: outline → draft → polish."""
    wf_id = _new_id("wf-content")
    steps = [
        Step(
            id="outline",
            type=StepType.WRITE,
            assigned_agent="writer",
            input={
                "prompt": (f"Create a 3-bullet outline for this content goal: {goal}"),
                "system": "You are a brand-aligned content strategist. Bullet points only.",
            },
        ),
        Step(
            id="draft",
            type=StepType.WRITE,
            assigned_agent="writer",
            dependencies=["outline"],
            input={
                "prompt": (
                    "Write the full content now. Follow this outline exactly.\n\n"
                    "Outline:\n{outline.content}\n\nGoal: " + goal
                ),
                "system": (
                    "Bold, direct, authoritative voice. Tactical luxury aesthetic. "
                    "No hedging, no fluff, no emojis."
                ),
            },
        ),
        Step(
            id="polish",
            type=StepType.WRITE,
            assigned_agent="writer",
            dependencies=["draft"],
            input={
                "prompt": (
                    "Polish this draft. Cut 20% of words without losing meaning.\n\n"
                    "Draft:\n{draft.content}"
                ),
                "system": "Editor mode. Tighten, sharpen, ship.",
            },
        ),
    ]
    return Workflow(id=wf_id, name="content", goal=goal, steps=steps)


def build_refactor_workflow(goal: str, target_file: str = "") -> Workflow:
    """Code refactor: inspect graph → plan change → propose edit (dry-run safe).

    The EXECUTE step uses action_type=query_graph (risk=NONE) so the whole
    workflow can run without --approve. A real refactor would add EDIT_FILE
    steps behind an approval gate.
    """
    wf_id = _new_id("wf-refactor")
    target = target_file or "scripts/eos_status.py"
    steps = [
        Step(
            id="impact",
            type=StepType.EXECUTE,
            assigned_agent="executor",
            input={
                "action_type": "query_graph",
                "target": target,
                "payload": {"question": "dependents", "node": target},
                "reason": f"assess blast radius before refactor: {goal}",
            },
        ),
        Step(
            id="plan",
            type=StepType.RESEARCH,
            assigned_agent="researcher",
            dependencies=["impact"],
            input={
                "prompt": (
                    f"Plan a refactor of {target}. Goal: {goal}\n\n"
                    "Impact report: {impact.action_output}\n\n"
                    "Produce a numbered plan. Do not write code yet."
                ),
                "graph_search": target.split("/")[-1].split(".")[0],
            },
        ),
        Step(
            id="go_no_go",
            type=StepType.DECISION,
            assigned_agent="ceo",
            dependencies=["plan"],
            input={
                "prompt": (
                    "Review this refactor plan and decide whether to proceed.\n\n"
                    "Plan: {plan.summary}"
                ),
                "choices": ["go", "no-go"],
            },
        ),
    ]
    return Workflow(id=wf_id, name="refactor", goal=goal, steps=steps)


EXAMPLE_BUILDERS: dict[str, Callable[..., Workflow]] = {
    "research": build_research_workflow,
    "content": build_content_workflow,
    "refactor": build_refactor_workflow,
}


# ═══════════════════════════════════════════════════════════════════════════
# 8. CLI
# ═══════════════════════════════════════════════════════════════════════════


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="workflow_engine",
        description="EOS workflow engine — goal → plan → execute → log.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list example workflows + agents")
    p_list.set_defaults(cmd="list")

    p_run = sub.add_parser("run", help="run an example workflow")
    p_run.add_argument("name", choices=sorted(EXAMPLE_BUILDERS.keys()))
    p_run.add_argument("--goal", required=True, help="goal string for the workflow")
    p_run.add_argument(
        "--target", default="", help="refactor target file (refactor only)"
    )
    p_run.add_argument(
        "--dry-run", action="store_true", help="validate + plan; no side effects"
    )
    p_run.add_argument("-v", "--verbose", action="store_true")

    p_show = sub.add_parser("show", help="show a saved workflow state file")
    p_show.add_argument("workflow_id")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        engine = WorkflowEngine()
        print("Example workflows:")
        for n in sorted(EXAMPLE_BUILDERS.keys()):
            print(f"  - {n}")
        print("\nAgents:")
        for name in engine.registry.names():
            a = engine.registry.get(name)
            caps = ",".join(sorted(c.value for c in a.capabilities))
            print(f"  - {name:11s}  caps={caps}  task={a.model_task_type}")
        return 0

    if args.cmd == "show":
        p = WORKFLOW_STATE_DIR / f"{args.workflow_id}.json"
        if not p.exists():
            print(f"no such workflow state: {p}")
            return 1
        print(p.read_text())
        return 0

    # run
    engine = WorkflowEngine(verbose=args.verbose)
    builder = EXAMPLE_BUILDERS[args.name]
    if args.name == "refactor":
        wf = builder(args.goal, target_file=args.target)
    else:
        wf = builder(args.goal)

    result = engine.run_workflow(wf, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
