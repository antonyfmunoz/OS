"""Tests for Governance Runtime — Campaign 15.0."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.governance_runtime import (
    AUTHORITY_RANK,
    ConflictSeverityLevel,
    ConflictStatus,
    GovernanceAuthority,
    GovernanceDriftType,
    GovernanceDriftWarning,
    GovernanceHealth,
    GovernancePolicy,
    GovernanceRuntime,
    GovernanceRuntimeSnapshot,
    SubsystemConflict,
)


# ── Enum Tests ───────────────────────────────────────────────────────


class TestEnums:
    def test_governance_authority_values(self) -> None:
        assert GovernanceAuthority.REALITY.value == "reality"
        assert GovernanceAuthority.STRATEGY.value == "strategy"
        assert GovernanceAuthority.GOALS.value == "goals"
        assert GovernanceAuthority.DECISIONS.value == "decisions"
        assert GovernanceAuthority.EXECUTIVE.value == "executive"
        assert GovernanceAuthority.WORK.value == "work"
        assert len(GovernanceAuthority) == 6

    def test_conflict_status_values(self) -> None:
        assert ConflictStatus.DETECTED.value == "detected"
        assert ConflictStatus.ARBITRATED.value == "arbitrated"
        assert ConflictStatus.ACKNOWLEDGED.value == "acknowledged"
        assert ConflictStatus.SUPERSEDED.value == "superseded"
        assert len(ConflictStatus) == 4

    def test_conflict_severity_level_values(self) -> None:
        assert ConflictSeverityLevel.CRITICAL.value == "critical"
        assert ConflictSeverityLevel.HIGH.value == "high"
        assert ConflictSeverityLevel.MEDIUM.value == "medium"
        assert ConflictSeverityLevel.LOW.value == "low"
        assert len(ConflictSeverityLevel) == 4

    def test_governance_health_values(self) -> None:
        assert GovernanceHealth.COHERENT.value == "coherent"
        assert GovernanceHealth.ALIGNED.value == "aligned"
        assert GovernanceHealth.STRAINED.value == "strained"
        assert GovernanceHealth.FRAGMENTED.value == "fragmented"
        assert GovernanceHealth.CRITICAL.value == "critical"
        assert len(GovernanceHealth) == 5

    def test_governance_drift_type_values(self) -> None:
        assert GovernanceDriftType.AUTHORITY_VIOLATION.value == "authority_violation"
        assert GovernanceDriftType.UNRESOLVED_CONFLICT.value == "unresolved_conflict"
        assert GovernanceDriftType.POLICY_STALENESS.value == "policy_staleness"
        assert GovernanceDriftType.SUBSYSTEM_DISAGREEMENT.value == "subsystem_disagreement"
        assert len(GovernanceDriftType) == 4


# ── Authority Hierarchy Tests ────────────────────────────────────────


class TestAuthorityHierarchy:
    def test_authority_rank_ordering(self) -> None:
        assert AUTHORITY_RANK["reality"] == 0
        assert AUTHORITY_RANK["strategy"] == 1
        assert AUTHORITY_RANK["goals"] == 2
        assert AUTHORITY_RANK["decisions"] == 3
        assert AUTHORITY_RANK["executive"] == 4
        assert AUTHORITY_RANK["work"] == 5

    def test_reality_outranks_all(self) -> None:
        for auth in ["strategy", "goals", "decisions", "executive", "work"]:
            assert AUTHORITY_RANK["reality"] < AUTHORITY_RANK[auth]

    def test_work_outranked_by_all(self) -> None:
        for auth in ["reality", "strategy", "goals", "decisions", "executive"]:
            assert AUTHORITY_RANK["work"] > AUTHORITY_RANK[auth]


# ── Dataclass Tests ──────────────────────────────────────────────────


class TestDataclasses:
    def test_subsystem_conflict_defaults(self) -> None:
        c = SubsystemConflict()
        assert c.conflict_id == ""
        assert c.source_authority == "work"
        assert c.target_authority == "work"
        assert c.winning_authority == ""
        assert c.losing_authority == ""
        assert c.status == "detected"

    def test_subsystem_conflict_to_dict(self) -> None:
        c = SubsystemConflict(conflict_id="test-1", winning_authority="strategy", losing_authority="work")
        d = c.to_dict()
        assert d["conflict_id"] == "test-1"
        assert d["winning_authority"] == "strategy"
        assert d["losing_authority"] == "work"
        assert "rationale" in d

    def test_governance_policy_defaults(self) -> None:
        p = GovernancePolicy()
        assert p.policy_id == ""
        assert p.active is True

    def test_governance_policy_to_dict(self) -> None:
        p = GovernancePolicy(policy_id="p-1", name="Test", authority="reality")
        d = p.to_dict()
        assert d["policy_id"] == "p-1"
        assert d["name"] == "Test"

    def test_governance_drift_warning_defaults(self) -> None:
        w = GovernanceDriftWarning()
        assert w.drift_type == "authority_violation"
        assert w.severity == "low"
        assert w.affected_ids == []

    def test_governance_drift_warning_to_dict(self) -> None:
        w = GovernanceDriftWarning(severity="high", description="test")
        d = w.to_dict()
        assert d["severity"] == "high"
        assert d["description"] == "test"

    def test_governance_runtime_snapshot_defaults(self) -> None:
        s = GovernanceRuntimeSnapshot()
        assert s.governance_health == "aligned"
        assert s.conflict_count == 0
        assert s.resolution_rate == 1.0

    def test_governance_runtime_snapshot_to_dict(self) -> None:
        s = GovernanceRuntimeSnapshot(governance_health="coherent", conflict_count=3)
        d = s.to_dict()
        assert d["governance_health"] == "coherent"
        assert d["conflict_count"] == 3
        assert "authority_hierarchy" in d


# ── Runtime Tests ────────────────────────────────────────────────────


class TestGovernanceRuntime:
    def test_no_deps_graceful_degradation(self) -> None:
        rt = GovernanceRuntime()
        assert rt.health() == GovernanceHealth.COHERENT
        assert isinstance(rt.drift_warnings(), list)
        assert isinstance(rt.detect_conflicts(), list)

    def test_resolve_conflict_higher_wins(self) -> None:
        rt = GovernanceRuntime()
        c = rt.resolve_conflict("reality", "work", "observe X", "execute Y")
        assert c.winning_authority == "reality"
        assert c.losing_authority == "work"
        assert c.resolution == "observe X"
        assert c.status == "arbitrated"

    def test_resolve_conflict_strategy_beats_executive(self) -> None:
        rt = GovernanceRuntime()
        c = rt.resolve_conflict("executive", "strategy", "allocate to X", "avoid X")
        assert c.winning_authority == "strategy"
        assert c.losing_authority == "executive"
        assert c.resolution == "avoid X"
        assert c.status == "arbitrated"
        assert "rank" in c.rationale.lower()

    def test_resolve_conflict_equal_authority_source_wins(self) -> None:
        rt = GovernanceRuntime()
        c = rt.resolve_conflict("work", "work", "rec A", "rec B")
        assert c.winning_authority == "work"
        assert c.resolution == "rec A"

    def test_resolve_conflict_no_mutation(self) -> None:
        """Acceptance test: governance resolves but does not mutate subsystems."""
        rt = GovernanceRuntime()
        c = rt.resolve_conflict("executive", "strategy", "allocate to X", "avoid X")
        assert c.winning_authority == "strategy"
        assert c.losing_authority == "executive"
        # No mutation methods called — resolution is recorded, not enacted
        assert c.status == "arbitrated"
        # The runtime itself has no mutate/apply/execute methods
        assert not hasattr(rt, "apply_resolution")
        assert not hasattr(rt, "execute_resolution")
        assert not hasattr(rt, "mutate")

    def test_conflict_id_uniqueness(self) -> None:
        rt = GovernanceRuntime()
        c1 = rt.resolve_conflict("reality", "work", "a", "b")
        c2 = rt.resolve_conflict("reality", "work", "a", "b")
        assert c1.conflict_id != c2.conflict_id

    def test_authority_for_known_domains(self) -> None:
        rt = GovernanceRuntime()
        assert rt.authority_for("reality") == "reality"
        assert rt.authority_for("strategy") == "strategy"
        assert rt.authority_for("goals") == "goals"
        assert rt.authority_for("decisions") == "decisions"
        assert rt.authority_for("executive") == "executive"
        assert rt.authority_for("work") == "work"
        assert rt.authority_for("goal_alignment") == "goals"
        assert rt.authority_for("resource_allocation") == "executive"

    def test_authority_for_unknown_defaults_to_work(self) -> None:
        rt = GovernanceRuntime()
        assert rt.authority_for("unknown_domain") == "work"

    def test_active_policies_returns_six(self) -> None:
        rt = GovernanceRuntime()
        policies = rt.active_policies()
        assert len(policies) == 6
        names = [p.name for p in policies]
        assert "Authority Hierarchy" in names
        assert "No Direct Mutation" in names

    def test_health_coherent_no_conflicts(self) -> None:
        rt = GovernanceRuntime()
        assert rt.health() == GovernanceHealth.COHERENT

    def test_health_critical_with_critical_conflict(self) -> None:
        rt = GovernanceRuntime()
        rt._conflicts.append(SubsystemConflict(
            conflict_id="crit-1",
            severity="critical",
            status="detected",
        ))
        assert rt.health() == GovernanceHealth.CRITICAL

    def test_snapshot_fields(self) -> None:
        rt = GovernanceRuntime()
        snap = rt.snapshot()
        assert isinstance(snap, GovernanceRuntimeSnapshot)
        d = snap.to_dict()
        assert "governance_health" in d
        assert "active_conflicts" in d
        assert "resolved_conflicts" in d
        assert "active_policies" in d
        assert "drift_warnings" in d
        assert "authority_hierarchy" in d
        assert "conflict_count" in d
        assert "resolution_rate" in d
        assert "generated_at" in d

    def test_summary_keys(self) -> None:
        rt = GovernanceRuntime()
        s = rt.summary()
        assert "governance_health" in s
        assert "active_conflict_count" in s
        assert "drift_warning_count" in s
        assert "policy_count" in s
        assert "authority_hierarchy" in s


# ── Canonical Type Registration ──────────────────────────────────────


class TestCanonicalTypes:
    def test_governance_runtime_importable(self) -> None:
        from substrate.organism.governance_runtime import GovernanceRuntime
        rt = GovernanceRuntime()
        assert rt is not None
