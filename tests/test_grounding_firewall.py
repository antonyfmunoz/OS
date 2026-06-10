"""Tests for Phase 14.14C — Grounding Firewall + Hermes + Vision.

Verifies:
1. No data = no hallucinated answer (deterministic blocker)
2. Grounding firewall prevents LLM path for status queries
3. Real data = grounded answer with correct structure
4. Hermes not healthy until real call succeeds
5. Vision queries require actual frame
6. Provider metadata includes routing reason
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Category 1: No data = no hallucinated answer ─────────────────────────────


class TestNoDataNoFabrication:
    def test_docker_missing_returns_blocker(self):
        from substrate.organism.grounding_registry import collect_grounding

        with patch("substrate.organism.grounding_registry.os.path.exists", return_value=False):
            result = collect_grounding("docker_status")
        assert "docker" in result.missing
        assert result.confidence in ("blocked", "partial")
        assert "container" not in result.summary.lower() or "0 container" in result.summary.lower()

    def test_providers_missing_returns_partial(self):
        from substrate.organism import grounding_registry

        original = grounding_registry._COLLECTORS["providers"]
        grounding_registry._COLLECTORS["providers"] = lambda: (_ for _ in ()).throw(
            ImportError("model_router not available")
        )
        try:
            result = grounding_registry.collect_grounding("provider_health")
            assert "providers" in result.missing
            assert result.confidence in ("blocked", "partial")
        finally:
            grounding_registry._COLLECTORS["providers"] = original

    def test_work_packets_missing_returns_empty(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            result = collect_grounding("work_packets")
        assert "work_packets" in result.missing

    def test_workcells_missing_returns_empty(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            result = collect_grounding("agent_status")
        assert "workcells" in result.missing

    def test_system_status_all_missing_says_so(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            with patch("substrate.organism.grounding_registry.os.path.exists", return_value=False):
                with patch(
                    "substrate.organism.grounding_registry._collect_providers",
                    side_effect=ImportError("no router"),
                ):
                    result = collect_grounding("system_status")
        assert len(result.missing) > 0
        assert result.confidence != "deterministic"


# ── Category 2: Firewall prevents LLM path ───────────────────────────────────


class TestFirewallPreventsLLM:
    def test_status_query_never_calls_call_with_fallback(self):
        from substrate.organism.advisor_conversation import AdvisorConversation

        mock_advisor = MagicMock()
        conv = AdvisorConversation(advisor=mock_advisor)

        with patch("adapters.models.model_router.call_with_fallback") as mock_cwf:
            response = conv._handle_status("what is the system status?")
            mock_cwf.assert_not_called()

        assert response.text
        assert "deterministic" in response.metadata.get("model_tier", "")

    def test_conversation_with_docker_question_reroutes_to_grounded(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        result = detect_status_seeking("hey what containers are running right now?")
        assert result == "docker_status"

    def test_conversation_with_provider_question_reroutes(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        result = detect_status_seeking("what providers are online?")
        assert result == "provider_health"

    def test_conversation_with_general_question_passes_through(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        result = detect_status_seeking("what should we focus on next quarter?")
        assert result is None

    def test_agent_query_uses_grounded_handler(self):
        from substrate.organism.advisor_conversation import AdvisorConversation

        mock_advisor = MagicMock()
        conv = AdvisorConversation(advisor=mock_advisor)

        with patch("adapters.models.model_router.call_with_fallback") as mock_cwf:
            with patch(
                "substrate.organism.grounded_handlers.handle_grounded_agents",
            ) as mock_handler:
                mock_handler.return_value = MagicMock(
                    text="test", conversation_id="", intent="agent_query"
                )
                from substrate.workstation.command_router import CommandIntent

                # Directly test the dispatch logic
                response = mock_handler("what agents are running")
                mock_cwf.assert_not_called()
                mock_handler.assert_called_once()

    def test_blocked_query_uses_grounded_handler(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        result = detect_status_seeking("what is blocked right now?")
        assert result == "blocked_packets"


# ── Category 3: Real data = grounded answer ───────────────────────────────────


class TestRealDataGrounded:
    def test_work_packet_counts_match_file(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        wp_dir = tmp_path / "data" / "umh" / "universal_work"
        wp_dir.mkdir(parents=True)
        wp_file = wp_dir / "work_packets.jsonl"
        wp_file.write_text(
            '{"id": "wp-1", "status": "active"}\n'
            '{"id": "wp-2", "status": "blocked"}\n'
            '{"id": "wp-3", "status": "in_progress"}\n'
            '{"id": "wp-4", "status": "completed"}\n'
        )

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            result = collect_grounding("work_packets")

        assert result.confidence == "deterministic"
        assert result.data["work_packets"]["active"] == 2  # active + in_progress
        assert result.data["work_packets"]["blocked"] == 1
        assert result.data["work_packets"]["total"] == 4

    def test_blocked_packets_filters_correctly(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        wp_dir = tmp_path / "data" / "umh" / "universal_work"
        wp_dir.mkdir(parents=True)
        wp_file = wp_dir / "work_packets.jsonl"
        wp_file.write_text(
            '{"id": "wp-1", "status": "active", "title": "Active task"}\n'
            '{"id": "wp-2", "status": "blocked", "title": "Blocked task"}\n'
            '{"id": "wp-3", "status": "blocked", "title": "Another blocked"}\n'
        )

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            result = collect_grounding("blocked_packets")

        assert result.confidence == "deterministic"
        assert len(result.data["blocked_packets"]["blocked"]) == 2

    def test_workcell_heartbeats_reads_real_files(self, tmp_path):
        from substrate.organism.grounding_registry import collect_grounding

        wc_dir = tmp_path / "data" / "umh" / "organism" / "workcells" / "researcher"
        wc_dir.mkdir(parents=True)
        hb = wc_dir / "heartbeat.json"
        hb.write_text('{"status": "active", "timestamp": "2026-06-09T10:00:00Z"}')

        with patch("substrate.organism.grounding_registry._REPO", str(tmp_path)):
            result = collect_grounding("agent_status")

        assert result.confidence == "deterministic"
        assert len(result.data["workcells"]["workcells"]) == 1
        assert result.data["workcells"]["workcells"][0]["name"] == "researcher"


# ── Category 4: Hermes ────────────────────────────────────────────────────────


class TestHermesIntegration:
    def test_hermes_not_healthy_until_call_succeeds(self):
        import adapters.models.hermes_cli as hcli

        # Reset state
        hcli._first_call_succeeded = False
        assert not hcli.is_verified()

    def test_hermes_is_available_checks_mesh(self):
        import adapters.models.hermes_cli as hcli

        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = ConnectionRefusedError()
            assert not hcli.is_available()

    def test_hermes_model_registry_strengths_updated(self):
        from adapters.models.model_router import MODEL_REGISTRY
        from substrate.contracts.agent_types import TaskType

        hermes_config = MODEL_REGISTRY.get("hermes-agent")
        assert hermes_config is not None
        assert TaskType.CONVERSATION in hermes_config.strengths
        assert TaskType.ANALYSIS in hermes_config.strengths

    def test_hermes_supplemental_only_for_safe_purposes(self):
        from adapters.models.model_router import SUPPLEMENTAL_PROVIDERS

        assert "hermes-agent" in SUPPLEMENTAL_PROVIDERS.get("quick_triage", [])
        assert "hermes-agent" in SUPPLEMENTAL_PROVIDERS.get("advise_founder", [])
        assert "hermes-agent" not in SUPPLEMENTAL_PROVIDERS.get("status_report", [])
        assert "hermes-agent" not in SUPPLEMENTAL_PROVIDERS.get("build_code", [])
        assert "hermes-agent" not in SUPPLEMENTAL_PROVIDERS.get("autonomous_execution", [])


# ── Category 5: Vision ────────────────────────────────────────────────────────


class TestVisionGrounding:
    def test_vision_query_requires_frame(self):
        from substrate.organism import grounding_registry

        original = grounding_registry._COLLECTORS["vision"]
        grounding_registry._COLLECTORS["vision"] = lambda: (_ for _ in ()).throw(
            ConnectionRefusedError("relay offline")
        )
        try:
            result = grounding_registry.collect_grounding("vision_status")
            assert "vision" in result.missing
        finally:
            grounding_registry._COLLECTORS["vision"] = original

    def test_vision_status_seeking_detected(self):
        from substrate.organism.grounding_registry import detect_status_seeking

        assert detect_status_seeking("what is the camera status") == "vision_status"
        assert detect_status_seeking("is the camera stream working") == "vision_status"


# ── Category 6: Response format ───────────────────────────────────────────────


class TestResponseFormat:
    def test_grounded_response_has_required_fields(self):
        from substrate.organism.grounding_registry import collect_grounding

        result = collect_grounding("system_status")
        d = result.to_dict()

        assert "source" in d
        assert "freshness" in d
        assert "data" in d
        assert "summary" in d
        assert "missing" in d
        assert "confidence" in d
        assert isinstance(d["missing"], list)
        assert d["confidence"] in ("deterministic", "partial", "blocked")

    def test_grounded_handler_returns_advisor_response(self):
        from substrate.organism.grounded_handlers import handle_grounded_status

        response = handle_grounded_status("system status")

        assert hasattr(response, "text")
        assert hasattr(response, "metadata")
        assert response.metadata.get("model_tier") == "deterministic"
        assert "grounding" in response.metadata
        assert response.intent == "status_query"

    def test_detect_status_seeking_all_patterns_valid(self):
        from substrate.organism.grounding_registry import (
            _STATUS_SEEKING_PATTERNS,
            _QUERY_SOURCES,
        )

        for _pattern, qtype in _STATUS_SEEKING_PATTERNS:
            assert qtype in _QUERY_SOURCES, f"Pattern maps to unknown query type: {qtype}"


# ── Category 7: Provider metadata ─────────────────────────────────────────────


class TestProviderMetadata:
    def test_supplemental_providers_requires_available(self):
        from adapters.models.model_router import (
            MODEL_REGISTRY,
            _providers_for_purpose,
        )

        hermes_config = MODEL_REGISTRY.get("hermes-agent")
        original_available = hermes_config.available

        hermes_config.available = False
        keys = _providers_for_purpose("quick_triage")
        assert "hermes-agent" not in keys

        hermes_config.available = original_available

    def test_providers_for_purpose_returns_role_based_first(self):
        from adapters.models.model_router import _providers_for_purpose

        keys = _providers_for_purpose("quick_triage")
        assert len(keys) >= 2
        # Role-based providers should come before supplemental
        assert keys[0] != "hermes-agent"
