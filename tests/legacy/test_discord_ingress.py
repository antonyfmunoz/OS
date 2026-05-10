"""
Tests for Discord ingress adapter and operator trace.

Validates:
1. Discord ingress emits exactly one orchestration ingress event.
2. Disabled mode returns rejected result (no event emitted).
3. Intent classification works for commands and channel hints.
4. Goal text extraction strips command prefixes.
5. IngressRequest is JSON-serializable.
6. Full end-to-end: Discord ingress → scheduler → intent created.
7. Operator trace includes essential fields.
8. Operator trace formatters produce valid output.
9. No legacy double-processing in active mode.
10. Transport-agnostic shape preserves voice/workstation extensibility.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/OS")

from umh.substrate.discord_ingress_adapter import (
    TRANSPORT_DISCORD_TEXT,
    TRANSPORT_DISCORD_VOICE,
    TRANSPORT_WORKSTATION,
    IngressRequest,
    IngressResult,
    classify_intent_type,
    extract_goal_text,
    ingest_discord_message,
)
from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.event_scheduler import EventScheduler, SchedulerEvent
from umh.substrate.intent_models import (
    IntentStatus,
    IntentType,
    PlanStep,
    intent_store_key,
)
from umh.substrate.operator_trace import (
    OperatorTrace,
    build_trace_from_drain,
    format_trace_for_discord,
    format_trace_for_log,
)
from umh.substrate.orchestration_bootstrap import bootstrap_orchestration
from umh.substrate.runtime_state_store import RuntimeStateStore


# ── Helpers ──────────────────────────────────────────────────────────


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    log = EventLogRuntime(log_path=Path(tempfile.mktemp(suffix=".jsonl")))
    scheduler = EventScheduler(store=store, event_log=log)
    return scheduler, store


def _one_step_generator(intent, state) -> tuple[PlanStep, ...]:
    return (PlanStep(step_index=0, event_type="test_step_event", payload={}),)


# ── Test: Ingress Adapter ───────────────────────────────────────────


class TestDiscordIngressAdapter(unittest.TestCase):
    """Tests for discord_ingress_adapter.py"""

    def test_disabled_mode_returns_rejected(self):
        """When EOS_DISCORD_ORCHESTRATION_ENABLED is not set, adapter rejects."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EOS_DISCORD_ORCHESTRATION_ENABLED", None)
            result = ingest_discord_message(
                text="hello",
                user_id="123",
                channel_id="456",
            )
            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "disabled")
            self.assertIsNone(result.event)

    def test_enabled_mode_emits_event(self):
        """When enabled, adapter produces exactly one SchedulerEvent."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="run morning brief",
                user_id="user_42",
                channel_id="ch_1",
                guild_id="guild_1",
                channel_name="general",
            )
            self.assertTrue(result.accepted)
            self.assertIsNotNone(result.event)
            self.assertEqual(result.event.event_type, "operator_intent_requested")
            self.assertEqual(result.intent_type, "workflow_run")

    def test_event_has_correct_payload(self):
        """Event payload contains intent_type, goal, and source_context."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="run morning brief",
                user_id="user_42",
                channel_id="ch_1",
                channel_name="morning-brief",
            )
            payload = result.event.payload
            self.assertEqual(payload["intent_type"], "workflow_run")
            self.assertIn("text", payload["goal"])
            self.assertEqual(payload["goal"]["text"], "run morning brief")
            self.assertIn("source_context", payload)
            self.assertEqual(
                payload["source_context"]["adapter"], "discord_ingress_adapter"
            )

    def test_operator_id_in_event_source(self):
        """Event source includes operator ID."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="hello",
                user_id="user_99",
            )
            self.assertIn("user_99", result.event.source)

    def test_empty_text_rejected(self):
        """Empty text is rejected with reason."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(text="", user_id="123")
            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "empty_text")

    def test_missing_user_id_rejected(self):
        """Missing user_id is rejected."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(text="hello", user_id="")
            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "missing_operator_id")

    def test_ingress_request_serializable(self):
        """IngressRequest.to_dict() produces JSON-serializable output."""
        req = IngressRequest(
            text="test message",
            operator_id="user_1",
            transport=TRANSPORT_DISCORD_TEXT,
            channel_id="ch_1",
            guild_id="guild_1",
            channel_name="general",
        )
        d = req.to_dict()
        self.assertEqual(d["text"], "test message")
        self.assertEqual(d["transport"], "discord_text")
        self.assertIn("timestamp", d)
        import json

        json.dumps(d)  # Must not raise

    def test_ingress_result_serializable(self):
        """IngressResult.to_dict() produces JSON-serializable output."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="hello", user_id="user_1", channel_id="ch_1"
            )
            d = result.to_dict()
            self.assertTrue(d["accepted"])
            self.assertIn("event_type", d)
            import json

            json.dumps(d)  # Must not raise

    def test_session_name_derived_from_channel(self):
        """Session name defaults to discord:{channel_id}."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="hello", user_id="u1", channel_id="ch_99"
            )
            self.assertEqual(result.event.session_name, "discord:ch_99")

    def test_session_name_override(self):
        """Explicit session_name overrides default derivation."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="hello",
                user_id="u1",
                channel_id="ch_99",
                session_name="custom_session",
            )
            self.assertEqual(result.event.session_name, "custom_session")


# ── Test: Intent Classification ─────────────────────────────────────


class TestIntentClassification(unittest.TestCase):
    """Tests for classify_intent_type and extract_goal_text."""

    def test_command_prefix_run(self):
        self.assertEqual(classify_intent_type("!run morning brief"), "workflow_run")

    def test_command_prefix_execute(self):
        self.assertEqual(
            classify_intent_type("!execute send_email"), "execution_request"
        )

    def test_command_prefix_intent(self):
        self.assertEqual(classify_intent_type("!intent custom_thing"), "custom")

    def test_channel_hint_morning_brief(self):
        self.assertEqual(
            classify_intent_type("hello", channel_name="morning-brief"),
            "workflow_run",
        )

    def test_default_is_workflow_run(self):
        self.assertEqual(classify_intent_type("some random text"), "workflow_run")

    def test_extract_goal_strips_prefix(self):
        self.assertEqual(extract_goal_text("!run morning brief"), "morning brief")

    def test_extract_goal_preserves_plain_text(self):
        self.assertEqual(extract_goal_text("hello world"), "hello world")


# ── Test: Transport Agnostic Shape ──────────────────────────────────


class TestTransportAgnosticShape(unittest.TestCase):
    """Verify the ingress shape supports multiple transports."""

    def test_discord_text_transport(self):
        req = IngressRequest(
            text="msg", operator_id="u1", transport=TRANSPORT_DISCORD_TEXT
        )
        self.assertEqual(req.transport, "discord_text")

    def test_discord_voice_transport(self):
        req = IngressRequest(
            text="msg", operator_id="u1", transport=TRANSPORT_DISCORD_VOICE
        )
        self.assertEqual(req.transport, "discord_voice")

    def test_workstation_transport(self):
        req = IngressRequest(
            text="msg", operator_id="u1", transport=TRANSPORT_WORKSTATION
        )
        self.assertEqual(req.transport, "workstation")

    def test_all_transports_same_shape(self):
        """All transports produce the same IngressRequest structure."""
        for transport in [
            TRANSPORT_DISCORD_TEXT,
            TRANSPORT_DISCORD_VOICE,
            TRANSPORT_WORKSTATION,
        ]:
            req = IngressRequest(text="test", operator_id="u1", transport=transport)
            d = req.to_dict()
            self.assertIn("text", d)
            self.assertIn("operator_id", d)
            self.assertIn("transport", d)
            self.assertIn("timestamp", d)


# ── Test: End-to-End Orchestration ──────────────────────────────────


class TestEndToEndOrchestration(unittest.TestCase):
    """Full integration: Discord message → scheduler → intent created."""

    def test_discord_ingress_creates_intent_in_scheduler(self):
        """A Discord message routed through the adapter creates an intent
        in the RuntimeStateStore after scheduler drain."""
        scheduler, store = _make_scheduler()

        # Bootstrap orchestration with a test plan generator
        coordinator = bootstrap_orchestration(scheduler)
        coordinator._plan_registry.register(
            IntentType.WORKFLOW_RUN, _one_step_generator
        )

        # Produce the ingress event
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="run morning brief",
                user_id="user_42",
                channel_id="ch_1",
                channel_name="general",
            )

        self.assertTrue(result.accepted)

        # Emit into scheduler and drain
        scheduler.emit(result.event)
        run_result = scheduler.run()

        # Verify intent was created
        self.assertGreater(run_result.events_processed, 0)

        # Check store for intent
        snapshot = store.snapshot()
        intent_keys = [k for k in snapshot if k.startswith("intent:")]
        self.assertGreater(len(intent_keys), 0, "No intent created in store")

        # Verify the intent has the correct type
        intent_data = snapshot[intent_keys[0]]
        self.assertEqual(intent_data["intent_type"], "workflow_run")
        self.assertEqual(intent_data["status"], "active")

    def test_discord_ingress_emits_exactly_one_event(self):
        """Adapter produces exactly one SchedulerEvent per message."""
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="run something",
                user_id="user_1",
            )
            self.assertTrue(result.accepted)
            # Exactly one event
            self.assertIsNotNone(result.event)
            self.assertEqual(result.event.event_type, "operator_intent_requested")

    def test_no_double_processing_in_active_mode(self):
        """When orchestration is active, the event goes through
        the orchestration path only — not duplicated."""
        scheduler, store = _make_scheduler()
        coordinator = bootstrap_orchestration(scheduler)
        coordinator._plan_registry.register(
            IntentType.WORKFLOW_RUN, _one_step_generator
        )

        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            result = ingest_discord_message(
                text="do something",
                user_id="user_1",
                channel_id="ch_1",
            )

        scheduler.emit(result.event)
        run_result = scheduler.run()

        # Count how many intents were created (should be exactly 1)
        snapshot = store.snapshot()
        active_keys = [k for k in snapshot if k.startswith("active_intent.")]
        self.assertEqual(len(active_keys), 1, "Expected exactly 1 active intent")

    def test_inactive_mode_unchanged(self):
        """When orchestration is disabled, no event is produced
        and the existing paths remain unaffected."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EOS_DISCORD_ORCHESTRATION_ENABLED", None)
            result = ingest_discord_message(
                text="hello",
                user_id="user_1",
            )
            self.assertFalse(result.accepted)
            self.assertIsNone(result.event)
            # No side effects — no scheduler interaction


# ── Test: Operator Trace ────────────────────────────────────────────


class TestOperatorTrace(unittest.TestCase):
    """Tests for operator_trace.py"""

    def test_trace_essential_fields(self):
        """OperatorTrace has all required fields."""
        trace = OperatorTrace(
            ingress_source="discord_ingress_adapter",
            ingress_transport="discord_text",
            intent_id="int_abc123",
            intent_type="workflow_run",
            terminal_status="completed",
        )
        self.assertEqual(trace.ingress_source, "discord_ingress_adapter")
        self.assertEqual(trace.ingress_transport, "discord_text")
        self.assertEqual(trace.intent_id, "int_abc123")
        self.assertEqual(trace.intent_type, "workflow_run")
        self.assertEqual(trace.terminal_status, "completed")

    def test_trace_to_dict_serializable(self):
        """OperatorTrace.to_dict() is JSON-serializable."""
        trace = OperatorTrace(
            ingress_source="test",
            intent_id="int_1",
            intent_type="workflow_run",
            plan_score=0.85,
            steps_total=3,
            steps_executed=2,
        )
        d = trace.to_dict()
        import json

        json.dumps(d)  # Must not raise
        self.assertEqual(d["intent"]["intent_id"], "int_1")
        self.assertEqual(d["plan"]["score"], 0.85)
        self.assertEqual(d["execution"]["steps_total"], 3)

    def test_format_trace_for_log(self):
        """Log formatter produces a single-line string with key fields."""
        trace = OperatorTrace(
            intent_id="int_abc",
            intent_type="workflow_run",
            terminal_status="completed",
            steps_total=2,
            steps_executed=2,
            events_processed=5,
        )
        log_line = format_trace_for_log(trace)
        self.assertIn("int_abc", log_line)
        self.assertIn("workflow_run", log_line)
        self.assertIn("completed", log_line)
        self.assertIn("2/2", log_line)

    def test_format_trace_for_discord(self):
        """Discord formatter produces markdown with status emoji."""
        trace = OperatorTrace(
            intent_id="int_abc123456789",
            intent_type="workflow_run",
            terminal_status="completed",
            ingress_transport="discord_text",
            variant_id="lifecycle_finalize:default",
            plan_score=0.9,
            plan_success_count=5,
            plan_failure_count=1,
            steps_total=3,
            steps_executed=3,
            events_processed=8,
            mutations_applied=4,
        )
        text = format_trace_for_discord(trace)
        self.assertIn("✅", text)
        self.assertIn("workflow_run", text)
        self.assertIn("discord_text", text)
        self.assertIn("lifecycle_finalize:default", text)
        self.assertIn("0.900", text)
        self.assertIn("3/3", text)

    def test_format_trace_failed_shows_reason(self):
        """Failed trace shows reason in both formatters."""
        trace = OperatorTrace(
            intent_id="int_x",
            intent_type="workflow_run",
            terminal_status="failed",
            terminal_reason="no_plan_available",
        )
        log_line = format_trace_for_log(trace)
        self.assertIn("no_plan_available", log_line)

        discord_text = format_trace_for_discord(trace)
        self.assertIn("❌", discord_text)
        self.assertIn("no_plan_available", discord_text)

    def test_build_trace_from_drain(self):
        """build_trace_from_drain produces a trace from scheduler drain."""
        scheduler, store = _make_scheduler()
        coordinator = bootstrap_orchestration(scheduler)
        coordinator._plan_registry.register(
            IntentType.WORKFLOW_RUN, _one_step_generator
        )

        # Create and process an intent
        with patch.dict(os.environ, {"EOS_DISCORD_ORCHESTRATION_ENABLED": "1"}):
            ingress_result = ingest_discord_message(
                text="run test",
                user_id="user_1",
                channel_id="ch_1",
            )

        scheduler.emit(ingress_result.event)
        run_result = scheduler.run()

        # Build trace
        trace = build_trace_from_drain(
            run_result,
            store,
            ingress_context=ingress_result.event.payload.get("source_context"),
        )

        self.assertGreater(trace.events_processed, 0)
        self.assertEqual(trace.intent_type, "workflow_run")
        self.assertIn(trace.intent_status, ("active", "completed", "failed"))

    def test_trace_mutated_variant_flag(self):
        """Mutated variant flag is correctly reflected."""
        trace = OperatorTrace(
            is_mutated_variant=True,
            variant_id="test:mutated_v1",
        )
        d = trace.to_dict()
        self.assertTrue(d["plan"]["is_mutated_variant"])

        discord_text = format_trace_for_discord(trace)
        self.assertIn("mutated", discord_text)


if __name__ == "__main__":
    unittest.main()
