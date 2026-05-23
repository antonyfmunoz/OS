"""
Capability-aware task routing — deterministic target selection.

Maps tasks to execution targets based on content analysis and session state.
No LLM calls. No network calls. Pure keyword heuristics + session context.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Deterministic — regex keyword matching, zero LLM cost.
- Best-effort — routing failures return safe defaults, never raise.
- Bounded — fixed enum sets, no unbounded state.
"""

from __future__ import annotations

import re
import sys
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from substrate.execution.transport.operator_session import OperatorSession
    from substrate.execution.transport.task_system import Task


# ─── Enums ───────────────────────────────────────────────────────────────────


class TaskCapability(str, Enum):
    """What a task needs from its execution environment."""

    LIGHTWEIGHT_REASONING = "lightweight_reasoning"
    HEAVY_REASONING = "heavy_reasoning"
    LOCAL_COMPUTE = "local_compute"
    VPS_COMPUTE = "vps_compute"
    PRODUCT_CONTEXT = "product_context"
    BUILDER_CONTEXT = "builder_context"


class ExecutionTarget(str, Enum):
    """Where a task should execute."""

    LOCAL_PRODUCT = "local_product"
    LOCAL_BUILDER = "local_builder"
    VPS_PRODUCT = "vps_product"
    VPS_BUILDER = "vps_builder"


# ─── Constants ───────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.capability_routing] {msg}", file=sys.stderr)


# Builder-context keywords: development / infrastructure work
_BUILDER_RE = re.compile(
    r"\b(build|builder|code|debug|fix|patch|repo|script|deploy|refactor"
    r"|test|migration|schema|infra|docker|tmux|service|daemon|api"
    r"|endpoint|module|class|function|import)\b",
    re.IGNORECASE,
)

# Heavy compute / local-preference keywords
_HEAVY_RE = re.compile(
    r"\b(model|local|gpu|heavy|train|fine.?tune|embedding|vector"
    r"|compute|render|compile|transcode)\b",
    re.IGNORECASE,
)


# ─── Capability Inference ────────────────────────────────────────────────────


def infer_task_capabilities(task: "Task") -> set[TaskCapability]:
    """Infer required capabilities from task text. Deterministic keyword matching.

    Rules:
    - Builder keywords → BUILDER_CONTEXT, else → PRODUCT_CONTEXT
    - Heavy/local keywords → LOCAL_COMPUTE + HEAVY_REASONING
    - Otherwise → LIGHTWEIGHT_REASONING
    - Autonomous tasks without local-specific keywords → VPS_COMPUTE allowed
    """
    from substrate.execution.transport.task_system import TaskExecutionPolicy

    text = f"{task.title} {task.description or ''}"
    caps: set[TaskCapability] = set()

    # Context classification
    if _BUILDER_RE.search(text):
        caps.add(TaskCapability.BUILDER_CONTEXT)
    else:
        caps.add(TaskCapability.PRODUCT_CONTEXT)

    # Compute weight classification
    if _HEAVY_RE.search(text):
        caps.add(TaskCapability.LOCAL_COMPUTE)
        caps.add(TaskCapability.HEAVY_REASONING)
    else:
        caps.add(TaskCapability.LIGHTWEIGHT_REASONING)

    # VPS eligibility for autonomous tasks without local-specific needs
    if (
        task.execution_policy == TaskExecutionPolicy.AUTONOMOUS
        and TaskCapability.LOCAL_COMPUTE not in caps
    ):
        caps.add(TaskCapability.VPS_COMPUTE)

    return caps


# ─── Target Selection ────────────────────────────────────────────────────────


def choose_execution_target(
    task: "Task",
    session: Optional["OperatorSession"] = None,
    local_available: bool = False,
) -> ExecutionTarget:
    """Choose the best execution target for a task.

    Resolution order:
    1. Infer capabilities from task text.
    2. Determine context lane (builder vs product).
    3. Determine node (local vs vps) based on:
       - session.node_preference (if set and not "auto")
       - local_available + task needs local compute → local
       - otherwise → vps
    4. Combine context + node → ExecutionTarget.

    Always returns a valid target. Never raises.
    """
    caps = infer_task_capabilities(task)

    # Context lane
    is_builder = TaskCapability.BUILDER_CONTEXT in caps

    # Node preference from session
    node_pref = "auto"
    if session is not None:
        node_pref = session.node_preference or "auto"

    # Node selection
    needs_local = TaskCapability.LOCAL_COMPUTE in caps
    use_local = False

    if node_pref == "local":
        # Operator explicitly prefers local
        use_local = local_available
    elif node_pref == "vps":
        # Operator explicitly prefers VPS — only override for hard local needs
        use_local = needs_local and local_available
    else:
        # Auto — use local if needed and available, otherwise VPS
        use_local = needs_local and local_available

    # Combine
    if is_builder:
        return (
            ExecutionTarget.LOCAL_BUILDER if use_local else ExecutionTarget.VPS_BUILDER
        )
    else:
        return (
            ExecutionTarget.LOCAL_PRODUCT if use_local else ExecutionTarget.VPS_PRODUCT
        )


# ─── Routing Metadata ────────────────────────────────────────────────────────


def route_task(
    task: "Task",
    session: Optional["OperatorSession"] = None,
    local_available: bool = False,
) -> "Task":
    """Attach routing metadata to a task. Mutates and returns the task.

    Sets:
    - task.required_capabilities
    - task.chosen_target
    - task.routing_reason
    """
    caps = infer_task_capabilities(task)
    target = choose_execution_target(task, session, local_available)

    task.required_capabilities = [c.value for c in sorted(caps, key=lambda c: c.value)]
    task.chosen_target = target.value
    task.routing_reason = _build_reason(caps, target, session, local_available)

    _log(f"routed {task.task_id} → {target.value} ({task.routing_reason})")
    return task


def _build_reason(
    caps: set[TaskCapability],
    target: ExecutionTarget,
    session: Optional["OperatorSession"],
    local_available: bool,
) -> str:
    """Build a human-readable routing reason string."""
    parts: list[str] = []

    if TaskCapability.BUILDER_CONTEXT in caps:
        parts.append("builder_context")
    else:
        parts.append("product_context")

    if TaskCapability.HEAVY_REASONING in caps:
        parts.append("heavy_compute")
    else:
        parts.append("lightweight")

    node_pref = "auto"
    if session is not None:
        node_pref = session.node_preference or "auto"
    parts.append(f"node_pref={node_pref}")
    parts.append(f"local={'up' if local_available else 'down'}")

    return f"{target.value} ← {', '.join(parts)}"


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "TaskCapability",
    "ExecutionTarget",
    "infer_task_capabilities",
    "choose_execution_target",
    "route_task",
]
