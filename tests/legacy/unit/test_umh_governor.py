"""Tests for umh.governance.governor — controlled self-modification."""

from __future__ import annotations

import ast
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

import pytest

from umh.governance.governor import Governor, ImprovementProposal


# ── Import boundary ─────────────────────────────────────────────


class TestImportBoundary:
    def test_no_forbidden_imports(self):
        with open("umh/governance/governor.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"eos", "core", "services", "scripts"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"from {node.module}"


# ── ImprovementProposal ─────────────────────────────────────────


class TestImprovementProposal:
    def test_to_dict(self):
        p = ImprovementProposal(
            id="imp_001",
            timestamp=1000.0,
            target_component="router",
            proposed_change={"weight": 0.5},
            reason="testing",
            expected_impact="better routing",
            risk_level="low",
            requires_approval=False,
            rollback_plan="revert",
        )
        d = p.to_dict()
        assert d["id"] == "imp_001"
        assert d["risk_level"] == "low"
        assert d["proposed_change"]["weight"] == 0.5


# ── Governor core ────────────────────────────────────────────────


class TestGovernor:
    def test_low_risk_auto_applied(self):
        gov = Governor()
        p = gov.propose(
            target_component="router",
            proposed_change={"weight": 0.5},
            reason="testing",
            risk_level="low",
        )
        assert p.status == "applied"
        assert p.applied_at is not None
        assert not p.requires_approval

    def test_medium_risk_pending(self):
        gov = Governor()
        p = gov.propose(
            target_component="objective_engine",
            proposed_change={"threshold": 0.8},
            reason="testing",
            risk_level="medium",
        )
        assert p.status == "pending"
        assert p.requires_approval is True

    def test_high_risk_pending(self):
        gov = Governor()
        p = gov.propose(
            target_component="code",
            proposed_change={"logic": "new"},
            reason="testing",
            risk_level="high",
        )
        assert p.status == "pending"
        assert p.requires_approval is True

    def test_approve(self):
        gov = Governor()
        p = gov.propose(
            target_component="engine",
            proposed_change={},
            reason="test",
            risk_level="medium",
        )
        result = gov.approve(p.id)
        assert result is not None
        assert result.status == "applied"

    def test_approve_nonexistent_returns_none(self):
        gov = Governor()
        assert gov.approve("nonexistent") is None

    def test_approve_already_applied_returns_none(self):
        gov = Governor()
        p = gov.propose(
            target_component="x", proposed_change={},
            reason="t", risk_level="low",
        )
        assert gov.approve(p.id) is None

    def test_reject(self):
        gov = Governor()
        p = gov.propose(
            target_component="engine",
            proposed_change={},
            reason="test",
            risk_level="medium",
        )
        result = gov.reject(p.id, reason="not needed")
        assert result is not None
        assert result.status == "rejected"
        assert result.evidence["rejection_reason"] == "not needed"

    def test_rollback(self):
        gov = Governor()
        p = gov.propose(
            target_component="engine",
            proposed_change={},
            reason="test",
            risk_level="medium",
        )
        gov.approve(p.id)
        result = gov.rollback(p.id)
        assert result is not None
        assert result.status == "rolled_back"

    def test_rollback_pending_returns_none(self):
        gov = Governor()
        p = gov.propose(
            target_component="x", proposed_change={},
            reason="t", risk_level="medium",
        )
        assert gov.rollback(p.id) is None

    def test_get_pending(self):
        gov = Governor()
        gov.propose(target_component="a", proposed_change={}, reason="t", risk_level="low")
        gov.propose(target_component="b", proposed_change={}, reason="t", risk_level="medium")
        gov.propose(target_component="c", proposed_change={}, reason="t", risk_level="high")
        pending = gov.get_pending()
        assert len(pending) == 2

    def test_get_applied(self):
        gov = Governor()
        gov.propose(target_component="a", proposed_change={}, reason="t", risk_level="low")
        gov.propose(target_component="b", proposed_change={}, reason="t", risk_level="medium")
        applied = gov.get_applied()
        assert len(applied) == 1

    def test_get_all(self):
        gov = Governor()
        gov.propose(target_component="a", proposed_change={}, reason="t", risk_level="low")
        gov.propose(target_component="b", proposed_change={}, reason="t", risk_level="medium")
        assert len(gov.get_all()) == 2

    def test_default_rollback_plan(self):
        gov = Governor()
        p = gov.propose(
            target_component="router",
            proposed_change={},
            reason="test",
            risk_level="low",
        )
        assert "router" in p.rollback_plan

    def test_default_expected_impact(self):
        gov = Governor()
        p = gov.propose(
            target_component="composer",
            proposed_change={},
            reason="test",
            risk_level="low",
        )
        assert "composer" in p.expected_impact


# ── Filesystem integration ───────────────────────────────────────


class TestGovernorFilesystem:
    def test_writes_proposal_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proposals_dir = Path(tmpdir) / "proposals"
            log_file = Path(tmpdir) / "audit.jsonl"
            gov = Governor(proposals_dir=proposals_dir, log_file=log_file)

            p = gov.propose(
                target_component="engine",
                proposed_change={"x": 1},
                reason="test",
                risk_level="medium",
            )

            proposal_file = proposals_dir / f"{p.id}.json"
            assert proposal_file.exists()
            data = json.loads(proposal_file.read_text())
            assert data["target_component"] == "engine"

    def test_writes_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            gov = Governor(log_file=log_file)

            gov.propose(
                target_component="router",
                proposed_change={},
                reason="test",
                risk_level="low",
            )

            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["event"] == "auto_applied"

    def test_no_filesystem_when_no_paths(self):
        gov = Governor()
        p = gov.propose(
            target_component="x",
            proposed_change={},
            reason="t",
            risk_level="medium",
        )
        assert p.status == "pending"


# ── propose_from_objective_results ───────────────────────────────


class TestObjectiveProposals:
    def test_skips_achieved(self):
        gov = Governor()
        results = [{"name": "metric", "achieved": True, "score": 0.9}]
        proposals = gov.propose_from_objective_results(results, 0.9)
        assert proposals == []

    def test_hard_constraint_failure(self):
        gov = Governor()
        results = [{
            "name": "reply_rate",
            "achieved": False,
            "score": 0.2,
            "gap": 0.3,
            "weight": 0.5,
            "hard_constraint": True,
        }]
        proposals = gov.propose_from_objective_results(results, 0.5)
        assert len(proposals) == 1
        assert proposals[0].risk_level == "medium"
        assert "reply_rate" in proposals[0].reason

    def test_high_weight_underperforming(self):
        gov = Governor()
        results = [{
            "name": "conversion",
            "achieved": False,
            "score": 0.3,
            "gap": 0.2,
            "weight": 0.4,
            "hard_constraint": False,
        }]
        proposals = gov.propose_from_objective_results(results, 0.5)
        assert len(proposals) == 1
        assert proposals[0].risk_level == "low"


# ── propose_from_strategy ────────────────────────────────────────


class TestStrategyProposals:
    def test_rejects_low_success(self):
        gov = Governor()
        result = gov.propose_from_strategy({"success_rate": 0.3, "confidence": 0.8})
        assert result is None

    def test_rejects_low_confidence(self):
        gov = Governor()
        result = gov.propose_from_strategy({"success_rate": 0.8, "confidence": 0.2})
        assert result is None

    def test_high_confidence_is_low_risk(self):
        gov = Governor()
        result = gov.propose_from_strategy({
            "success_rate": 0.8,
            "confidence": 0.8,
            "strategy_id": "s1",
        })
        assert result is not None
        assert result.risk_level == "low"

    def test_moderate_confidence_is_medium_risk(self):
        gov = Governor()
        result = gov.propose_from_strategy({
            "success_rate": 0.7,
            "confidence": 0.5,
            "strategy_id": "s2",
        })
        assert result is not None
        assert result.risk_level == "medium"
