"""End-to-end acceptance tests for the converged UMH substrate."""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[1])
# Insert at index 0 so the worktree's packages take priority over /opt/OS.
# substrate/execution/spine.py does sys.path.insert(0, "/opt/OS") which would
# otherwise shadow the worktree's projections/ package with the main repo's
# (older) projections/ package. Pre-importing projections here caches the
# worktree version in sys.modules before substrate is imported.
sys.path.insert(0, _ROOT)
import projections  # noqa: E402 — must precede substrate import
import projections.eos  # noqa: E402
import projections.eos.agents  # noqa: E402

import pytest
from substrate import Substrate
from substrate.types import (
    ComponentType,
    ExecutionOutcome,
    SignalEnvelope,
    SignalSource,
)


class TestConvergenceAcceptance:
    @pytest.fixture
    def substrate(self):
        return Substrate()

    @pytest.mark.asyncio
    async def test_signal_to_result(self, substrate):
        """Full lifecycle: signal → identity → context → governance → spine → result."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="hello, what can you do?",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert result.output != ""
        assert result.trace_id is not None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_governance_blocks_critical(self, substrate):
        """Critical action gets blocked by governance."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="send email to all customers with pricing update",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.outcome == ExecutionOutcome.BLOCKED

    @pytest.mark.asyncio
    async def test_deterministic_always_produces_output(self, substrate):
        """Even with no LLM, the system produces a response."""
        signal = SignalEnvelope(
            source=SignalSource.USER,
            content="analyze this data for me",
            user_id="test",
            organization_id="test-org",
        )
        result = await substrate.execute(signal)
        assert result.output != ""
        assert len(result.output) > 10

    def test_no_dataclasses_in_substrate_core(self):
        """Invariant: no @dataclass in substrate core (types, control_plane, execution/spine)."""
        import subprocess

        core_dirs = [
            "substrate/types.py",
            "substrate/execution/spine.py",
            "substrate/execution/trace.py",
            "substrate/execution/feedback.py",
        ]
        hits = []
        for target in core_dirs:
            result = subprocess.run(
                ["grep", "-rn", "@dataclass", target, "--include=*.py"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                hits.append(result.stdout.strip())
        assert not hits, f"Found dataclasses in substrate core: {chr(10).join(hits)}"

    def test_ontology_laws_are_callable(self):
        """Invariant: laws have check() method."""
        from substrate.ontology.laws import LawRegistry

        registry = LawRegistry()
        for law in registry.all():
            assert callable(getattr(law, "check", None)), f"Law {law.name} has no check()"

    def test_substrate_status_healthy(self, substrate):
        status = substrate.status()
        assert status.healthy is True
        assert "spine" in status.subsystems
        assert "governance" in status.subsystems

    @pytest.mark.asyncio
    async def test_eos_projection_isolation(self, substrate):
        """EOS projection only uses public API."""
        import subprocess

        result = subprocess.run(
            ["grep", "-rn", r"from substrate\.", "projections/", "--include=*.py"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.strip().split("\n"):
            if line:
                assert "from substrate import" in line or "from substrate.types" in line, (
                    f"Projection imports substrate internals: {line}"
                )

    def test_reality_model_canonical_governance(self):
        """Canonical patterns require governance to update."""
        from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern

        model = CanonicalRealityModel()
        model.store(
            CanonicalPattern(
                name="test",
                domain="test",
                description="test",
                evidence_count=1,
                confidence=0.9,
            )
        )
        with pytest.raises(ValueError, match="governance"):
            model.update("test", description="changed", governance_approved=False)

    @pytest.mark.asyncio
    async def test_eos_agents_register(self, substrate):
        """EOS agents register through substrate public API."""
        from projections.eos.agents.ceo import register_ceo_agent
        from projections.eos.agents.sales import register_sales_agent
        from projections.eos.agents.marketing import register_marketing_agent

        r1 = await register_ceo_agent(substrate)
        r2 = await register_sales_agent(substrate)
        r3 = await register_marketing_agent(substrate)

        assert r1.success and r2.success and r3.success
