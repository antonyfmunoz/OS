"""EOS EventBus — reactive coordination layer backed by UMH.

All pub/sub infrastructure comes from umh.signal.event_bus.
This module provides:
  1. NeonEventLogger — persists events to Neon events table
  2. EOS event type constants
  3. EOS-specific handler functions (business logic)
  4. EOSEventRegistry — wires default handlers at startup
  5. get_bus() — shared bus instance for the process

Usage:
    from umh.runtime_engine.event_bus import get_bus, EOSEventRegistry

    bus = get_bus()
    EOSEventRegistry(bus).register_defaults()

    bus.publish('new_lead', {
        'username': 'johndoe',
        'score': 8,
        'state': 'Frustrated Drifter',
        'venture_id': 'lyfe_institute',
    })
"""

from __future__ import annotations

import json
import os
import sys
import threading
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from umh.signal.event_bus import (  # noqa: E402
    EventBus,
    EventLogger,
    EventRegistry,
    EventResult,
    NullLogger,
)


# ─── Neon persistence logger ────────────────────────────────────────────────


class NeonEventLogger:
    """Persists events to Neon events table. Satisfies umh EventLogger protocol."""

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        handled_by: list[str],
    ) -> None:
        try:
            from umh.storage.adapters.neon import get_conn, ORG_ID

            with get_conn(ORG_ID) as cur:
                cur.execute(
                    """
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (ORG_ID, event_type, json.dumps(payload), json.dumps(handled_by)),
                )
        except Exception as e:
            print(f"[EventBus] log_event failed: {e}")


# ─── Supported event types ────────────────────────────────────────────────────

EVENT_TYPES = frozenset(
    {
        "new_lead",
        "lead_replied",
        "lead_booked",
        "lead_closed",
        "lead_lost",
        "signal_captured",
        "content_needed",
        "morning_cycle",
        "skill_threshold",
    }
)


# ─── Shared bus instance ─────────────────────────────────────────────────────

_BUS: EventBus | None = None
_BUS_LOCK = threading.Lock()


def get_bus() -> EventBus:
    """Return the process-wide EventBus backed by Neon persistence."""
    global _BUS
    with _BUS_LOCK:
        if _BUS is None:
            _BUS = EventBus(logger=NeonEventLogger())
        return _BUS


# ─── Default handlers (EOS business logic) ───────────────────────────────────


def _handle_new_lead(payload: dict) -> dict:
    from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType

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
    from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType

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
        system_extra=(
            f"Interaction ID context: {interaction_id}" if interaction_id else None
        ),
    )
    print(f"[EventBus:lead_replied] @{username} — objection handler ran")
    return {
        "username": username,
        "interaction_id": result.interaction_id,
        "response_preview": result.output[:200],
    }


def _handle_lead_booked(payload: dict) -> dict:
    from umh.runtime_engine.memory import AgentMemory

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
        return {
            "username": username,
            "outcome_id": outcome_id,
            "interaction_id": row["id"],
        }
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
    from umh.runtime_engine.memory import AgentMemory

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

    try:
        from umh.runtime_engine.human_intelligence import HumanIntelligenceEngine
        from umh.environments.system_context import load_context_from_env

        engine = HumanIntelligenceEngine(load_context_from_env())
        profiles = engine.run_profile_cycle()
        print(f"[EventBus:lead_closed] profile cycle: {profiles}")
    except Exception as e:
        print(f"[EventBus:lead_closed] profile update skipped: {e}")

    return {"username": username, "outcome_id": outcome_id}


def _handle_lead_lost(payload: dict) -> dict:
    from umh.runtime_engine.memory import AgentMemory

    username = payload.get("username", "unknown")
    objection = payload.get("objection", "")
    venture_id = payload.get("venture_id", "lyfe_institute")

    mem = AgentMemory()
    notes = "event_bus:lead_lost"
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
    from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType

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
    from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType

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
    from umh.runtime_engine.orchestrator import EOSOrchestrator

    print("[EventBus:morning_cycle] firing orchestrator.run_morning_cycle()")
    orchestrator = EOSOrchestrator()
    orchestrator.run_morning_cycle()
    return {"status": "morning_cycle_complete"}


def _handle_skill_threshold(payload: dict) -> dict:
    try:
        from umh.runtime_engine.skill_improvement import SkillImprovementEngine
    except ImportError:
        pass

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


# ─── EOSEventRegistry ────────────────────────────────────────────────────────


class EOSEventRegistry(EventRegistry):
    """EOS-specific handler set. Extends UMH's EventRegistry."""

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.add("new_lead", _handle_new_lead)
        self.add("lead_replied", _handle_lead_replied)
        self.add("lead_booked", _handle_lead_booked)
        self.add("lead_closed", _handle_lead_closed)
        self.add("lead_lost", _handle_lead_lost)
        self.add("signal_captured", _handle_signal_captured)
        self.add("content_needed", _handle_content_needed)
        self.add("morning_cycle", _handle_morning_cycle)
        self.add("skill_threshold", _handle_skill_threshold)

    def register_defaults(self) -> None:
        """Wire all EOS default handlers."""
        count = self.register_all()
        print(f"[EOSEventRegistry] {count} default handlers registered")


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from umh.storage.adapters.neon import get_conn, ORG_ID

    print("=" * 60)
    print("EventBus — reactive chain test (UMH-backed)")
    print("=" * 60)

    bus = get_bus()
    registry = EOSEventRegistry(bus)
    registry.register_defaults()

    print("\n── Simulating new_lead event ──\n")
    result = bus.publish(
        "new_lead",
        {
            "username": "test_lead_cli",
            "score": 9,
            "state": "Frustrated Drifter",
            "venture_id": "lyfe_institute",
        },
    )
    print(f"Handlers called: {result.handlers_called}, Errors: {result.errors}")

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
        print(
            f"  [{str(row['id'])[:8]}] {row['event_type']} "
            f"@ {str(row['created_at'])[:19]}"
        )
        print(f"       handled_by: {handlers}")
