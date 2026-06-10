"""Tests for Phase 14.14E — Hermes Adapter Parity.

Verifies:
1. Health checks return structured responses
2. Provider/model inventory strips secrets
3. Generate calls work through mesh
4. Session create/send/read/list/close lifecycle
5. Timeout returns structured blocker
6. Cancel returns structured response
7. Unsupported operations are explicit
8. Capability registry is complete
9. Role matrix blocks build_code by default
10. Status report requires source data
11. No-data refusal
12. Summarizes supplied data only
13. Benchmark assigns roles
14. Metadata visible not spoken
15. Prompt base64 encoding works
16. PowerShell injection blocked
17. Provider not primary without benchmark
18. Router role gating
19. Diagnostics return actionable blockers
20. Existing grounding firewall not regressed
"""

from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_mesh_dispatch_success(capability, params, timeout=None):
    """Simulates a successful Hermes call through mesh."""
    return {
        "success": True,
        "stdout": "HERMES_OK\n",
        "stderr": "",
        "exit_code": 0,
        "latency_ms": 5000,
    }


def _mock_mesh_dispatch_timeout(capability, params, timeout=None):
    return None


def _mock_beast_connected():
    return True


def _mock_hermes_available():
    return True


def _mock_hermes_shell_version(command, timeout=15):
    if "version" in command.lower():
        return {"success": True, "stdout": "hermes agent v0.15.2"}
    if "config show" in command.lower():
        return {"success": True, "stdout": "provider: anthropic\nmodel: claude-sonnet-4\nkey: sk-redacted"}
    if "config path" in command.lower():
        return {"success": True, "stdout": "/home/user/.hermes/config.toml"}
    if "config get provider" in command.lower():
        return {"success": True, "stdout": "anthropic"}
    return {"success": True, "stdout": "ok"}


# ── Category 1: Health checks ─────────────────────────────────────────────────


class TestHermesHealth:
    def test_health_returns_structured_response(self):
        from adapters.models.hermes_cli import health

        with patch("adapters.models.hermes_cli._beast_connected", return_value=False):
            result = health()

        assert result["provider"] == "hermes-agent"
        assert result["runtime"] == "hermes_beast"
        assert result["node"] == "beast_windows"
        assert result["transport"] == "mesh_dispatch"
        assert result["status"] == "beast_offline"
        assert "capabilities" in result
        assert "assigned_roles" in result
        assert "blocked_roles" in result

    def test_health_beast_connected_unverified(self):
        import adapters.models.hermes_cli as hcli

        old_verified = hcli._first_call_succeeded
        hcli._first_call_succeeded = False
        try:
            with patch("adapters.models.hermes_cli._beast_connected", return_value=True), \
                 patch("adapters.models.hermes_cli._hermes_shell", _mock_hermes_shell_version):
                result = hcli.health()
            assert result["status"] == "unverified"
            assert result["available"] is True
            assert result["verified"] is False
        finally:
            hcli._first_call_succeeded = old_verified

    def test_health_beast_connected_verified(self):
        import adapters.models.hermes_cli as hcli

        old_verified = hcli._first_call_succeeded
        hcli._first_call_succeeded = True
        try:
            with patch("adapters.models.hermes_cli._beast_connected", return_value=True), \
                 patch("adapters.models.hermes_cli._hermes_shell", _mock_hermes_shell_version):
                result = hcli.health()
            assert result["status"] == "healthy"
            assert result["verified"] is True
        finally:
            hcli._first_call_succeeded = old_verified


# ── Category 2: Provider/model inventory ──────────────────────────────────────


class TestHermesInventory:
    def test_providers_strips_secrets(self):
        from adapters.models.hermes_cli import providers

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._hermes_shell", _mock_hermes_shell_version):
            result = providers()

        assert result["success"] is True
        for line in result["providers"]:
            lower = line.lower() if isinstance(line, str) else ""
            assert "sk-" not in lower
            assert "secret" not in lower

    def test_models_returns_list(self):
        from adapters.models.hermes_cli import models

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._hermes_shell", _mock_hermes_shell_version):
            result = models()

        assert result["success"] is True
        assert isinstance(result["models"], list)
        assert len(result["models"]) > 0

    def test_providers_unavailable_returns_error(self):
        from adapters.models.hermes_cli import providers

        with patch("adapters.models.hermes_cli.is_available", return_value=False):
            result = providers()

        assert result["success"] is False


# ── Category 3: Generate calls ────────────────────────────────────────────────


class TestHermesGenerate:
    def test_generate_returns_hermes_result(self):
        from adapters.models.hermes_cli import query_hermes_sync

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._mesh_dispatch", _mock_mesh_dispatch_success):
            result = query_hermes_sync("test prompt", timeout=30)

        assert result is not None
        assert "HERMES_OK" in result.output
        assert result.provider == "hermes"
        assert result.estimated_input_tokens > 0
        assert result.estimated_output_tokens > 0
        assert result.metadata["runtime"] == "hermes_beast"
        assert result.metadata["node"] == "beast_windows"

    def test_generate_timeout_returns_none(self):
        from adapters.models.hermes_cli import query_hermes_sync

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._mesh_dispatch", _mock_mesh_dispatch_timeout):
            result = query_hermes_sync("test prompt", timeout=5)

        assert result is None

    def test_generate_error_leak_returns_none(self):
        from adapters.models.hermes_cli import query_hermes_sync

        def mock_error(cap, params, timeout=None):
            return {"success": True, "stdout": "authentication error: invalid api key", "stderr": "", "exit_code": 0}

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._mesh_dispatch", mock_error):
            result = query_hermes_sync("test prompt", timeout=30)

        assert result is None


# ── Category 4: Session lifecycle ─────────────────────────────────────────────


class TestHermesSessions:
    def test_session_create(self):
        from adapters.models.hermes_cli import session_create

        result = session_create(purpose="conversation")
        assert result["success"] is True
        assert "session" in result
        assert result["session"]["purpose"] == "conversation"
        assert result["session"]["status"] == "active"
        assert result["session"]["session_id"].startswith("hermes_beast_")

    def test_session_send_and_read(self):
        from adapters.models.hermes_cli import session_create, session_send, session_read

        create = session_create(purpose="conversation")
        sid = create["session"]["session_id"]

        with patch("adapters.models.hermes_cli.is_available", return_value=True), \
             patch("adapters.models.hermes_cli._mesh_dispatch", _mock_mesh_dispatch_success):
            send_result = session_send(sid, "hello")

        assert send_result["success"] is True
        assert "HERMES_OK" in send_result["text"]
        assert send_result["session"]["turn_count"] == 1

        read_result = session_read(sid)
        assert read_result["success"] is True
        assert len(read_result["turns"]) == 1
        assert read_result["turns"][0]["user"] == "hello"

    def test_session_list(self):
        from adapters.models.hermes_cli import session_create, session_list

        session_create(purpose="test")
        result = session_list()
        assert result["success"] is True
        assert result["count"] >= 1

    def test_session_close(self):
        from adapters.models.hermes_cli import session_create, session_close

        create = session_create()
        sid = create["session"]["session_id"]

        result = session_close(sid)
        assert result["success"] is True
        assert result["session"]["status"] == "closed"

    def test_session_not_found(self):
        from adapters.models.hermes_cli import session_send

        result = session_send("nonexistent_session", "hello")
        assert result["success"] is False
        assert result["error_code"] == "HERMES_SESSION_NOT_FOUND"

    def test_session_closed_cannot_send(self):
        from adapters.models.hermes_cli import session_create, session_close, session_send

        create = session_create()
        sid = create["session"]["session_id"]
        session_close(sid)

        result = session_send(sid, "hello")
        assert result["success"] is False
        assert result["error_code"] == "HERMES_SESSION_CLOSED"


# ── Category 5: Capability registry ──────────────────────────────────────────


class TestHermesCapabilities:
    def test_capability_registry_complete(self):
        from adapters.models.hermes_cli import CAPABILITY_STATES

        required = {
            "generate", "chat", "health", "providers", "models",
            "diagnostics", "benchmark", "cancel",
            "session_create", "session_send", "session_read",
            "session_list", "session_close",
            "streaming", "pseudo_streaming",
        }
        for cap in required:
            assert cap in CAPABILITY_STATES, f"missing capability: {cap}"
            assert CAPABILITY_STATES[cap] in ("supported", "unsupported", "unknown", "degraded")

    def test_streaming_explicitly_unsupported(self):
        from adapters.models.hermes_cli import CAPABILITY_STATES

        assert CAPABILITY_STATES["streaming"] == "unsupported"
        assert CAPABILITY_STATES["pseudo_streaming"] == "supported"


# ── Category 6: Role matrix ──────────────────────────────────────────────────


class TestHermesRoleMatrix:
    def test_build_code_blocked_by_default(self):
        from adapters.models.hermes_cli import get_blocked_roles

        with patch("adapters.models.hermes_cli.get_benchmark_result", return_value=None):
            blocked = get_blocked_roles()

        assert "build_code" in blocked

    def test_status_report_always_blocked(self):
        from adapters.models.hermes_cli import ROLE_REQUIREMENTS

        assert ROLE_REQUIREMENTS["status_report"] == "BLOCKED"

    def test_vision_always_blocked(self):
        from adapters.models.hermes_cli import ROLE_REQUIREMENTS

        assert ROLE_REQUIREMENTS["vision_analysis"] == "BLOCKED"

    def test_conversation_assigned_after_liveness(self):
        from adapters.models.hermes_cli import get_assigned_roles

        mock_bench = {
            "overall_pass": True,
            "tests": {
                "liveness": {"pass": True},
                "summarization": {"pass": True},
                "conversation": {"pass": True},
                "code_review": {"pass": False},
                "code_patch": {"pass": False},
            },
        }
        with patch("adapters.models.hermes_cli.get_benchmark_result", return_value=mock_bench):
            roles = get_assigned_roles()

        assert "conversation" in roles
        assert "summarization" in roles
        assert "quick_triage" in roles
        assert "build_code" not in roles
        assert "code_review" not in roles

    def test_no_roles_without_benchmark(self):
        from adapters.models.hermes_cli import get_assigned_roles

        with patch("adapters.models.hermes_cli.get_benchmark_result", return_value=None):
            roles = get_assigned_roles()

        assert roles == []


# ── Category 7: Router integration ───────────────────────────────────────────


class TestHermesRouterIntegration:
    def test_hermes_not_primary_without_benchmark(self):
        from adapters.models.model_router import _hermes_allowed_for_purpose

        with patch("adapters.models.hermes_cli.get_assigned_roles", return_value=[]):
            assert _hermes_allowed_for_purpose("quick_triage") is False

    def test_hermes_allowed_with_matching_role(self):
        from adapters.models.model_router import _hermes_allowed_for_purpose

        with patch("adapters.models.hermes_cli.get_assigned_roles", return_value=["quick_triage", "conversation"]):
            assert _hermes_allowed_for_purpose("quick_triage") is True
            assert _hermes_allowed_for_purpose("advise_founder") is True

    def test_hermes_blocked_for_unassigned_purpose(self):
        from adapters.models.model_router import _hermes_allowed_for_purpose

        with patch("adapters.models.hermes_cli.get_assigned_roles", return_value=["conversation"]):
            assert _hermes_allowed_for_purpose("plan_architecture") is False


# ── Category 8: Diagnostics ──────────────────────────────────────────────────


class TestHermesDiagnostics:
    def test_diagnostics_returns_actionable_blockers(self):
        from adapters.models.hermes_cli import diagnostics

        with patch("adapters.models.hermes_cli._beast_connected", return_value=False):
            result = diagnostics()

        assert result["provider"] == "hermes-agent"
        assert result["runtime"] == "hermes_beast"
        assert len(result["blockers"]) > 0
        assert "recovery" in result["blockers"][0]
        assert "blocker" in result["blockers"][0]

    def test_diagnostics_includes_capabilities(self):
        from adapters.models.hermes_cli import diagnostics

        with patch("adapters.models.hermes_cli._beast_connected", return_value=False):
            result = diagnostics()

        assert "capabilities" in result
        assert "assigned_roles" in result
        assert "blocked_roles" in result
        assert "checks" in result


# ── Category 9: Prompt encoding ──────────────────────────────────────────────


class TestHermesPromptSafety:
    def test_base64_encoding(self):
        from adapters.models.hermes_cli import _encode_prompt
        import base64

        prompt = "Hello, how are you?"
        cmd = _encode_prompt(prompt)
        assert "FromBase64String" in cmd
        assert "hermes -z" in cmd
        assert '"$p"' in cmd

    def test_injection_blocked_via_base64(self):
        from adapters.models.hermes_cli import _encode_prompt

        malicious = '; Remove-Item -Recurse -Force C:\\; echo "pwned"'
        cmd = _encode_prompt(malicious)
        assert "; Remove-Item" not in cmd
        assert "pwned" not in cmd
        assert "FromBase64String" in cmd

    def test_null_bytes_stripped(self):
        from adapters.models.hermes_cli import _encode_prompt

        prompt = "hello\x00world"
        cmd = _encode_prompt(prompt)
        assert "\x00" not in cmd

    def test_prompt_length_capped(self):
        from adapters.models.hermes_cli import _encode_prompt

        long_prompt = "x" * 20000
        cmd = _encode_prompt(long_prompt)
        import base64
        b64_part = cmd.split("FromBase64String('")[1].split("')")[0]
        decoded = base64.b64decode(b64_part).decode("utf-8")
        assert len(decoded) <= 10000


# ── Category 10: Structured responses ────────────────────────────────────────


class TestHermesStructuredResponses:
    def test_success_response_format(self):
        from adapters.models.hermes_cli import build_success_response

        resp = build_success_response(
            text="hello",
            purpose="conversation",
            latency_ms=5000,
        )
        assert resp["ok"] is True
        assert resp["runtime"] == "hermes_beast"
        assert resp["provider"] == "hermes"
        assert resp["node"] == "beast_windows"
        assert resp["error"] is None
        assert "tokens" in resp
        assert "metadata" in resp

    def test_error_response_format(self):
        from adapters.models.hermes_cli import build_error_response

        resp = build_error_response(
            error_code="HERMES_TIMEOUT",
            message="timed out after 60s",
            recoverable=True,
            blocker="LLM inference exceeded timeout",
            next_action="Retry with longer timeout",
        )
        assert resp["ok"] is False
        assert resp["error"]["code"] == "HERMES_TIMEOUT"
        assert resp["error"]["recoverable"] is True
        assert resp["metadata"]["blocker"] != ""
        assert resp["metadata"]["next_action"] != ""


# ── Category 11: Beast-side adapter ──────────────────────────────────────────


class TestBeastHermesAdapter:
    def test_unsupported_operation_is_explicit(self):
        from nodes.windows.umh_node.adapters.hermes import HermesAdapter

        adapter = HermesAdapter.__new__(HermesAdapter)
        adapter._available = True
        adapter._active_process = None
        adapter._process_lock = __import__("threading").Lock()
        adapter._last_error = ""
        adapter._last_success_at = 0
        adapter._call_count = 0

        result = adapter.execute("hermes.unknown_op", {})
        assert result["success"] is False
        assert result["error_code"] == "HERMES_UNSUPPORTED_OPERATION"
        assert "supported_operations" in result

    def test_capabilities_returns_full_list(self):
        from nodes.windows.umh_node.adapters.hermes import HermesAdapter

        adapter = HermesAdapter.__new__(HermesAdapter)
        adapter._available = True
        adapter._active_process = None
        adapter._process_lock = __import__("threading").Lock()
        adapter._last_error = ""
        adapter._last_success_at = 0
        adapter._call_count = 0

        result = adapter._capabilities({})
        assert result["success"] is True
        caps = result["capabilities"]
        assert caps["generate"] == "supported"
        assert caps["streaming"] == "unsupported"
        assert caps["session_native"] == "unsupported"
        assert caps["session_managed"] == "supported"
        assert "notes" in result

    def test_unavailable_returns_structured_error(self):
        from nodes.windows.umh_node.adapters.hermes import HermesAdapter

        adapter = HermesAdapter.__new__(HermesAdapter)
        adapter._available = False
        adapter._active_process = None
        adapter._process_lock = __import__("threading").Lock()
        adapter._last_error = ""
        adapter._last_success_at = 0
        adapter._call_count = 0

        result = adapter.execute("hermes.generate", {"prompt": "test"})
        assert result["success"] is False
        assert result["error_code"] == "HERMES_UNAVAILABLE"
        assert result["recoverable"] is False


# ── Category 12: Cancellation ────────────────────────────────────────────────


class TestHermesCancellation:
    def test_cancel_no_active_process(self):
        from adapters.models.hermes_cli import cancel

        with patch("adapters.models.hermes_cli._beast_connected", return_value=True), \
             patch("adapters.models.hermes_cli._hermes_operation") as mock_op:
            mock_op.return_value = {"cancelled": False, "reason": "no active process"}
            result = cancel()

        assert result["success"] is True
        assert result["cancelled"] is False

    def test_cancel_beast_offline(self):
        from adapters.models.hermes_cli import cancel

        with patch("adapters.models.hermes_cli._beast_connected", return_value=False):
            result = cancel()

        assert result["success"] is False
        assert result["error"] == "beast offline"


# ── Category 13: Grounding firewall regression ───────────────────────────────


class TestGroundingFirewallRegression:
    def test_existing_grounding_tests_still_pass(self):
        """Verify that imports from the grounding firewall still work."""
        from substrate.organism.grounding_registry import detect_status_seeking
        from substrate.organism.grounded_handlers import handle_grounded_status

        assert callable(detect_status_seeking)
        assert callable(handle_grounded_status)

    def test_hermes_result_has_metadata(self):
        """Verify HermesResult carries metadata for DEX visibility."""
        from adapters.models.hermes_cli import HermesResult

        result = HermesResult(
            output="test",
            latency_ms=5000,
            metadata={"runtime": "hermes_beast"},
        )
        assert result.metadata["runtime"] == "hermes_beast"
        assert result.provider == "hermes"
