"""P0 smoke tests — fast import/health checks for all production services.

Run with: pytest tests/test_p0_smoke.py -m smoke
"""

import importlib
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

_REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.smoke


# ── Discord bot import chain ─────────────────────────────────────────────────

class TestDiscordBotImports:
    def test_gateway_imports(self):
        from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway
        assert EntrepreneurOSGateway is not None

    def test_context_loader_safe(self):
        from substrate.state.context.context import try_load_context_from_env
        result = try_load_context_from_env()
        assert result is None or hasattr(result, "org_id")

    def test_message_handlers_importable(self):
        import services.discord_message_handlers as h
        assert hasattr(h, "__name__")

    def test_bot_commands_importable(self):
        import services.discord_bot_commands as c
        assert hasattr(c, "__name__")

    def test_signal_factory_importable(self):
        from transports.discord.signal_factory import message_to_signal
        assert callable(message_to_signal)

    def test_discord_utils_importable(self):
        from transports.discord.discord_utils import chunk_message, post_to_webhook
        assert callable(chunk_message)
        assert callable(post_to_webhook)


# ── Operator API ─────────────────────────────────────────────────────────────

class TestOperatorAPI:
    def test_operator_module_importable(self):
        spec = importlib.util.find_spec("transports.api.operator")
        assert spec is not None, "transports.api.operator module not found"

    def test_legacy_operator_module_importable(self):
        spec = importlib.util.find_spec("services.operator_api")
        assert spec is not None, "services.operator_api module not found"


# ── Webhook service ──────────────────────────────────────────────────────────

class TestWebhookService:
    def test_higgsfield_webhook_importable(self):
        from services.higgsfield_webhook import register
        assert callable(register)

    def test_higgsfield_handle_webhook(self):
        from services.higgsfield_webhook import handle_webhook
        assert callable(handle_webhook)


# ── Node mesh ────────────────────────────────────────────────────────────────

class TestNodeMesh:
    def _make_node(self, node_id: str = "test-smoke"):
        from transports.node_mesh.integration.types import ConnectedNode
        return ConnectedNode(
            node_id=node_id,
            hostname="smoke",
            os="linux",
            os_version="6.8",
            capabilities=[],
            daemon_version="0.1.0",
            tailscale_ip="100.0.0.1",
            ws=MagicMock(),
        )

    def test_registry_import(self):
        from transports.node_mesh.registry import NodeRegistry
        assert NodeRegistry is not None

    def test_registry_crud(self):
        from transports.node_mesh.registry import NodeRegistry
        reg = NodeRegistry()
        node = self._make_node()
        reg.add(node)
        assert reg.node_count() == 1
        assert reg.get("test-smoke") is not None
        removed = reg.remove("test-smoke")
        assert removed is not None
        assert reg.node_count() == 0

    def test_registry_no_deadlock_on_heartbeat(self):
        """update_heartbeat must complete in <2s — deadlock = timeout."""
        from transports.node_mesh.registry import NodeRegistry
        reg = NodeRegistry()
        node = self._make_node("hb-test")
        reg.add(node)

        completed = threading.Event()

        def heartbeat():
            reg.update_heartbeat("hb-test", {"cpu": 0.5})
            completed.set()

        t = threading.Thread(target=heartbeat)
        t.start()
        assert completed.wait(timeout=2.0), "update_heartbeat deadlocked"
        t.join(timeout=1.0)
        reg.remove("hb-test")

    def test_registry_uses_plain_lock(self):
        """RLock was masking the nested-lock bug — verify Lock is used."""
        from transports.node_mesh.registry import NodeRegistry
        reg = NodeRegistry()
        assert isinstance(reg._lock, type(threading.Lock()))


# ── Substrate core ───────────────────────────────────────────────────────────

class TestSubstrateCore:
    def test_types_import(self):
        from substrate.types import SignalEnvelope
        assert SignalEnvelope is not None

    def test_substrate_class(self):
        from substrate import Substrate
        assert hasattr(Substrate, "execute")

    def test_model_router_importable(self):
        from adapters.models.model_router import call_with_fallback
        assert callable(call_with_fallback)

    def test_governance_importable(self):
        from substrate.control_plane.governance import GovernanceEngine
        assert GovernanceEngine is not None

    def test_execution_spine_importable(self):
        from substrate.execution.runtime.execution_spine import ExecutionSpine
        assert ExecutionSpine is not None


# ── Ghost env refs eliminated ────────────────────────────────────────────────

class TestNoGhostEnvRefs:
    @pytest.mark.parametrize("script", [
        "scripts/scheduled/nightly_maintenance.sh",
        "scripts/scheduled/morning_prep.sh",
        "scripts/scheduled/weekly_review.sh",
        "scripts/scheduled/nightly_consolidation.sh",
        "scripts/auth_monitor/credential_watcher.sh",
        "scripts/auth_monitor/session_resurrector.sh",
        "scripts/auth_monitor/health_check.sh",
        "scripts/auth_monitor/credential_coordinator.sh",
    ])
    def test_no_runtime_env_ref(self, script):
        content = (_REPO_ROOT / script).read_text()
        assert "runtime/.env" not in content, f"{script} still references runtime/.env"

    def test_discord_bot_no_runtime_env(self):
        content = (_REPO_ROOT / "services" / "discord_bot.py").read_text()
        assert "runtime/.env" not in content
