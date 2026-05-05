"""
Plan Executor — converts orchestration plans into real execution behavior.

Bridges the gap between the orchestration planning layer
(adaptive_orchestration_policy.py) and the task execution layer
(task_execution.py / pipeline_execution.py).

Execution modes:
  SINGLE_AGENT           → passthrough to existing execution (no change)
  SEQUENTIAL_PHASES      → phase-by-phase with checkpoint + compression
  PARALLEL_SUBAGENTS     → bounded concurrent fanout + merge
  PLANNER_EXECUTOR_VERIFIER → 3-pass chain (plan → execute → verify)
  HYBRID                 → parallel phases + sequential synthesis

V2 semantic layer (additive, with V1 fallback):
  - Semantic decomposition produces SubtaskSpecs with dependency DAGs
  - Role-shaped prompts replace generic sub-agent framing
  - Intelligent synthesis replaces naive concatenation
  - Bounded replanning on failure/weak output
  - Structure-aware summarization replaces truncation

Design rules (mirror substrate conventions):
  - Additive only — calls into existing execution, never replaces it.
  - Deterministic — mode dispatch is pure branching, no LLM in control flow.
  - Best-effort — failures captured and returned, never raised.
  - Traceable — every decision logged to orchestration_record.
  - V1 fallback — if any V2 component fails, V1 path still works.
"""

from __future__ import annotations

import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from umh.substrate.adaptive_orchestration_policy import (
    OrchestrationPlan,
    OrchestrationPhase,
    PreferredNode,
    ReasoningTier,
)
from umh.substrate.context_budget import OrchestrationMode
from umh.substrate.orchestration_record import (
    OrchestrationRecord,
    PhaseTransition,
    compress_for_next_phase,
    get_orchestration_store,
    record_phase_transition,
    summarize_phase_output,
)

# ─── V2 semantic layer imports (best-effort) ────────────────────────────────
# If any V2 module is unavailable, the executor falls back to V1 behavior.

_V2_AVAILABLE = False
try:
    from umh.substrate.semantic_planner import (
        SemanticTaskPlan,
        semantic_decompose,
    )
    from umh.substrate.result_synthesizer import (
        MergeStrategy as SynthMergeStrategy,
        synthesize_results,
    )
    from umh.substrate.replan_engine import (
        ReplanAction,
        ReplanContext,
        ReplanTrigger,
        assess_output_quality,
        build_retry_prompt,
        evaluate_replan,
    )
    from umh.substrate.smart_summarizer import (
        summarize_phase_output as smart_summarize,
        compress_for_next_phase as smart_compress,
    )
    from umh.substrate.role_shaping import (
        RoleAssignment,
        SubagentRole,
        assign_roles_to_phases,
        build_role_prompt,
        get_merge_order,
    )

    _V2_AVAILABLE = True
except ImportError as _v2_exc:
    pass  # V2 unavailable — V1 fallback used. Logged at first use.

_LOG_PREFIX = "[substrate.plan_executor]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "exec") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Execution Result ────────────────────────────────────────────────────────


class ExecutionOutcome(str, Enum):
    """Outcome of a plan execution."""

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"  # some phases succeeded, some failed
    FAILED = "failed"


@dataclass
class PhaseResult:
    """Result of a single phase execution."""

    phase_name: str
    status: str  # "succeeded" | "failed"
    output: str = ""
    error: Optional[str] = None
    duration_s: float = 0.0
    summary: str = ""  # compressed version for next phase
    node_used: str = ""  # which node executed this phase

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "status": self.status,
            "output_chars": len(self.output),
            "error": self.error,
            "duration_s": round(self.duration_s, 2),
            "summary_chars": len(self.summary),
            "node_used": self.node_used,
        }


@dataclass
class PlanExecutionResult:
    """Complete result of executing an orchestration plan."""

    execution_id: str = field(default_factory=lambda: _new_id("exec"))
    plan_mode: str = ""
    outcome: ExecutionOutcome = ExecutionOutcome.FAILED
    phases: list[PhaseResult] = field(default_factory=list)
    final_output: str = ""
    execution_path: str = ""  # human-readable path taken
    record_id: str = ""  # orchestration record ID
    started_at: str = field(default_factory=_utcnow)
    completed_at: str = ""
    duration_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_mode": self.plan_mode,
            "outcome": self.outcome.value,
            "phase_count": len(self.phases),
            "phases": [p.to_dict() for p in self.phases],
            "final_output_chars": len(self.final_output),
            "execution_path": self.execution_path,
            "record_id": self.record_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_s": round(self.duration_s, 2),
            "metadata": self.metadata,
        }


# ─── Node resolution ─────────────────────────────────────────────────────────


def _resolve_preferred_node(plan: OrchestrationPlan) -> str:
    """Map plan preferred_node to execution target string.

    Returns "local" or "vps" — compatible with existing routing.
    Falls back to "vps" if local is unavailable.
    """
    if plan.preferred_node == PreferredNode.LOCAL:
        try:
            from umh.substrate.node_controller import _is_local_node_online

            if _is_local_node_online():
                return "local"
        except Exception:
            pass
        return "vps"  # fallback
    return "vps"


def _resolve_node_for_phase(
    phase: OrchestrationPhase,
    plan: OrchestrationPlan,
) -> str:
    """Resolve which node a specific phase should execute on."""
    if phase.requires_local:
        try:
            from umh.substrate.node_controller import _is_local_node_online

            if _is_local_node_online():
                return "local"
        except Exception:
            pass
    return _resolve_preferred_node(plan)


# ─── Single-phase dispatch ────────────────────────────────────────────────────


def _dispatch_to_session(
    prompt: str,
    *,
    session_name: str = "dex_builder_main",
    target: str = "vps",
    max_polls: int = 60,
    poll_interval_s: float = 2.0,
) -> dict[str, Any]:
    """Dispatch a prompt to a Claude tmux session and wait for response.

    Wraps ask_session() with best-effort error handling.
    Returns dict with "ok", "reply_text", and metadata.
    """
    try:
        from umh.substrate.claude_session_bridge import ask_session

        result = ask_session(
            target,
            session_name,
            prompt,
            ensure=True,
            poll_interval_s=poll_interval_s,
            max_polls=max_polls,
        )
        return result
    except Exception as exc:
        _log(f"dispatch failed: {exc}")
        return {"ok": False, "reply_text": "", "error": str(exc)}


def _execute_single_phase(
    phase_text: str,
    phase_name: str,
    *,
    target: str = "vps",
    session_name: str = "dex_builder_main",
    context_prefix: str = "",
) -> PhaseResult:
    """Execute a single phase via Claude session dispatch.

    Args:
        phase_text: The prompt/task for this phase.
        phase_name: Human-readable phase name.
        target: Compute target ("local" or "vps").
        session_name: tmux session name.
        context_prefix: Optional context from previous phases.

    Returns:
        PhaseResult with output and status.
    """
    start = time.monotonic()

    # Build the dispatch prompt
    prompt_parts: list[str] = []
    if context_prefix:
        prompt_parts.append(f"[Context from prior phases]\n{context_prefix}\n")
    prompt_parts.append(phase_text)
    full_prompt = "\n".join(prompt_parts)

    result = _dispatch_to_session(
        full_prompt,
        session_name=session_name,
        target=target,
    )

    duration = time.monotonic() - start
    reply = result.get("reply_text", "")

    if result.get("ok"):
        return PhaseResult(
            phase_name=phase_name,
            status="succeeded",
            output=reply,
            duration_s=duration,
            node_used=target,
        )
    else:
        return PhaseResult(
            phase_name=phase_name,
            status="failed",
            output=reply,
            error=result.get("error", "dispatch returned ok=False"),
            duration_s=duration,
            node_used=target,
        )


# ─── Phase text splitting ────────────────────────────────────────────────────


def _split_task_into_phases(
    task_text: str,
    plan: OrchestrationPlan,
) -> list[str]:
    """Split task text into phase-sized chunks aligned with plan phases.

    V1 strategy:
    1. If plan has named phases, try to match them to task sections.
    2. If task has explicit phase/section markers, split on those.
    3. Fallback: chunk into roughly equal parts by paragraph.

    Returns a list of phase texts, one per plan phase.
    """
    import re

    phase_count = len(plan.phases)
    if phase_count <= 1:
        return [task_text]

    # Strategy 1: split on explicit phase/section markers
    # Look for "PHASE N", "Phase N", "== PHASE", "## Phase", numbered sections
    section_pattern = re.compile(
        r"(?:^|\n)(?:={3,}|#{2,}\s+|PHASE\s+\d+)", re.IGNORECASE
    )
    sections = section_pattern.split(task_text)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) >= phase_count:
        # Merge extras into last section if we have too many
        result = sections[: phase_count - 1]
        result.append("\n\n".join(sections[phase_count - 1 :]))
        return result

    # Strategy 2: split by double-newline paragraphs
    paragraphs = [p.strip() for p in task_text.split("\n\n") if p.strip()]
    if len(paragraphs) >= phase_count:
        # Distribute paragraphs across phases
        per_phase = max(1, len(paragraphs) // phase_count)
        result: list[str] = []
        for i in range(phase_count):
            start_idx = i * per_phase
            end_idx = start_idx + per_phase if i < phase_count - 1 else len(paragraphs)
            result.append("\n\n".join(paragraphs[start_idx:end_idx]))
        return result

    # Strategy 3: fallback — single chunk per phase (repeat task for each)
    # This is the degenerate case: plan says N phases but text isn't splittable.
    # Return the full task for phase 1 and empty strings for the rest.
    return [task_text] + [""] * (phase_count - 1)


# ─── Sequential execution ────────────────────────────────────────────────────


def execute_sequential_phases(
    task_text: str,
    plan: OrchestrationPlan,
    *,
    correlation_id: str = "",
    record_id: str = "",
) -> PlanExecutionResult:
    """Execute a plan as sequential phases with checkpoint + compression.

    For each phase:
    1. Optionally checkpoint task boundary
    2. Execute the phase via Claude session
    3. Summarize output if plan requires
    4. Compress context for next phase
    5. Append to cumulative result

    Args:
        task_text: Full task text.
        plan: OrchestrationPlan with phases.
        correlation_id: Workflow correlation.
        record_id: Orchestration record ID.

    Returns:
        PlanExecutionResult with all phase outputs merged.
    """
    _log(f"sequential execution: {len(plan.phases)} phases")

    # ── Session rhythm: emit TASK_START (additive, best-effort) ──────────
    try:
        from umh.substrate.session_rhythm import RhythmEvent, handle_rhythm_event

        handle_rhythm_event(
            RhythmEvent.TASK_START,
            {"task_text_chars": len(task_text), "phase_count": len(plan.phases)},
        )
    except Exception:
        pass  # rhythm unavailable — no effect on execution

    phase_texts = _split_task_into_phases(task_text, plan)
    all_phases: list[PhaseResult] = []
    carry_forward_context = ""
    execution_path_parts: list[str] = []

    for i, phase in enumerate(plan.phases):
        phase_text = phase_texts[i] if i < len(phase_texts) else ""
        if not phase_text and not phase.is_verifier:
            _log(f"  phase {i + 1}/{len(plan.phases)} '{phase.name}': skipped (empty)")
            continue

        # Resolve node for this phase
        target = _resolve_node_for_phase(phase, plan)

        # Build phase prompt
        if phase.is_verifier:
            # Verifier gets the accumulated output to check
            accumulated = "\n\n---\n\n".join(
                pr.output for pr in all_phases if pr.status == "succeeded"
            )
            phase_text = (
                f"Verify the following execution output for completeness, "
                f"contradictions, and missing sections:\n\n{accumulated}"
            )

        _log(
            f"  phase {i + 1}/{len(plan.phases)} '{phase.name}': "
            f"executing on {target} ({len(phase_text)} chars)"
        )

        # Execute
        phase_result = _execute_single_phase(
            phase_text,
            phase.name,
            target=target,
            context_prefix=carry_forward_context,
        )
        all_phases.append(phase_result)
        execution_path_parts.append(f"{phase.name}:{phase_result.status}:{target}")

        # Record phase transition
        if i < len(plan.phases) - 1:
            next_phase = plan.phases[i + 1]

            # V2: structure-aware summarization; V1 fallback: truncation
            if plan.require_summary_between_phases and phase_result.output:
                phase_result.summary = _smart_summarize_phase(
                    phase_result.output,
                    max_chars=2000,
                    phase_role=phase.name,
                )

            # Compress context for next phase
            carry_items: list[str] = []
            if phase_result.status == "succeeded":
                carry_items.append(f"Phase '{phase.name}' completed successfully")
            else:
                carry_items.append(f"Phase '{phase.name}' failed: {phase_result.error}")

            carry_forward_context = _smart_compress_for_next(
                phase_result.summary or phase_result.output,
                carry_forward=carry_items,
                max_chars=1500,
                phase_role=phase.name,
            )

            # Log transition
            record_phase_transition(
                PhaseTransition(
                    record_id=record_id,
                    from_phase=phase.name,
                    to_phase=next_phase.name,
                    summary=phase_result.summary,
                    carry_forward=carry_items,
                    checkpoint_created=plan.require_checkpoint_between_phases,
                )
            )

        # V2: check for replanning on failure or weak output
        if phase_result.status == "failed" and not phase.is_verifier:
            replan_decision = _try_replan(
                phase.name,
                phase_result,
                all_phases,
                plan,
                task_text,
                correlation_id=correlation_id,
            )
            if replan_decision is not None and replan_decision.get("action") == "retry":
                retry_result = _execute_single_phase(
                    replan_decision["retry_prompt"],
                    f"{phase.name}_retry",
                    target=target,
                    context_prefix=carry_forward_context,
                )
                all_phases.append(retry_result)
                execution_path_parts.append(
                    f"{phase.name}_retry:{retry_result.status}:{target}"
                )
                if retry_result.status == "succeeded":
                    phase_result = retry_result  # use retry result for carry-forward
                    _log(f"  phase '{phase.name}' retry succeeded")
                else:
                    _log(f"  phase '{phase.name}' retry also failed — stopping")
                    break
            elif (
                replan_decision is not None
                and replan_decision.get("action") == "continue"
            ):
                _log(f"  phase '{phase.name}' failed but replan says continue")
            else:
                _log(f"  phase '{phase.name}' failed — stopping sequential execution")
                break

    # V2: intelligent synthesis; V1 fallback: naive concatenation
    final_output = _synthesize_final_output(all_phases, plan)

    # Determine outcome
    failed = [pr for pr in all_phases if pr.status == "failed"]
    if not failed:
        outcome = ExecutionOutcome.SUCCEEDED
    elif len(failed) < len(all_phases):
        outcome = ExecutionOutcome.PARTIAL
    else:
        outcome = ExecutionOutcome.FAILED

    # ── Session rhythm: emit TASK_COMPLETE (additive, best-effort) ─────────
    try:
        from umh.substrate.session_rhythm import RhythmEvent, handle_rhythm_event

        handle_rhythm_event(
            RhythmEvent.TASK_COMPLETE,
            {
                "outcome": outcome.value,
                "phase_count": len(all_phases),
                "failed_count": len(failed),
            },
        )
    except Exception:
        pass  # rhythm unavailable — no effect on execution

    return PlanExecutionResult(
        plan_mode=plan.mode.value,
        outcome=outcome,
        phases=all_phases,
        final_output=final_output,
        execution_path=" → ".join(execution_path_parts),
        record_id=record_id,
    )


# ─── Parallel execution ──────────────────────────────────────────────────────


def _build_subagent_prompt(
    task_text: str,
    phase: OrchestrationPhase,
    index: int,
    total: int,
    *,
    role_assignment: Any = None,
    context_prefix: str = "",
) -> str:
    """Build a self-contained prompt for a parallel sub-agent.

    V2: if a RoleAssignment is available, uses role-shaped prompts
    with structured output expectations.

    V1 fallback: generic sub-agent framing.

    Each sub-agent gets the full task context plus its specific
    phase assignment, so it can operate independently.
    """
    # V2: role-shaped prompt
    if _V2_AVAILABLE and role_assignment is not None:
        try:
            return build_role_prompt(role_assignment, task_text, context_prefix)
        except Exception as exc:
            _log(f"role prompt build failed, using V1 fallback: {exc}")

    # V1: generic framing
    return (
        f"You are sub-agent {index + 1} of {total}, assigned to: "
        f"'{phase.name}' — {phase.description}\n\n"
        f"Full task context:\n{task_text}\n\n"
        f"Focus on your assigned scope. Be thorough but concise. "
        f"Output your findings in a structured format."
    )


def execute_parallel_subagents(
    task_text: str,
    plan: OrchestrationPlan,
    *,
    correlation_id: str = "",
    record_id: str = "",
) -> PlanExecutionResult:
    """Execute independent subtasks via bounded concurrent sub-agents.

    Steps:
    1. Create N sub-prompts from plan phases.
    2. Dispatch concurrently via ThreadPoolExecutor (bounded by plan.max_subagents).
    3. Collect results.
    4. Merge with structure.

    Args:
        task_text: Full task text.
        plan: OrchestrationPlan with phases and subagent config.
        correlation_id: Workflow correlation.
        record_id: Orchestration record ID.

    Returns:
        PlanExecutionResult with merged outputs.
    """
    max_agents = max(1, plan.max_subagents)
    phases = [p for p in plan.phases if not p.is_verifier]
    verifier_phases = [p for p in plan.phases if p.is_verifier]

    _log(f"parallel execution: {len(phases)} sub-agents (max concurrent={max_agents})")

    # Build sub-prompts
    prompts: list[tuple[str, OrchestrationPhase, int]] = []
    for i, phase in enumerate(phases):
        prompt = _build_subagent_prompt(task_text, phase, i, len(phases))
        prompts.append((prompt, phase, i))

    # Execute concurrently
    all_results: list[PhaseResult] = [
        PhaseResult(phase_name="", status="failed")
    ] * len(prompts)

    def _run_subagent(
        idx: int, prompt: str, phase: OrchestrationPhase
    ) -> tuple[int, PhaseResult]:
        target = _resolve_node_for_phase(phase, plan)
        # Each sub-agent gets a unique session to avoid contention
        session_name = f"dex_subagent_{idx}"
        result = _execute_single_phase(
            prompt,
            phase.name,
            target=target,
            session_name=session_name,
        )
        return idx, result

    with ThreadPoolExecutor(max_workers=max_agents) as executor:
        futures = {
            executor.submit(_run_subagent, idx, prompt, phase): idx
            for prompt, phase, idx in prompts
        }

        for future in as_completed(futures):
            try:
                idx, result = future.result()
                all_results[idx] = result
                _log(
                    f"  sub-agent {idx + 1}/{len(prompts)}: "
                    f"{result.status} ({result.duration_s:.1f}s)"
                )
            except Exception as exc:
                idx = futures[future]
                _log(f"  sub-agent {idx + 1}/{len(prompts)}: exception {exc}")
                all_results[idx] = PhaseResult(
                    phase_name=f"subagent_{idx}",
                    status="failed",
                    error=str(exc),
                )

    # Run verifier if required
    if verifier_phases and plan.require_verifier:
        accumulated = "\n\n---\n\n".join(
            f"[Sub-agent: {r.phase_name}]\n{r.output}"
            for r in all_results
            if r.status == "succeeded"
        )
        for vp in verifier_phases:
            verifier_prompt = (
                f"Verify the following parallel execution outputs for "
                f"completeness, contradictions, and gaps:\n\n{accumulated}"
            )
            verifier_result = _execute_single_phase(
                verifier_prompt,
                vp.name,
                target=_resolve_preferred_node(plan),
            )
            all_results.append(verifier_result)

    # V2: intelligent synthesis; V1 fallback: naive concatenation
    final_output = _synthesize_final_output(all_results, plan)

    # Determine outcome
    failed = [r for r in all_results if r.status == "failed"]
    if not failed:
        outcome = ExecutionOutcome.SUCCEEDED
    elif successful:
        outcome = ExecutionOutcome.PARTIAL
    else:
        outcome = ExecutionOutcome.FAILED

    execution_path = " | ".join(
        f"{r.phase_name}:{r.status}:{r.node_used}" for r in all_results
    )

    return PlanExecutionResult(
        plan_mode=plan.mode.value,
        outcome=outcome,
        phases=all_results,
        final_output=final_output,
        execution_path=f"parallel({len(phases)}) → {execution_path}",
        record_id=record_id,
    )


# ─── Planner / Executor / Verifier chain ─────────────────────────────────────


def execute_planner_executor_verifier(
    task_text: str,
    plan: OrchestrationPlan,
    *,
    correlation_id: str = "",
    record_id: str = "",
) -> PlanExecutionResult:
    """Execute the 3-pass planner → executor → verifier chain.

    Pass 1 (Planner): Produces a structured execution plan.
    Pass 2 (Executor): Executes based on the planner's output.
    Pass 3 (Verifier): Checks completeness and correctness.

    Args:
        task_text: Full task text.
        plan: OrchestrationPlan.
        correlation_id: Workflow correlation.
        record_id: Orchestration record ID.

    Returns:
        PlanExecutionResult with all three pass outputs.
    """
    _log("planner-executor-verifier chain: 3 passes")
    target = _resolve_preferred_node(plan)
    all_phases: list[PhaseResult] = []

    # ── Pass 1: Planner ──────────────────────────────────────────────
    planner_prompt = (
        f"You are the PLANNER in a planner-executor-verifier chain.\n\n"
        f"Task:\n{task_text}\n\n"
        f"Produce a structured execution plan with:\n"
        f"1. Clear numbered steps\n"
        f"2. Expected outputs for each step\n"
        f"3. Risk points to watch for\n"
        f"4. Success criteria\n\n"
        f"Output the plan in a structured format. Do NOT execute — only plan."
    )

    _log("  pass 1/3: planner")
    planner_result = _execute_single_phase(
        planner_prompt,
        "planner",
        target=target,
    )
    all_phases.append(planner_result)

    if planner_result.status == "failed":
        _log("  planner failed — aborting chain")
        return PlanExecutionResult(
            plan_mode=plan.mode.value,
            outcome=ExecutionOutcome.FAILED,
            phases=all_phases,
            final_output="",
            execution_path="planner:failed",
            record_id=record_id,
        )

    # Record transition
    record_phase_transition(
        PhaseTransition(
            record_id=record_id,
            from_phase="planner",
            to_phase="executor",
            summary=_smart_summarize_phase(
                planner_result.output, max_chars=2000, phase_role="planner"
            ),
            carry_forward=["Planner completed successfully"],
            checkpoint_created=True,
        )
    )

    # ── Pass 2: Executor ─────────────────────────────────────────────
    executor_prompt = (
        f"You are the EXECUTOR in a planner-executor-verifier chain.\n\n"
        f"Original task:\n{task_text}\n\n"
        f"Execution plan from planner:\n{planner_result.output}\n\n"
        f"Execute the plan step by step. Follow the planner's structure exactly. "
        f"Report what you did for each step."
    )

    _log("  pass 2/3: executor")
    executor_result = _execute_single_phase(
        executor_prompt,
        "executor",
        target=target,
    )
    all_phases.append(executor_result)

    if executor_result.status == "failed":
        _log("  executor failed — running verifier on partial output")

    # Record transition
    record_phase_transition(
        PhaseTransition(
            record_id=record_id,
            from_phase="executor",
            to_phase="verifier",
            summary=_smart_summarize_phase(
                executor_result.output, max_chars=2000, phase_role="executor"
            ),
            carry_forward=[
                f"Executor {'completed' if executor_result.status == 'succeeded' else 'failed'}"
            ],
            checkpoint_created=True,
        )
    )

    # ── Pass 3: Verifier ─────────────────────────────────────────────
    verifier_prompt = (
        f"You are the VERIFIER in a planner-executor-verifier chain.\n\n"
        f"Original task:\n{task_text}\n\n"
        f"Planner output:\n{planner_result.output}\n\n"
        f"Executor output:\n{executor_result.output}\n\n"
        f"Verify:\n"
        f"1. Completeness — did the executor address every step?\n"
        f"2. Correctness — are there contradictions or errors?\n"
        f"3. Missing sections — what was skipped?\n\n"
        f"Output a verification report with PASS/FAIL for each check, "
        f"and append any corrections needed."
    )

    _log("  pass 3/3: verifier")
    verifier_result = _execute_single_phase(
        verifier_prompt,
        "verifier",
        target=target,
    )
    all_phases.append(verifier_result)

    # V2: PEV-aware synthesis; V1 fallback: section-labeled concat
    final_output = _synthesize_final_output(all_phases, plan)

    # Determine outcome
    if executor_result.status == "failed":
        outcome = ExecutionOutcome.FAILED
    elif verifier_result.status == "failed":
        outcome = ExecutionOutcome.PARTIAL
    else:
        outcome = ExecutionOutcome.SUCCEEDED

    execution_path = " → ".join(f"{r.phase_name}:{r.status}" for r in all_phases)

    return PlanExecutionResult(
        plan_mode=plan.mode.value,
        outcome=outcome,
        phases=all_phases,
        final_output=final_output,
        execution_path=f"pev({execution_path})",
        record_id=record_id,
    )


# ─── Context pressure enforcement ────────────────────────────────────────────


def _enforce_context_pressure(
    plan: OrchestrationPlan,
) -> dict[str, Any]:
    """Apply context pressure rules before execution.

    Returns enforcement decisions that modify execution behavior.
    """
    enforcement: dict[str, Any] = {
        "checkpoint_forced": False,
        "fanout_reduced": False,
        "output_limits_applied": False,
        "original_max_subagents": plan.max_subagents,
        "effective_max_subagents": plan.max_subagents,
    }

    if plan.context_budget is None:
        return enforcement

    pressure = plan.context_budget.pressure.value

    if pressure in ("high", "critical"):
        enforcement["checkpoint_forced"] = True
        _log(f"pressure={pressure}: forcing checkpoint before execution")

    if pressure == "critical" and plan.use_parallelism:
        # Reduce fanout under critical pressure
        reduced = max(1, plan.max_subagents // 2)
        enforcement["fanout_reduced"] = True
        enforcement["effective_max_subagents"] = reduced
        _log(
            f"pressure=critical: reducing fanout from {plan.max_subagents} to {reduced}"
        )

    if pressure in ("high", "critical"):
        enforcement["output_limits_applied"] = True

    return enforcement


# ─── V2 integration helpers ──────────────────────────────────────────────────


def _smart_summarize_phase(
    output: str,
    *,
    max_chars: int = 2000,
    phase_role: str = "",
) -> str:
    """Summarize phase output using smart_summarizer if available, else V1.

    Returns a plain string (not SummaryResult) for backward compat.
    """
    if _V2_AVAILABLE:
        try:
            result = smart_summarize(output, max_chars=max_chars, phase_role=phase_role)
            return result.text
        except Exception as exc:
            _log(f"smart summarize failed, using V1: {exc}")
    return summarize_phase_output(output, max_chars=max_chars)


def _smart_compress_for_next(
    output: str,
    carry_forward: list[str] | None = None,
    *,
    max_chars: int = 1500,
    phase_role: str = "",
) -> str:
    """Compress phase output for next phase using smart_summarizer if available."""
    if _V2_AVAILABLE:
        try:
            return smart_compress(
                output,
                carry_forward_items=carry_forward,
                max_chars=max_chars,
                phase_role=phase_role,
            )
        except Exception as exc:
            _log(f"smart compress failed, using V1: {exc}")
    return compress_for_next_phase(output, carry_forward, max_chars=max_chars)


def _synthesize_final_output(
    phase_results: list[PhaseResult],
    plan: OrchestrationPlan,
) -> str:
    """Synthesize final output from phase results.

    V2: uses result_synthesizer for intelligent merge.
    V1 fallback: naive section-labeled concatenation.
    """
    if _V2_AVAILABLE:
        try:
            # Build result dicts for the synthesizer
            results = []
            for pr in phase_results:
                if pr.output:
                    results.append(
                        {
                            "source_id": pr.phase_name,
                            "role": pr.phase_name,  # maps to role in merge logic
                            "output_text": pr.output,
                            "status": pr.status,
                            "metadata": {
                                "duration_s": pr.duration_s,
                                "node": pr.node_used,
                            },
                        }
                    )
            if results:
                synthesis = synthesize_results(results, plan_mode=plan.mode.value)
                return synthesis.final_text
        except Exception as exc:
            _log(f"synthesis failed, using V1 merge: {exc}")

    # V1 fallback: naive concatenation
    parts: list[str] = []
    for pr in phase_results:
        if pr.output:
            parts.append(f"## {pr.phase_name}\n\n{pr.output}")
    return "\n\n---\n\n".join(parts)


def _try_replan(
    phase_name: str,
    phase_result: PhaseResult,
    all_phases: list[PhaseResult],
    plan: OrchestrationPlan,
    task_text: str,
    *,
    correlation_id: str = "",
) -> dict[str, Any] | None:
    """Attempt replanning after a phase failure.

    V2: uses replan_engine for bounded retry/revision decisions.
    V1: returns None (caller falls through to stop execution).

    Returns:
        dict with "action" key ("retry", "continue", "stop") and optional
        "retry_prompt" for retry actions. None if V2 unavailable.
    """
    if not _V2_AVAILABLE:
        return None

    try:
        # Build replan context from existing phase results
        ctx = ReplanContext()
        for pr in all_phases:
            if pr.phase_name.endswith("_retry"):
                # Track retries
                original = pr.phase_name.removesuffix("_retry")
                ctx.retry_counts[original] = ctx.retry_counts.get(original, 0) + 1
                ctx.total_retries_used += 1

        decision = evaluate_replan(
            ReplanTrigger.PHASE_FAILED,
            phase_name,
            {
                "status": phase_result.status,
                "error": phase_result.error,
                "output_chars": len(phase_result.output),
            },
            ctx,
        )

        _log(
            f"replan decision: action={decision.action.value} reason={decision.reason}"
        )

        if decision.action == ReplanAction.RETRY_SUBTASK:
            retry_prompt = build_retry_prompt(
                task_text,
                phase_result.error or "phase failed",
                decision.retry_count,
            )
            return {"action": "retry", "retry_prompt": retry_prompt}
        elif decision.action == ReplanAction.CONTINUE:
            return {"action": "continue"}
        else:
            # FAIL_TASK, ESCALATE, REVISE — stop for V1
            return {"action": "stop"}

    except Exception as exc:
        _log(f"replan evaluation failed: {exc}")
        return None


def _obtain_semantic_plan(
    task_text: str,
    plan: OrchestrationPlan,
) -> Any:
    """Attempt semantic decomposition for the task.

    Returns SemanticTaskPlan or None if V2 unavailable or decomposition fails.
    """
    if not _V2_AVAILABLE:
        return None

    try:
        ctx: dict[str, Any] = {}
        if plan.context_budget is not None:
            ctx["pressure"] = plan.context_budget.pressure.value

        semantic_plan = semantic_decompose(
            task_text,
            plan_mode=plan.mode.value,
            context=ctx,
        )

        # Only use the semantic plan if it produces more than one subtask
        if semantic_plan.subtask_count > 1:
            _log(
                f"semantic plan: {semantic_plan.subtask_count} subtasks, "
                f"merge={semantic_plan.merge_strategy.value}, "
                f"method={semantic_plan.decomposition_method}"
            )
            return semantic_plan
        return None

    except Exception as exc:
        _log(f"semantic decomposition failed (non-blocking): {exc}")
        return None


# ─── Main entry point ─────────────────────────────────────────────────────────


def execute_with_plan(
    task_text: str,
    plan: OrchestrationPlan,
    *,
    correlation_id: str = "",
    node_context: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> PlanExecutionResult:
    """Canonical execution entry point — routes to mode-specific executor.

    This is the single function that converts an OrchestrationPlan into
    real execution behavior. All task execution should flow through this
    when an orchestration plan is available.

    Args:
        task_text: The raw task text.
        plan: OrchestrationPlan from adaptive_orchestration_policy.
        correlation_id: Workflow-level correlation.
        node_context: Optional compute context overrides.
        dry_run: If True, log decisions but don't execute.

    Returns:
        PlanExecutionResult with execution outcome and all phase results.
    """
    mode = plan.mode
    _log(
        f"execute_with_plan: mode={mode.value} "
        f"phases={len(plan.phases)} "
        f"node={plan.preferred_node.value} "
        f"reasoning={plan.reasoning_tier.value}"
    )

    # Create orchestration record
    record = OrchestrationRecord.from_plan(
        plan,
        correlation_id=correlation_id,
        metadata={"executor": "plan_executor", "dry_run": dry_run},
    )
    record_id = get_orchestration_store().append(record)

    # V2: attempt semantic decomposition
    semantic_plan = _obtain_semantic_plan(task_text, plan)

    # Enforce context pressure
    enforcement = _enforce_context_pressure(plan)
    _log(f"enforcement: {enforcement}")

    # Dry run — return plan analysis without executing
    if dry_run:
        _log("dry_run=True — returning plan analysis without execution")
        dry_meta: dict[str, Any] = {
            "dry_run": True,
            "enforcement": enforcement,
            "plan": plan.to_dict(),
            "v2_available": _V2_AVAILABLE,
        }
        if semantic_plan is not None:
            dry_meta["semantic_plan_summary"] = {
                "subtask_count": semantic_plan.subtask_count,
                "merge_strategy": semantic_plan.merge_strategy.value,
                "has_parallel_work": semantic_plan.has_parallel_work,
                "verifier_required": semantic_plan.verifier_required,
                "decomposition_method": semantic_plan.decomposition_method,
            }
        return PlanExecutionResult(
            plan_mode=mode.value,
            outcome=ExecutionOutcome.SUCCEEDED,
            execution_path=f"dry_run:{mode.value}",
            record_id=record_id,
            metadata=dry_meta,
        )

    start_time = time.monotonic()

    # ── Session rhythm: apply mode hints to execution (additive) ─────────
    try:
        from umh.substrate.session_rhythm import get_combined_execution_hints

        rhythm_hints = get_combined_execution_hints()
        if rhythm_hints.get("prefer_sequential") and mode in (
            OrchestrationMode.PARALLEL_SUBAGENTS,
            OrchestrationMode.HYBRID,
        ):
            _log(
                f"rhythm override: {mode.value} → sequential_phases "
                f"(prefer_sequential=True, reason=work_mode)"
            )
            mode = OrchestrationMode.SEQUENTIAL_PHASES
            plan = plan  # keep plan phases but change execution mode
    except Exception:
        pass  # rhythm unavailable — use original mode

    # ── Mode dispatch ──────────────────────────────────────────────────
    result: PlanExecutionResult

    if mode == OrchestrationMode.SINGLE_AGENT:
        # Passthrough — execute as a single phase
        _log("mode=SINGLE_AGENT: passthrough execution")
        target = _resolve_preferred_node(plan)
        phase_result = _execute_single_phase(
            task_text,
            "execute",
            target=target,
        )
        result = PlanExecutionResult(
            plan_mode=mode.value,
            outcome=(
                ExecutionOutcome.SUCCEEDED
                if phase_result.status == "succeeded"
                else ExecutionOutcome.FAILED
            ),
            phases=[phase_result],
            final_output=phase_result.output,
            execution_path=f"single_agent:{phase_result.status}:{target}",
            record_id=record_id,
        )

    elif mode == OrchestrationMode.SEQUENTIAL_PHASES:
        result = execute_sequential_phases(
            task_text,
            plan,
            correlation_id=correlation_id,
            record_id=record_id,
        )

    elif mode == OrchestrationMode.PARALLEL_SUBAGENTS:
        result = execute_parallel_subagents(
            task_text,
            plan,
            correlation_id=correlation_id,
            record_id=record_id,
        )

    elif mode == OrchestrationMode.PLANNER_EXECUTOR_VERIFIER:
        result = execute_planner_executor_verifier(
            task_text,
            plan,
            correlation_id=correlation_id,
            record_id=record_id,
        )

    elif mode == OrchestrationMode.HYBRID:
        # V1 HYBRID: parallel execution of non-verifier phases,
        # then sequential verification
        _log("mode=HYBRID: parallel phases + sequential verify")
        result = execute_parallel_subagents(
            task_text,
            plan,
            correlation_id=correlation_id,
            record_id=record_id,
        )

    else:
        _log(f"unknown mode '{mode.value}' — falling back to single agent")
        target = _resolve_preferred_node(plan)
        phase_result = _execute_single_phase(task_text, "execute", target=target)
        result = PlanExecutionResult(
            plan_mode=mode.value,
            outcome=(
                ExecutionOutcome.SUCCEEDED
                if phase_result.status == "succeeded"
                else ExecutionOutcome.FAILED
            ),
            phases=[phase_result],
            final_output=phase_result.output,
            execution_path=f"fallback_single:{phase_result.status}",
            record_id=record_id,
        )

    # Finalize timing
    duration = time.monotonic() - start_time
    result.duration_s = duration
    result.completed_at = _utcnow()
    result.record_id = record_id
    result.metadata["enforcement"] = enforcement
    result.metadata["v2_available"] = _V2_AVAILABLE
    if semantic_plan is not None:
        result.metadata["semantic_plan_summary"] = {
            "subtask_count": semantic_plan.subtask_count,
            "merge_strategy": semantic_plan.merge_strategy.value,
            "has_parallel_work": semantic_plan.has_parallel_work,
            "verifier_required": semantic_plan.verifier_required,
            "decomposition_method": semantic_plan.decomposition_method,
        }

    # Update orchestration record with execution trace (V1 + V2)
    execution_trace: dict[str, Any] = {
        "phases_executed": len(result.phases),
        "phases_succeeded": sum(1 for p in result.phases if p.status == "succeeded"),
        "phases_failed": sum(1 for p in result.phases if p.status == "failed"),
        "retries_used": sum(
            1 for p in result.phases if p.phase_name.endswith("_retry")
        ),
        "subagents_spawned": (
            len([p for p in result.phases if not p.phase_name.startswith("verify")])
            if mode == OrchestrationMode.PARALLEL_SUBAGENTS
            else 0
        ),
        "summaries_created": sum(1 for p in result.phases if p.summary),
        "compression_applied": plan.require_summary_between_phases,
        "duration_s": round(duration, 2),
        "outcome": result.outcome.value,
        "nodes_used": list(set(p.node_used for p in result.phases if p.node_used)),
        "phase_results": [p.to_dict() for p in result.phases],
        "v2_available": _V2_AVAILABLE,
        "v2_semantic_plan": (
            semantic_plan.to_dict() if semantic_plan is not None else None
        ),
    }
    get_orchestration_store().mark_completed(
        record_id,
        execution_path=result.execution_path,
        execution_trace=execution_trace,
    )

    _log(
        f"execution complete: mode={mode.value} "
        f"outcome={result.outcome.value} "
        f"duration={duration:.1f}s "
        f"phases={len(result.phases)}"
    )

    return result


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "ExecutionOutcome",
    "PhaseResult",
    "PlanExecutionResult",
    "execute_with_plan",
    "execute_sequential_phases",
    "execute_parallel_subagents",
    "execute_planner_executor_verifier",
]
