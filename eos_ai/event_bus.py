"""
EventBus — reactive coordination layer for EOS agents.

Decouples event producers (icp_scorer, dm_monitor, calendly_webhook) from
consumers (agents, orchestrator, memory). Any component can publish a business
event; registered handlers fire synchronously or in a background thread.

All events are persisted to Neon → events table for audit and replay.

Usage:
    from eos_ai.event_bus import EventBus, EventRegistry

    bus = EventBus()                         # singleton
    EventRegistry(bus).register_defaults()   # wire standard handlers

    bus.publish('new_lead', {
        'username': 'johndoe',
        'score': 8,
        'state': 'Frustrated Drifter',
        'venture_id': 'lyfe_institute',
    })
"""

import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable

import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.db import get_conn, ORG_ID


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Supported event types ────────────────────────────────────────────────────

EVENT_TYPES = frozenset(
    {
        "new_lead",  # → sales.icp_qualifier
        "lead_replied",  # → sales.objection_handler
        "lead_booked",  # log outcome + notify orchestrator
        "lead_closed",  # log outcome + run profile update
        "lead_lost",  # log outcome + log objection data
        "signal_captured",  # → research.signal_analyzer
        "content_needed",  # → content.hook_generator
        "morning_cycle",  # → orchestrator.run_morning_cycle
        "skill_threshold",  # → skill_improvement.check_and_improve
        "goal_activated",  # → goal state change: now producing tasks
        "goal_deferred",  # → goal state change: paused, no tasks
        "goal_completed",  # → goal state change: terminal
        "goal_dropped",  # → goal state change: terminal
        "goal_blocked",  # → goal state change: waiting on dependency
        "goal_selection_cycle",  # → selection cycle completed
        "goal_task_completed",  # → task succeeded → update goal performance
        "goal_task_failed",  # → task failed → update goal performance
        "goal_swap_triggered",  # → deferred goal replaced active (9F swap pressure)
        "goal_opportunity_penalty",  # → active goal penalized by opportunity cost (9F)
        "goal_executed",  # → goal execution completed (11A execution loop)
        "goal_priority_decayed",  # → priority decay applied after sustained failure (9H)
    }
)


# ─── EventBus (singleton) ────────────────────────────────────────────────────


class EventBus:
    """
    Singleton event bus. Use EventBus() anywhere — always returns the same
    instance. Thread-safe.
    """

    _instance: "EventBus | None" = None
    _class_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "EventBus":
        with cls._class_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._handlers: dict[str, list[Callable]] = {}
                cls._instance = instance
        return cls._instance

    def _log_event(
        self,
        event_type: str,
        payload: dict,
        handled_by: list[str],
    ) -> str:
        try:
            with get_conn(ORG_ID) as cur:
                cur.execute(
                    """
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (ORG_ID, event_type, json.dumps(payload), json.dumps(handled_by)),
                )
                return str(cur.fetchone()["id"])
        except Exception as e:
            print(f"[EventBus] _log_event failed: {e}")
            return ""

    # ─── Subscribe ────────────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler_fn: Callable) -> None:
        """
        Register a handler for an event type.
        Multiple handlers per event type are supported — all will fire in
        registration order.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler_fn)
        handler_name = getattr(handler_fn, "__name__", repr(handler_fn))
        print(f"[EventBus] subscribed: {event_type} → {handler_name}")

    # ─── Publish (blocking) ───────────────────────────────────────────────────

    def publish(self, event_type: str, payload: dict) -> list[Any]:
        """
        Fire all handlers for this event type synchronously.
        Persists the event to memory.db regardless of handler count.
        Returns list of results from each handler.
        """
        handlers = self._handlers.get(event_type, [])
        results: list[Any] = []
        handled_by: list[str] = []

        for handler in handlers:
            handler_name = getattr(handler, "__name__", repr(handler))
            try:
                result = handler(payload)
                results.append(result)
                handled_by.append(handler_name)
                print(f"[EventBus] {event_type} → {handler_name} OK")
            except Exception as exc:
                label = f"{handler_name}:ERROR:{exc}"
                handled_by.append(label)
                print(f"[EventBus] {event_type} → {handler_name} FAILED: {exc}")

        self._log_event(event_type, payload, handled_by)

        if not handlers:
            print(f"[EventBus] {event_type} published — no handlers registered")

        return results

    # ─── Publish (non-blocking) ───────────────────────────────────────────────

    def publish_async(self, event_type: str, payload: dict) -> None:
        """
        Fire all handlers in a background daemon thread.
        Returns immediately — caller is never blocked.
        """
        thread = threading.Thread(
            target=self.publish,
            args=(event_type, payload),
            daemon=True,
            name=f"eventbus-{event_type}",
        )
        thread.start()


# ─── Default handlers ─────────────────────────────────────────────────────────


def _handle_new_lead(payload: dict) -> dict:
    """
    new_lead → run icp_qualifier skill.
    Generates a personalized outreach strategy for the lead.
    Logs the result to memory.db via AgentRuntime.
    """
    from eos_ai.agent_runtime import AgentRuntime, TaskType

    username = payload.get("username", "unknown")
    score = payload.get("score", 0)
    state = payload.get("state", "unknown")
    venture_id = payload.get("venture_id", "lyfe_institute")

    runtime = AgentRuntime()
    prompt = (
        f"New qualified lead: @{username}\n"
        f"ICP Score: {score}/10\n"
        f"Psychological State: {state}\n\n"
        f"Generate a personalized outreach strategy:\n"
        f"1. Recommended opener approach (1 sentence)\n"
        f"2. Key pain angle to address\n"
        f"3. Conversation goal for first reply"
    )
    result = runtime.run(
        task_type=TaskType.GENERATE,
        prompt=prompt,
        venture_id=venture_id,
        skill_name="icp_qualifier",
        max_tokens=400,
        agent="sales.icp_qualifier",
    )
    print(f"[EventBus:new_lead] @{username} — outreach strategy generated")
    return {
        "username": username,
        "interaction_id": result.interaction_id,
        "strategy_preview": result.output[:200],
    }


def _handle_lead_replied(payload: dict) -> dict:
    """
    lead_replied → run objection_handler skill.
    Analyzes the reply and returns the best next response.
    """
    from eos_ai.agent_runtime import AgentRuntime, TaskType

    username = payload.get("username", "unknown")
    message = payload.get("message", "")
    interaction_id = payload.get("interaction_id")
    venture_id = payload.get("venture_id", "lyfe_institute")

    runtime = AgentRuntime()
    prompt = (
        f"Lead @{username} replied:\n\n"
        f'"{message}"\n\n'
        f"Analyze the reply:\n"
        f"1. Conversation stage (Cold/Engaged/Diagnosing/Qualifying/Booked)\n"
        f"2. Objection or resistance detected (if any)\n"
        f"3. Single best next response (1-3 sentences)"
    )
    result = runtime.run(
        task_type=TaskType.GENERATE,
        prompt=prompt,
        venture_id=venture_id,
        skill_name="objection_handler",
        max_tokens=400,
        agent="sales.objection_handler",
        system_extra=f"Interaction ID context: {interaction_id}" if interaction_id else None,
    )
    print(f"[EventBus:lead_replied] @{username} — objection handler ran")
    return {
        "username": username,
        "interaction_id": result.interaction_id,
        "response_preview": result.output[:200],
    }


def _handle_lead_booked(payload: dict) -> dict:
    """
    lead_booked → log 'booked' outcome to memory.db + notify orchestrator.
    """
    from eos_ai.memory import AgentMemory

    username = payload.get("username", "unknown")
    booking_time = payload.get("booking_time", "")
    venture_id = payload.get("venture_id", "lyfe_institute")

    mem = AgentMemory()
    row = mem.get_interaction_for_lead(username, venture_id=venture_id)
    if row:
        outcome_id = mem.log_outcome(
            row["id"],
            outcome_type="booked",
            score=1.0,
            notes=f"event_bus:lead_booked — {booking_time}",
        )
        print(f"[EventBus:lead_booked] @{username} — outcome logged (id={outcome_id})")
        return {"username": username, "outcome_id": outcome_id, "interaction_id": row["id"]}
    else:
        orphan_id = mem.log_orphaned_reply(
            username,
            outcome_type="booked",
            score=1.0,
            notes=f"event_bus:lead_booked — {booking_time} — no prior interaction",
        )
        print(f"[EventBus:lead_booked] @{username} — logged as orphan (id={orphan_id})")
        return {"username": username, "orphan_id": orphan_id}


def _handle_lead_closed(payload: dict) -> dict:
    """
    lead_closed → log 'closed' outcome + run human profile update.
    """
    from eos_ai.memory import AgentMemory

    username = payload.get("username", "unknown")
    venture_id = payload.get("venture_id", "lyfe_institute")

    mem = AgentMemory()
    row = mem.get_interaction_for_lead(username, venture_id=venture_id)
    if row:
        outcome_id = mem.log_outcome(
            row["id"],
            outcome_type="closed",
            score=1.0,
            notes="event_bus:lead_closed",
        )
        print(f"[EventBus:lead_closed] @{username} — outcome logged (id={outcome_id})")
    else:
        outcome_id = None
        mem.log_orphaned_reply(
            username,
            outcome_type="closed",
            score=1.0,
            notes="event_bus:lead_closed — no prior interaction",
        )
        print(f"[EventBus:lead_closed] @{username} — logged as orphan")

    # Run human profile update
    try:
        from eos_ai.human_intelligence import HumanIntelligenceEngine
        from eos_ai.context import load_context_from_env

        engine = HumanIntelligenceEngine(load_context_from_env())
        profiles = engine.run_profile_cycle()
        print(f"[EventBus:lead_closed] profile cycle: {profiles}")
    except Exception as e:
        print(f"[EventBus:lead_closed] profile update skipped: {e}")

    return {"username": username, "outcome_id": outcome_id}


def _handle_lead_lost(payload: dict) -> dict:
    """
    lead_lost → log 'no_reply' outcome + store objection data for RLHF.
    """
    from eos_ai.memory import AgentMemory

    username = payload.get("username", "unknown")
    objection = payload.get("objection", "")
    venture_id = payload.get("venture_id", "lyfe_institute")

    mem = AgentMemory()
    notes = f"event_bus:lead_lost"
    if objection:
        notes += f" — objection: {objection}"

    row = mem.get_interaction_for_lead(username, venture_id=venture_id)
    if row:
        outcome_id = mem.log_outcome(
            row["id"],
            outcome_type="no_reply",
            score=0.0,
            notes=notes,
        )
        print(f"[EventBus:lead_lost] @{username} — outcome logged (id={outcome_id})")
        return {"username": username, "outcome_id": outcome_id}
    else:
        orphan_id = mem.log_orphaned_reply(
            username, outcome_type="no_reply", score=0.0, notes=notes
        )
        print(f"[EventBus:lead_lost] @{username} — logged as orphan (id={orphan_id})")
        return {"username": username, "orphan_id": orphan_id}


def _handle_signal_captured(payload: dict) -> dict:
    """
    signal_captured → run research.signal_analyzer.
    Analyzes the signal for ICP relevance and recommended action.
    """
    from eos_ai.agent_runtime import AgentRuntime, TaskType

    signal_text = payload.get("signal_text", "")
    source = payload.get("source", "unknown")
    venture_id = payload.get("venture_id", "lyfe_institute")

    runtime = AgentRuntime()
    prompt = (
        f"Analyze this incoming signal from {source}:\n\n"
        f'"{signal_text}"\n\n'
        f"1. ICP match level (high/medium/low) and why\n"
        f"2. Psychological state detected\n"
        f"3. Recommended immediate action"
    )
    result = runtime.run(
        task_type=TaskType.ANALYZE,
        prompt=prompt,
        venture_id=venture_id,
        max_tokens=300,
        agent="research.signal_analyzer",
    )
    print(f"[EventBus:signal_captured] signal from {source} — analyzed")
    return {"interaction_id": result.interaction_id, "analysis": result.output[:200]}


def _handle_content_needed(payload: dict) -> dict:
    """
    content_needed → trigger content.hook_generator.
    Generates a hook and content angle for the given topic.
    """
    from eos_ai.agent_runtime import AgentRuntime, TaskType

    topic = payload.get("topic", "")
    platform = payload.get("platform", "instagram")
    venture_id = payload.get("venture_id", "lyfe_institute")

    runtime = AgentRuntime()
    prompt = (
        f"Generate a high-converting content hook for {platform}.\n\n"
        f"Topic: {topic}\n\n"
        f"Deliver:\n"
        f"1. 3 hook variations (under 15 words each)\n"
        f"2. Recommended angle (visceral pain, transformation, or identity challenge)\n"
        f"3. One-line CTA"
    )
    result = runtime.run(
        task_type=TaskType.GENERATE,
        prompt=prompt,
        venture_id=venture_id,
        max_tokens=500,
        agent="content.hook_generator",
    )
    print(f"[EventBus:content_needed] hooks generated for: {topic[:50]}")
    return {"interaction_id": result.interaction_id, "hooks": result.output[:300]}


def _handle_morning_cycle(payload: dict) -> dict:
    """
    morning_cycle → trigger orchestrator.run_morning_cycle().
    """
    from eos_ai.orchestrator import EOSOrchestrator

    print("[EventBus:morning_cycle] firing orchestrator.run_morning_cycle()")
    orchestrator = EOSOrchestrator()
    orchestrator.run_morning_cycle()
    return {"status": "morning_cycle_complete"}


def _handle_skill_threshold(payload: dict) -> dict:
    """
    skill_threshold → trigger skill_improvement.check_and_improve.
    Runs the improvement cycle for the named skill (or all if not specified).
    """
    from eos_ai.skill_improvement import SkillImprovementEngine

    skill_id = payload.get("skill_id")
    print(
        f"[EventBus:skill_threshold] running improvement cycle"
        + (f" for {skill_id}" if skill_id else " (all skills)")
    )

    engine = SkillImprovementEngine()
    summary = engine.run_improvement_cycle()
    improved = [s for s in summary if s.get("action") == "improved"]
    print(f"[EventBus:skill_threshold] {len(improved)} skill(s) improved")
    return {"improved": len(improved), "summary": summary}


def _handle_goal_activated(payload: dict) -> dict:
    """goal_activated → log + trigger selection cycle re-evaluation."""
    goal_id = payload.get("goal_id", "unknown")
    title = payload.get("title", "")
    print(f"[EventBus:goal_activated] [{goal_id}] {title} → now producing tasks")
    return {"goal_id": goal_id, "state": "active"}


def _handle_goal_deferred(payload: dict) -> dict:
    """goal_deferred → log. Tasks for this goal stop."""
    goal_id = payload.get("goal_id", "unknown")
    title = payload.get("title", "")
    print(f"[EventBus:goal_deferred] [{goal_id}] {title} → tasks paused")
    return {"goal_id": goal_id, "state": "deferred"}


def _handle_goal_completed(payload: dict) -> dict:
    """goal_completed → run selection cycle to promote next goal."""
    goal_id = payload.get("goal_id", "unknown")
    title = payload.get("title", "")
    print(f"[EventBus:goal_completed] [{goal_id}] {title} → triggering re-selection")
    try:
        from eos_ai.goal_selector import GoalSelector

        selector = GoalSelector()
        active = selector.run_selection_cycle()
        print(f"[EventBus:goal_completed] re-selection: {len(active)} active goals")
        return {"goal_id": goal_id, "reselected": len(active)}
    except Exception as e:
        print(f"[EventBus:goal_completed] re-selection failed: {e}")
        return {"goal_id": goal_id, "error": str(e)}


def _handle_goal_dropped(payload: dict) -> dict:
    """goal_dropped → run selection cycle to promote next goal."""
    goal_id = payload.get("goal_id", "unknown")
    title = payload.get("title", "")
    print(f"[EventBus:goal_dropped] [{goal_id}] {title} → triggering re-selection")
    try:
        from eos_ai.goal_selector import GoalSelector

        selector = GoalSelector()
        active = selector.run_selection_cycle()
        print(f"[EventBus:goal_dropped] re-selection: {len(active)} active goals")
        return {"goal_id": goal_id, "reselected": len(active)}
    except Exception as e:
        print(f"[EventBus:goal_dropped] re-selection failed: {e}")
        return {"goal_id": goal_id, "error": str(e)}


def _handle_goal_task_completed(payload: dict) -> dict:
    """goal_task_completed → update goal performance profile with success."""
    goal_id = payload.get("goal_id")
    if not goal_id:
        return {"error": "no goal_id"}
    try:
        from eos_ai.goal_selector import OutcomeTracker

        tracker = OutcomeTracker()
        tracker.record_outcome(
            goal_id=goal_id,
            outcome_type="success",
            execution_time=float(payload.get("execution_time", 0.0)),
            impact_delta=float(payload.get("impact_delta", 0.0)),
            task_type=payload.get("task_type", ""),
            metadata=payload.get("metadata"),
        )
        return {"goal_id": goal_id, "outcome": "success"}
    except Exception as e:
        print(f"[EventBus:goal_task_completed] failed: {e}")
        return {"goal_id": goal_id, "error": str(e)}


def _handle_goal_task_failed(payload: dict) -> dict:
    """goal_task_failed → update goal performance profile with failure."""
    goal_id = payload.get("goal_id")
    if not goal_id:
        return {"error": "no goal_id"}
    try:
        from eos_ai.goal_selector import OutcomeTracker

        tracker = OutcomeTracker()
        tracker.record_outcome(
            goal_id=goal_id,
            outcome_type="failure",
            execution_time=float(payload.get("execution_time", 0.0)),
            task_type=payload.get("task_type", ""),
            metadata=payload.get("metadata"),
        )
        return {"goal_id": goal_id, "outcome": "failure"}
    except Exception as e:
        print(f"[EventBus:goal_task_failed] failed: {e}")
        return {"goal_id": goal_id, "error": str(e)}


# ─── EventRegistry ────────────────────────────────────────────────────────────


class EventRegistry:
    """
    Holds the default handler registrations.
    Call register_defaults() once at startup to wire everything.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def register_defaults(self) -> None:
        """Wire all standard event type → handler mappings."""
        mappings = [
            ("new_lead", _handle_new_lead),
            ("lead_replied", _handle_lead_replied),
            ("lead_booked", _handle_lead_booked),
            ("lead_closed", _handle_lead_closed),
            ("lead_lost", _handle_lead_lost),
            ("signal_captured", _handle_signal_captured),
            ("content_needed", _handle_content_needed),
            ("morning_cycle", _handle_morning_cycle),
            ("skill_threshold", _handle_skill_threshold),
            ("goal_activated", _handle_goal_activated),
            ("goal_deferred", _handle_goal_deferred),
            ("goal_completed", _handle_goal_completed),
            ("goal_dropped", _handle_goal_dropped),
            ("goal_task_completed", _handle_goal_task_completed),
            ("goal_task_failed", _handle_goal_task_failed),
        ]
        for event_type, handler in mappings:
            self._bus.subscribe(event_type, handler)
        print(f"[EventRegistry] {len(mappings)} default handlers registered")


# ─── Module-level singleton helper ───────────────────────────────────────────


def get_bus() -> EventBus:
    """Return the singleton EventBus instance."""
    return EventBus()


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("EventBus — reactive chain test")
    print("=" * 60)

    bus = EventBus()
    registry = EventRegistry(bus)
    registry.register_defaults()

    print("\n── Simulating new_lead event ──\n")
    results = bus.publish(
        "new_lead",
        {
            "username": "test_lead_cli",
            "score": 9,
            "state": "Frustrated Drifter",
            "venture_id": "lyfe_institute",
        },
    )

    print("\n── Events table (last 5) ──\n")
    with get_conn(ORG_ID) as cur:
        cur.execute(
            "SELECT id, event_type, created_at, handled_by FROM events "
            "WHERE org_id = %s ORDER BY created_at DESC LIMIT 5",
            (ORG_ID,),
        )
        rows = cur.fetchall()
    for row in rows:
        handlers = json.loads(row["handled_by"] or "[]")
        print(f"  [{str(row['id'])[:8]}] {row['event_type']} @ {str(row['created_at'])[:19]}")
        print(f"       handled_by: {handlers}")

    print("\n── Recent interactions (last 3) ──\n")
    with get_conn(ORG_ID) as cur:
        cur.execute(
            "SELECT id, agent_label, output_summary, created_at "
            "FROM interactions WHERE org_id = %s ORDER BY created_at DESC LIMIT 3",
            (ORG_ID,),
        )
        rows = cur.fetchall()
    for row in rows:
        print(f"  [{str(row['id'])[:8]}] {row['agent_label']} | {str(row['created_at'])[:19]}")
        print(f"       {(row['output_summary'] or '')[:100]}")
