"""
Unified post-generation commit pipeline for winning responses.

Every response that is selected as the final output — whether from
ExecutionSpine's single-path flow or multi_strategy's winner selection —
must pass through ``commit_winner()`` exactly once.  This is the single
canonical implementation of stages 6–10.

Stages:
    6a. ConversationMemory — write user + assistant messages
    6b. AgentMemory        — log interaction (output, model, tokens)
    7.  Knowledge integration
    8.  Feedback logging
    9.  World model update (signal-attributed)
    9b. Reflection logging  (multi-iteration insight)
    10. Session persistence

Design constraints:
    - Explicit parameters only — no hidden state, no caller locals.
    - Stateless — safe to call from both ExecutionSpine and multi_strategy.
    - Side-effect boundary: only the winning response reaches this function.
      Rejected candidates must never call it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_log = logging.getLogger(__name__)


def commit_winner(
    *,
    message: str,
    response: str,
    ctx: object,
    agent_type: str,
    session_id: str | None,
    channel_id: str | None,
    org_id: str | None,
    task_type: object | None,
    venture_id: str | None,
    skill_name: str | None,
    evaluation: dict | None,
    world_model_signal: object | None,
    model_used: str,
    tokens_used: dict | int,
    iterations: int,
) -> None:
    """Run all post-generation persistence stages for a committed response.

    Parameters
    ----------
    message : str
        Original user message.
    response : str
        Final LLM output selected as the winner.
    ctx : object
        Runtime context (from ``load_context_from_env``).
    agent_type : str
        Agent that produced the response.
    session_id : str | None
        Session identifier for conversation tracking.
    channel_id : str | None
        Channel for session persistence key.
    org_id : str | None
        Organization ID — gates world model writes.
    task_type : object | None
        Task classification (may be enum or string).
    venture_id : str | None
        Venture scope for memory and feedback.
    skill_name : str | None
        Skill used during generation, if any.
    evaluation : dict | None
        Outcome evaluation dict (quality_score, confidence, flags).
    world_model_signal : object | None
        Pre-gated signal from ``route_signals()``.  If provided, the
        world model stage uses the attributed path.  If None, falls
        back to evaluation-based gating.
    model_used : str
        Model that generated the response.
    tokens_used : dict | int
        Token counts (dict with input/output/total, or int total).
    iterations : int
        Number of generation iterations (1 = single pass).
    """

    _task_type_str = str(task_type) if task_type else "unknown"

    # ── 6a. ConversationMemory ───────────────────────────────────────────
    try:
        from umh.runtime_engine.memory import ConversationMemory

        cm = ConversationMemory(ctx)
        cm.store(
            session_id=session_id or "",
            role="user",
            content=message[:10000],
            channel=channel_id or "unknown",
            agent=agent_type,
        )
        cm.store(
            session_id=session_id or "",
            role="assistant",
            content=response[:10000],
            channel=channel_id or "unknown",
            agent=agent_type,
        )
    except Exception as e:
        _log.warning("ConversationMemory write FAILED: %s", e)

    # ── 6b. AgentMemory ──────────────────────────────────────────────────
    try:
        from umh.runtime_engine.memory import AgentMemory
        from umh.runtime_engine.agent_runtime import AgentResult

        _agent_result = AgentResult(
            output=response[:2000],
            model_used=model_used,
            tokens_used=tokens_used,
            skill_used=skill_name,
        )
        mem = AgentMemory()
        mem.log(
            agent_result=_agent_result,
            venture_id=venture_id,
            input_summary=message[:2000],
            agent=agent_type,
            task_type=_task_type_str,
        )
    except Exception as e:
        _log.warning("AgentMemory write FAILED: %s", e)

    # ── 7. Knowledge integration ─────────────────────────────────────────
    from umh.stages.commit import integrate_knowledge

    integrate_knowledge(
        message,
        response,
        ctx,
        agent=agent_type,
        task_type=_task_type_str,
    )

    # ── 8. Feedback logging ──────────────────────────────────────────────
    from umh.stages.commit import log_feedback

    log_feedback(
        message,
        response,
        ctx,
        venture_id=venture_id or "",
        evaluation=evaluation,
    )

    # ── 9. World model update (signal-attributed) ────────────────────────
    if org_id:
        from umh.stages.commit import update_world_model

        update_world_model(
            message,
            response,
            org_id,
            evaluation=evaluation,
            world_model_signal=world_model_signal,
        )

    # ── 9b. Reflection logging ───────────────────────────────────────────
    from umh.stages.commit import log_reflection

    log_reflection(message, iterations, agent_type, ctx)

    # ── 10. Session persistence ──────────────────────────────────────────
    if channel_id:
        try:
            from umh.substrate.storage import get_storage

            store = get_storage()
            store.put(f"session:{channel_id}", session_id)
        except Exception as e:
            _log.debug("Session persistence skipped: %s", e)
