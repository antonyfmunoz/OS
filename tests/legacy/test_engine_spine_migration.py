"""Tests — Engine-layer CognitiveLoop→ExecutionSpine migration.

Verifies that the 6 engine modules now use ExecutionSpine instead of
CognitiveLoop, and that downstream return handling works with string
output instead of CognitiveResult.

Source-level assertions + import verification + mock-based integration.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import ast
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Source-level assertions: CognitiveLoop removed from runtime code
# ---------------------------------------------------------------------------

_ENGINE_FILES = [
    "eos/coordination_engine.py",
    "eos/user_model.py",
    "eos/strategy_engine.py",
    "eos/reality_engine.py",
    "eos/evolution_engine.py",
    "eos/research_engine.py",
]


def _get_imports(filepath: str) -> list[str]:
    """Parse AST to get all imported names (not strings in comments/docstrings)."""
    source = Path(filepath).read_text()
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    names.append(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
    return names


class TestCognitiveLoopRemoved:
    """Confirm CognitiveLoop is not imported in any migrated engine module."""

    def test_no_cognitive_loop_import_in_engines(self):
        for relpath in _ENGINE_FILES:
            filepath = f"/opt/OS/{relpath}"
            imports = _get_imports(filepath)
            cl_imports = [i for i in imports if "CognitiveLoop" in i]
            assert cl_imports == [], (
                f"{relpath} still imports CognitiveLoop: {cl_imports}"
            )

    def test_execution_spine_imported_in_engines(self):
        for relpath in _ENGINE_FILES:
            filepath = f"/opt/OS/{relpath}"
            imports = _get_imports(filepath)
            spine_imports = [i for i in imports if "ExecutionSpine" in i]
            assert len(spine_imports) > 0, f"{relpath} does not import ExecutionSpine"

    def test_context_builder_imported_in_engines(self):
        for relpath in _ENGINE_FILES:
            filepath = f"/opt/OS/{relpath}"
            imports = _get_imports(filepath)
            cb_imports = [i for i in imports if "ContextBuilder" in i]
            assert len(cb_imports) > 0, f"{relpath} does not import ContextBuilder"


# ---------------------------------------------------------------------------
# No self.loop attribute in migrated engines
# ---------------------------------------------------------------------------


class TestNoLoopAttribute:
    """Engines should no longer store self.loop = CognitiveLoop(ctx)."""

    def test_strategy_engine_no_loop(self):
        source = Path("/opt/OS/eos/strategy_engine.py").read_text()
        assert "self.loop" not in source.split("class DecisionEngine")[0], (
            "StrategyEngine still has self.loop"
        )

    def test_reality_engine_no_loop(self):
        source = Path("/opt/OS/eos/reality_engine.py").read_text()
        assert "self.loop" not in source

    def test_evolution_engine_no_loop(self):
        source = Path("/opt/OS/eos/evolution_engine.py").read_text()
        assert "self.loop" not in source

    def test_research_engine_no_loop(self):
        source = Path("/opt/OS/eos/research_engine.py").read_text()
        assert "self.loop" not in source

    def test_user_model_no_loop(self):
        source = Path("/opt/OS/eos/user_model.py").read_text()
        assert "self.loop" not in source


# ---------------------------------------------------------------------------
# Integration: engine calls route through ExecutionSpine
# ---------------------------------------------------------------------------


def _mock_spine_run(return_value="Mocked spine output."):
    """Patch ExecutionSpine.run to return a controlled string."""
    return patch(
        "umh.runtime_engine.execution_spine.ExecutionSpine.run",
        return_value=return_value,
    )


def _mock_context_builder():
    """Patch ContextBuilder.build to return a fake unified context."""
    mock_uc = MagicMock()
    mock_uc.to_system_prompt.return_value = "test system prompt"
    return patch(
        "umh.runtime_engine.context_builder.ContextBuilder.build",
        return_value=mock_uc,
    )


class _FakeCtx:
    org_id = "test_org"
    user_id = "test_user"
    active_venture_id = "test_venture"
    portfolio_id = None
    ventures = []


class TestCoordinationEngineSpine:
    """Verify CoordinationEngine.ceo_delegate uses ExecutionSpine."""

    def test_ceo_delegate_calls_spine(self):
        json_response = '[{"description": "Test task", "executor": "human", "priority": "normal", "estimated_time": "30 min"}]'
        with _mock_spine_run(json_response) as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.coordination_engine.get_conn"):
                    with patch("umh.runtime_engine.coordination_engine.AuthorityEngine"):
                        from umh.runtime_engine.coordination_engine import CoordinationEngine

                        ce = CoordinationEngine.__new__(CoordinationEngine)
                        ce.ctx = _FakeCtx()
                        ce.event_bus = MagicMock()
                        ce.authority = MagicMock()
                        result = ce.ceo_delegate("Test objective", "test_venture")
        m_spine.assert_called_once()
        assert isinstance(result, dict)


class TestStrategyEngineSpine:
    """Verify StrategyEngine methods use ExecutionSpine."""

    def test_analyze_company_position_returns_parsed_dict(self):
        mock_output = (
            "CURRENT_POSITION: Pre-revenue.\n"
            "BINDING_CONSTRAINT: No paying customers.\n"
            "STRATEGIC_OPPORTUNITIES: Direct outreach.\n"
            "WHAT_TO_STOP: Content marketing.\n"
            "90_DAY_PRIORITY: Close first sale.\n"
            "COMPETITIVE_POSITION: Undifferentiated."
        )
        with _mock_spine_run(mock_output) as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.strategy_engine.VentureKnowledgeBase"):
                    with patch(
                        "umh.runtime_engine.strategy_engine._query_30d_stats",
                        return_value={
                            "interactions_30d": 0,
                            "total_tokens_30d": 0,
                            "positive_outcomes": 0,
                            "total_outcomes": 0,
                            "agents_active": 0,
                            "reply_rate": None,
                            "last_activity": "none",
                        },
                    ):
                        from umh.runtime_engine.strategy_engine import StrategyEngine

                        se = StrategyEngine.__new__(StrategyEngine)
                        se.ctx = _FakeCtx()
                        se.memory = MagicMock()
                        result = se.analyze_company_position("test_org")

        m_spine.assert_called_once()
        assert "current_position" in result
        assert "binding_constraint" in result
        assert result["raw_output"] == mock_output


class TestDecisionEngineSpine:
    """Verify DecisionEngine.evaluate uses ExecutionSpine for each step."""

    def test_evaluate_calls_spine_6_times(self):
        with _mock_spine_run("Step analysis result.") as m_spine:
            with _mock_context_builder():
                from umh.runtime_engine.strategy_engine import DecisionEngine, StrategyEngine

                de = DecisionEngine.__new__(DecisionEngine)
                de.ctx = _FakeCtx()
                de.strategy = StrategyEngine.__new__(StrategyEngine)
                de.strategy.ctx = _FakeCtx()
                de.memory = MagicMock()
                result = de.evaluate(
                    decision="Should I run paid ads?",
                    context={"revenue": 0},
                    venture_id="test_venture",
                )

        assert m_spine.call_count == 6
        assert "step1_context" in result
        assert "step6_recommendation" in result


class TestUserModelSpine:
    """Verify UserModel.build_communication_profile uses ExecutionSpine."""

    def test_build_profile_calls_spine(self):
        mock_json = '{"communication_style": "direct", "common_shorthand": [], "frequent_ambiguities": [], "decision_style": "fast"}'
        with _mock_spine_run(mock_json) as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.user_model.get_conn") as m_conn:
                    cursor = MagicMock()
                    cursor.fetchall.return_value = [
                        {
                            "input_summary": f"run the daily outreach sequence variant {i}",
                            "task_type": "generate",
                            "agent_label": "ea",
                            "created_at": "2026-01-01",
                        }
                        for i in range(15)
                    ]
                    cursor.fetchone.return_value = {"cnt": 50}
                    m_conn.return_value.__enter__ = MagicMock(return_value=cursor)
                    m_conn.return_value.__exit__ = MagicMock(return_value=False)

                    from umh.runtime_engine.user_model import UserModel

                    um = UserModel.__new__(UserModel)
                    um.ctx = _FakeCtx()
                    um._runtime = MagicMock()
                    result = um.build_communication_profile()

        m_spine.assert_called_once()
        assert "communication_style" in result
        assert result["communication_style"] == "direct"


# ---------------------------------------------------------------------------
# Slice 4: business_instance, onboarding_backfill, context_compaction
# ---------------------------------------------------------------------------

_SLICE4_FILES = [
    "eos/business_instance.py",
    "eos/onboarding_backfill.py",
    "eos/context_compaction.py",
]


class TestSlice4CognitiveLoopRemoved:
    """Confirm CognitiveLoop is fully absent from slice 4 files."""

    def test_no_cognitive_loop_import_in_slice4(self):
        for relpath in _SLICE4_FILES:
            filepath = f"/opt/OS/{relpath}"
            imports = _get_imports(filepath)
            cl_imports = [i for i in imports if "CognitiveLoop" in i]
            assert cl_imports == [], (
                f"{relpath} still imports CognitiveLoop: {cl_imports}"
            )

    def test_no_cognitive_loop_string_in_slice4(self):
        for relpath in _SLICE4_FILES:
            filepath = f"/opt/OS/{relpath}"
            source = Path(filepath).read_text()
            assert "CognitiveLoop" not in source, (
                f"{relpath} still contains CognitiveLoop reference"
            )


class TestSlice4SpineImported:
    """Confirm ExecutionSpine is used in all slice 4 files."""

    def test_execution_spine_in_business_instance(self):
        source = Path("/opt/OS/eos/business_instance.py").read_text()
        assert "ExecutionSpine" in source

    def test_execution_spine_in_onboarding_backfill(self):
        source = Path("/opt/OS/eos/onboarding_backfill.py").read_text()
        assert "ExecutionSpine" in source

    def test_execution_spine_in_context_compaction(self):
        source = Path("/opt/OS/eos/context_compaction.py").read_text()
        assert "ExecutionSpine" in source

    def test_context_builder_in_all_slice4(self):
        for relpath in _SLICE4_FILES:
            source = Path(f"/opt/OS/{relpath}").read_text()
            assert "ContextBuilder" in source, (
                f"{relpath} does not reference ContextBuilder"
            )


class TestSlice4NoSelfLoop:
    """No self.loop attribute in slice 4 modules."""

    def test_onboarding_backfill_no_loop(self):
        source = Path("/opt/OS/eos/onboarding_backfill.py").read_text()
        assert "self.loop" not in source


class TestBusinessInstanceSpine:
    """Verify BusinessInstanceManager.create_from_wizard uses ExecutionSpine."""

    def test_create_from_wizard_calls_spine_for_gaps(self):
        gap_json = '{"offer_promise": "Transform your career", "icp_description": "Ambitious professionals", "market_position": "Emerging leader"}'
        with _mock_spine_run(gap_json) as m_spine:
            with _mock_context_builder():
                from umh.workstation.business import BusinessInstanceManager

                bim = BusinessInstanceManager.__new__(BusinessInstanceManager)
                bim.ctx = _FakeCtx()
                bim.save_bis = MagicMock()

                result = bim.create_from_wizard(
                    {
                        "venture_id": "test_v",
                        "name": "Test Co",
                        "industry": "tech",
                        "business_model": "saas",
                    }
                )

        m_spine.assert_called_once()
        assert result.offer_promise == "Transform your career"
        assert result.icp_description == "Ambitious professionals"
        assert result.market_position == "Emerging leader"

    def test_create_from_wizard_no_spine_when_no_gaps(self):
        """If all key fields are provided, spine should not be called."""
        with _mock_spine_run("{}") as m_spine:
            with _mock_context_builder():
                from umh.workstation.business import BusinessInstanceManager

                bim = BusinessInstanceManager.__new__(BusinessInstanceManager)
                bim.ctx = _FakeCtx()
                bim.save_bis = MagicMock()

                result = bim.create_from_wizard(
                    {
                        "venture_id": "test_v",
                        "name": "Test Co",
                        "industry": "tech",
                        "business_model": "saas",
                        "offer_promise": "Already filled",
                        "icp_description": "Already filled",
                        "market_position": "Already filled",
                    }
                )

        m_spine.assert_not_called()
        assert result.offer_promise == "Already filled"


class TestOnboardingBackfillSpine:
    """Verify OnboardingBackfill._build_knowledge_base uses ExecutionSpine."""

    def test_build_knowledge_base_calls_spine(self):
        summary_text = "This business does XYZ with key contacts ABC."
        with _mock_spine_run(summary_text) as m_spine:
            with _mock_context_builder():
                from umh.runtime_engine.onboarding_backfill import OnboardingBackfill

                ob = OnboardingBackfill.__new__(OnboardingBackfill)
                ob.ctx = _FakeCtx()
                ob.results = {
                    "drive_docs": 5,
                    "gmail_contacts": 10,
                    "calendar_events": 20,
                    "calendar_contacts": 8,
                    "crm_leads": 3,
                }

                with patch("umh.runtime_engine.memory.AgentMemory") as m_mem:
                    m_mem.return_value.log_event = MagicMock()
                    ob._build_knowledge_base("test_venture")

        m_spine.assert_called_once()
        assert ob.results["knowledge_summary"] == summary_text[:300]


class TestContextCompactorSpine:
    """Verify ContextCompactor.compact uses ExecutionSpine."""

    def test_compact_calls_spine_and_parses_json(self):
        brief_json = json.dumps(
            {
                "who_user_is": "A founder building an AI system",
                "decisions_made": ["Use Python", "Deploy on VPS"],
                "open_loops": ["Pricing model"],
                "critical_facts": ["Pre-revenue stage"],
                "last_action": "Built onboarding",
                "next_intent": "Run first outreach",
            }
        )
        with _mock_spine_run(brief_json) as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.context_compaction.get_conn") as m_conn:
                    cursor = MagicMock()
                    cursor.fetchone.side_effect = [
                        {"cnt": 0},  # generation count query
                        {"id": "fake-uuid"},  # INSERT RETURNING
                    ]
                    m_conn.return_value.__enter__ = MagicMock(return_value=cursor)
                    m_conn.return_value.__exit__ = MagicMock(return_value=False)

                    from umh.runtime_engine.context_compaction import ContextCompactor

                    cc = ContextCompactor.__new__(ContextCompactor)
                    cc.ctx = _FakeCtx()

                    messages = [
                        {"role": "user", "content": f"Message {i}"} for i in range(50)
                    ]
                    result = cc.compact(messages, "test-session-id")

        m_spine.assert_called_once()
        assert result["who_user_is"] == "A founder building an AI system"
        assert "Use Python" in result["decisions_made"]
        assert result["next_intent"] == "Run first outreach"

    def test_compact_handles_non_json_spine_output(self):
        """If spine returns non-JSON, should fall back to storing raw output."""
        with _mock_spine_run("This is not JSON at all.") as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.context_compaction.get_conn") as m_conn:
                    cursor = MagicMock()
                    cursor.fetchone.side_effect = [
                        {"cnt": 0},
                        {"id": "fake-uuid"},
                    ]
                    m_conn.return_value.__enter__ = MagicMock(return_value=cursor)
                    m_conn.return_value.__exit__ = MagicMock(return_value=False)

                    from umh.runtime_engine.context_compaction import ContextCompactor

                    cc = ContextCompactor.__new__(ContextCompactor)
                    cc.ctx = _FakeCtx()

                    messages = [{"role": "user", "content": "Hello"}]
                    result = cc.compact(messages, "test-session-id")

        m_spine.assert_called_once()
        assert result["last_action"] == "This is not JSON at all."


# ---------------------------------------------------------------------------
# Slice 5: voice_interface + telegram media path (final multimodal callers)
# ---------------------------------------------------------------------------

_SLICE5_FILES = [
    "eos/voice_interface.py",
    "services/telegram_control.py",
]


class TestSlice5CognitiveLoopRemoved:
    """Confirm CognitiveLoop is fully absent from slice 5 runtime files."""

    def test_no_cognitive_loop_import_in_voice_interface(self):
        filepath = "/opt/OS/eos/voice_interface.py"
        imports = _get_imports(filepath)
        cl_imports = [i for i in imports if "CognitiveLoop" in i]
        assert cl_imports == [], (
            f"voice_interface.py still imports CognitiveLoop: {cl_imports}"
        )

    def test_no_cognitive_loop_import_in_telegram_control(self):
        source = Path("/opt/OS/services/telegram_control.py").read_text()
        assert "from umh.runtime_engine.cognitive_loop import CognitiveLoop" not in source

    def test_no_cognitive_loop_instantiation_in_voice_interface(self):
        source = Path("/opt/OS/eos/voice_interface.py").read_text()
        assert "CognitiveLoop(" not in source

    def test_no_cognitive_loop_instantiation_in_telegram_control(self):
        source = Path("/opt/OS/services/telegram_control.py").read_text()
        assert "CognitiveLoop(" not in source

    def test_no_self_loop_in_voice_interface(self):
        source = Path("/opt/OS/eos/voice_interface.py").read_text()
        assert "self.loop" not in source


class TestSlice5SpineUsed:
    """Confirm ExecutionSpine is used in voice and telegram paths."""

    def test_execution_spine_in_voice_interface(self):
        source = Path("/opt/OS/eos/voice_interface.py").read_text()
        assert "ExecutionSpine" in source
        assert "ContextBuilder" in source

    def test_execution_spine_in_telegram_media_handler(self):
        source = Path("/opt/OS/services/telegram_control.py").read_text()
        assert "ExecutionSpine" in source
        assert "ContextBuilder" in source


class TestSlice5NoCognitiveLoopAnywhere:
    """Global assertion: no CognitiveLoop instantiation in production code."""

    def test_zero_live_cognitive_loop_instantiations(self):
        """CognitiveLoop() should only appear in cognitive_loop.py and test files."""
        import os

        violations = []
        for root, _dirs, files in os.walk("/opt/OS"):
            if "/.git/" in root or "/__pycache__/" in root:
                continue
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                relpath = os.path.relpath(fpath, "/opt/OS")
                # Skip cognitive_loop itself and test files
                if relpath == "eos/cognitive_loop.py":
                    continue
                if "/tests/" in relpath or relpath.startswith("tests/"):
                    continue
                content = Path(fpath).read_text()
                if "CognitiveLoop(" in content:
                    violations.append(relpath)
        assert violations == [], f"CognitiveLoop still instantiated in: {violations}"


class TestVoiceInterfaceSpine:
    """Verify VoiceInterface methods use ExecutionSpine via _spine_call."""

    def test_process_voice_turn_calls_spine(self):
        with _mock_spine_run("I can help you with that.") as m_spine:
            with _mock_context_builder():
                from umh.runtime_engine.voice_interface import VoiceInterface

                vi = VoiceInterface.__new__(VoiceInterface)
                vi.ctx = _FakeCtx()
                vi.processor = MagicMock()
                vi.processor._local_transcribe.return_value = (
                    "What should I focus on today?"
                )
                vi.processor.synthesize_speech.return_value = "/tmp/response.wav"
                vi._session_transcript = []

                result = vi.process_voice_turn("/tmp/test.wav")

        m_spine.assert_called_once()
        assert result["transcript"] == "What should I focus on today?"
        assert result["response_text"] == "I can help you with that."
        assert result["response_audio_path"] == "/tmp/response.wav"
        assert result["model_used"] == "spine"

    def test_get_meeting_brief_calls_spine(self):
        with _mock_spine_run("Focus on closing the lead.") as m_spine:
            with _mock_context_builder():
                from umh.runtime_engine.voice_interface import VoiceInterface

                vi = VoiceInterface.__new__(VoiceInterface)
                vi.ctx = _FakeCtx()
                vi.MEETING_CONTEXTS = VoiceInterface.MEETING_CONTEXTS

                result = vi.get_meeting_brief("sales_call", "test_venture")

        m_spine.assert_called_once()
        assert "Focus on closing the lead." in result

    def test_end_meeting_session_calls_spine(self):
        mock_output = (
            "SUMMARY:\nGood meeting about strategy.\n\n"
            "DECISIONS:\n- Move to phase 2\n\n"
            "ACTION ITEMS:\n- Antony: Draft proposal\n\n"
            "NEXT STEPS:\n- Follow up Friday\n"
        )
        with _mock_spine_run(mock_output) as m_spine:
            with _mock_context_builder():
                with patch("umh.runtime_engine.memory.AgentMemory"):
                    from umh.runtime_engine.voice_interface import VoiceInterface

                    vi = VoiceInterface.__new__(VoiceInterface)
                    vi.ctx = _FakeCtx()
                    vi._session_transcript = [
                        {"text": "Let's discuss the next phase.", "role": "user"},
                        {"text": "I recommend moving to phase 2.", "role": "assistant"},
                    ]

                    result = vi.end_meeting_session("test-session-id")

        m_spine.assert_called_once()
        assert "Good meeting" in result["summary"]
        assert len(result["action_items"]) > 0

    def test_during_meeting_objections_calls_spine(self):
        with _mock_spine_run("1. Price too high - reframe value") as m_spine:
            with _mock_context_builder():
                from umh.runtime_engine.voice_interface import VoiceInterface

                vi = VoiceInterface.__new__(VoiceInterface)
                vi.ctx = _FakeCtx()

                result = vi.get_during_meeting_context(
                    "sales_call", "objections", "sess-1"
                )

        m_spine.assert_called_once()
        assert "Price too high" in result


class TestTelegramMediaPathSpine:
    """Verify telegram media handler uses MediaProcessor + ExecutionSpine."""

    def test_media_handler_no_multimodal_input_import(self):
        source = Path("/opt/OS/services/telegram_control.py").read_text()
        assert "MultimodalInput" not in source

    def test_media_handler_uses_media_processor(self):
        source = Path("/opt/OS/services/telegram_control.py").read_text()
        assert "MediaProcessor" in source
        assert "mp.process(" in source


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
