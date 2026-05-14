"""Migration pin: Phase 75B governed execution spine.

Pins §34 item 6: Input → Control Plane → Identity → Governance →
Backend Registry → Canonical Execution Engine → Trace Store → Result.

The spine (runtime.execution_spine.ExecutionSpine) uses lazy imports
for context/authority/model_router. Tests mock at the source module
level.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from execution.runtime.execution_spine import ExecutionSpine

pytestmark = pytest.mark.migration


class TestSpineImports:
    def test_execution_spine_importable(self):
        assert ExecutionSpine is not None

    def test_spine_has_run_method(self):
        assert hasattr(ExecutionSpine, "run")

    def test_run_signature_accepts_required_params(self):
        import inspect

        sig = inspect.signature(ExecutionSpine.run)
        params = list(sig.parameters.keys())
        assert "message" in params
        assert "unified_context" in params
        assert "agent_type" in params
        assert "authority_class" in params


class TestSpineAuthorityGate:
    def test_spine_blocks_critical_action(self):
        spine = ExecutionSpine()
        mock_ctx = MagicMock()
        mock_ctx.to_system_prompt.return_value = "test prompt"

        mock_ae = MagicMock()
        mock_ae.check_can_execute.return_value = {
            "can_execute": False,
            "requires_approval": True,
            "reason": "CRITICAL action",
            "risk_class": "CRITICAL",
            "autonomy_level": 1,
        }
        mock_ae.queue_for_approval.return_value = "approval-123"

        with (
            patch("runtime.context.load_context_from_env") as mock_load,
            patch("governance.policy.authority_engine.AuthorityEngine") as mock_ae_cls,
        ):
            mock_ae_cls.return_value = mock_ae

            result = spine.run(
                message="send_message to all users",
                unified_context=mock_ctx,
                authority_class="send_message",
            )

            mock_ae.check_can_execute.assert_called_once_with("send_message")
            assert "approval" in result.lower()
            assert "approval-123" in result

    def test_spine_proceeds_on_low_risk(self):
        spine = ExecutionSpine()
        mock_ctx = MagicMock()
        mock_ctx.to_system_prompt.return_value = "test prompt"

        mock_ae = MagicMock()
        mock_ae.check_can_execute.return_value = {
            "can_execute": True,
            "requires_approval": False,
            "reason": "LOW action",
            "risk_class": "LOW",
            "autonomy_level": 1,
        }

        mock_routing_result = MagicMock()
        mock_routing_result.output = "LLM response text"

        with (
            patch("runtime.context.load_context_from_env"),
            patch("governance.policy.authority_engine.AuthorityEngine") as mock_ae_cls,
            patch(
                "execution.runtime.model_router.call_with_fallback",
                return_value=mock_routing_result,
            ),
        ):
            mock_ae_cls.return_value = mock_ae

            result = spine.run(
                message="analyze this data",
                unified_context=mock_ctx,
                authority_class="analyze",
            )

            assert isinstance(result, str)
