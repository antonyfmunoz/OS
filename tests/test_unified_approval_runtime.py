"""Tests for UnifiedApprovalRuntime — Campaign 4.2.

Covers: pending collection, urgency scoring, approve/reject routing,
snapshot, filtering, graceful degradation, serialization,
compounding PromotionStatus, reconciliation, decisions.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from substrate.workstation.unified_approval_runtime import (
    RISK_WEIGHTS,
    ApprovalAction,
    ApprovalSourceType,
    UnifiedApproval,
    UnifiedApprovalRuntime,
    UnifiedApprovalSnapshot,
    _compute_urgency,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _mock_governed() -> MagicMock:
    m = MagicMock()
    m.blocked.return_value = [
        {"work_id": "w-1", "title": "Deploy service", "risk_class": "high", "created_at": time.time() - 3600},
        {"work_id": "w-2", "title": "Run migration", "risk_class": "critical", "created_at": time.time() - 7200},
    ]
    m.approve_work.return_value = {"status": "approved"}
    m.reject_work.return_value = {"status": "rejected"}
    return m


def _mock_intercept() -> MagicMock:
    m = MagicMock()
    item = MagicMock()
    item.approval_id = "ai-1"
    item.title = "Git push --force"
    item.risk_class = "high"
    item.created_at = time.time() - 1800
    item.to_dict.return_value = {"approval_id": "ai-1", "title": "Git push --force"}
    m.pending.return_value = [item]
    m.approve.return_value = item
    m.reject.return_value = item
    return m


def _mock_gate() -> MagicMock:
    m = MagicMock()
    pkt = MagicMock()
    pkt.packet_id = "pkt-1"
    pkt.title = "Sandbox deploy"
    pkt.risk_class = "medium"
    pkt.created_at = time.time() - 900
    pkt.to_dict.return_value = {"packet_id": "pkt-1"}
    m.pending_packets.return_value = [pkt]
    m.approve.return_value = pkt
    m.reject.return_value = pkt
    return m


def _mock_strategic() -> MagicMock:
    m = MagicMock()
    rec = MagicMock()
    rec.recommendation_id = "rec-1"
    rec.title = "Optimize DB queries"
    rec.risk_class = "low"
    rec.created_at = time.time() - 600
    rec.to_dict.return_value = {"recommendation_id": "rec-1"}
    m.get_top_recommendations.return_value = [rec]
    m.approve_recommendation.return_value = {"success": True}
    m.reject_recommendation.return_value = {"success": True}
    return m


def _mock_compounding() -> MagicMock:
    m = MagicMock()
    cand = MagicMock()
    cand.candidate_id = "promo-1"
    cand.title = "Pattern: retry with backoff"
    cand.risk_class = "low"
    cand.created_at = time.time() - 300
    cand.to_dict.return_value = {"candidate_id": "promo-1"}
    m.list_candidates.return_value = [cand]
    m.approve.return_value = True
    m.reject.return_value = True
    return m


def _mock_templates() -> MagicMock:
    m = MagicMock()
    t = MagicMock()
    t.template_id = "tmpl-1"
    t.title = "Service deploy template"
    t.risk_class = "low"
    t.created_at = time.time() - 120
    t.to_dict.return_value = {"template_id": "tmpl-1"}
    m.pending_approvals.return_value = [t]
    m.approve.return_value = True
    m.reject.return_value = True
    return m


def _mock_memory() -> MagicMock:
    m = MagicMock()
    mc = MagicMock()
    mc.candidate_id = "mem-1"
    mc.title = "Memory candidate"
    mc.risk_class = "low"
    mc.created_at = time.time() - 60
    mc.to_dict.return_value = {"candidate_id": "mem-1"}
    m.pending_approvals.return_value = [mc]
    m.promote.return_value = mc
    m.reject.return_value = True
    return m


def _mock_overnight() -> MagicMock:
    m = MagicMock()
    item = MagicMock()
    item.item_id = "on-1"
    item.title = "Overnight cleanup"
    item.risk_class = "low"
    item.created_at = time.time() - 45
    item.to_dict.return_value = {"item_id": "on-1"}
    m.get_pending_approval.return_value = [item]
    m.approve.return_value = item
    return m


def _mock_automation() -> MagicMock:
    m = MagicMock()
    m.pending_proposals.return_value = [
        {"proposal_id": "auto-1", "title": "Auto-scale workers", "risk_class": "medium", "created_at": time.time() - 30},
    ]
    m.approve.return_value = True
    return m


def _mock_reconciliation() -> MagicMock:
    m = MagicMock()
    m._sessions = {}
    return m


def _build_runtime(**kwargs: Any) -> UnifiedApprovalRuntime:
    return UnifiedApprovalRuntime(**kwargs)


def _full_runtime() -> UnifiedApprovalRuntime:
    return UnifiedApprovalRuntime(
        governed_work=_mock_governed(),
        approval_intercept=_mock_intercept(),
        approval_gate=_mock_gate(),
        strategic_gap=_mock_strategic(),
        compounding=_mock_compounding(),
        template_registry=_mock_templates(),
        memory_promotion=_mock_memory(),
        overnight_queue=_mock_overnight(),
        automation_pipeline=_mock_automation(),
        reconciliation=_mock_reconciliation(),
    )


# ── Pending Collection ───────────────────────────────────────────────────


class TestPending:
    def test_all_sources_collected(self) -> None:
        rt = _full_runtime()
        items = rt.pending()
        assert len(items) >= 9

    def test_empty_with_no_deps(self) -> None:
        rt = _build_runtime()
        items = rt.pending()
        assert items == []

    def test_filter_by_source_type(self) -> None:
        rt = _full_runtime()
        governed = rt.pending(source_type="governed_work")
        assert all(i.source_type == ApprovalSourceType.GOVERNED_WORK for i in governed)
        assert len(governed) == 2

    def test_filter_by_intercept(self) -> None:
        rt = _full_runtime()
        intercepts = rt.pending(source_type="execution_intercept")
        assert len(intercepts) == 1

    def test_each_has_urgency_score(self) -> None:
        rt = _full_runtime()
        for item in rt.pending():
            assert isinstance(item.urgency_score, float)

    def test_each_has_approval_id(self) -> None:
        rt = _full_runtime()
        for item in rt.pending():
            assert item.approval_id.startswith("uappr-")


# ── Urgency Scoring ──────────────────────────────────────────────────────


class TestUrgencyScoring:
    def test_critical_higher_than_low(self) -> None:
        base_time = time.time() - 3600
        critical = _compute_urgency("critical", base_time)
        low = _compute_urgency("low", base_time)
        assert critical > low

    def test_older_higher_urgency(self) -> None:
        old_time = time.time() - 7200
        new_time = time.time() - 60
        old = _compute_urgency("medium", old_time)
        new = _compute_urgency("medium", new_time)
        assert old > new

    def test_unknown_risk_uses_default(self) -> None:
        base_time = time.time() - 3600
        unknown = _compute_urgency("unknown", base_time)
        low = _compute_urgency("low", base_time)
        assert unknown == low

    def test_zero_age_zero_urgency(self) -> None:
        score = _compute_urgency("critical", time.time())
        assert score < 0.01

    def test_risk_weights_defined(self) -> None:
        assert "critical" in RISK_WEIGHTS
        assert "high" in RISK_WEIGHTS
        assert "medium" in RISK_WEIGHTS
        assert "low" in RISK_WEIGHTS


# ── By Urgency ───────────────────────────────────────────────────────────


class TestByUrgency:
    def test_sorted_descending(self) -> None:
        rt = _full_runtime()
        items = rt.by_urgency(limit=20)
        for i in range(len(items) - 1):
            assert items[i].urgency_score >= items[i + 1].urgency_score

    def test_limit_respected(self) -> None:
        rt = _full_runtime()
        items = rt.by_urgency(limit=3)
        assert len(items) <= 3

    def test_empty_with_no_deps(self) -> None:
        rt = _build_runtime()
        assert rt.by_urgency() == []


# ── Approve ──────────────────────────────────────────────────────────────


class TestApprove:
    def test_approve_governed_work(self) -> None:
        rt = _full_runtime()
        action = rt.approve("w-1", "governed_work")
        assert action.action == "approved"
        assert action.routed_to == "governed_work"

    def test_approve_intercept(self) -> None:
        rt = _full_runtime()
        action = rt.approve("ai-1", "execution_intercept")
        assert action.action == "approved"

    def test_approve_unknown_source(self) -> None:
        rt = _full_runtime()
        action = rt.approve("x", "nonexistent")
        assert action.action == "error"

    def test_approve_records_decision(self) -> None:
        rt = _full_runtime()
        rt.approve("w-1", "governed_work")
        assert len(rt.recent_decisions()) == 1

    def test_approve_gate(self) -> None:
        rt = _full_runtime()
        action = rt.approve("pkt-1", "sandbox_gate")
        assert action.action == "approved"

    def test_approve_strategic(self) -> None:
        rt = _full_runtime()
        action = rt.approve("rec-1", "strategic_recommendation")
        assert action.action == "approved"

    def test_approve_template(self) -> None:
        rt = _full_runtime()
        action = rt.approve("tmpl-1", "template")
        assert action.action == "approved"


# ── Reject ───────────────────────────────────────────────────────────────


class TestReject:
    def test_reject_governed_work(self) -> None:
        rt = _full_runtime()
        action = rt.reject("w-2", "governed_work", reason="Too risky")
        assert action.action == "rejected"
        assert action.reason == "Too risky"

    def test_reject_intercept(self) -> None:
        rt = _full_runtime()
        action = rt.reject("ai-1", "execution_intercept", reason="Denied")
        assert action.action == "rejected"

    def test_reject_unknown_source(self) -> None:
        rt = _full_runtime()
        action = rt.reject("x", "fake_source")
        assert action.action == "error"

    def test_reject_records_decision(self) -> None:
        rt = _full_runtime()
        rt.reject("w-1", "governed_work", reason="No")
        decisions = rt.recent_decisions()
        assert len(decisions) == 1
        assert decisions[0].action == "rejected"


# ── Snapshot ─────────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_total_pending(self) -> None:
        rt = _full_runtime()
        snap = rt.snapshot()
        assert snap.total_pending >= 9

    def test_snapshot_by_source(self) -> None:
        rt = _full_runtime()
        snap = rt.snapshot()
        assert "governed_work" in snap.by_source

    def test_snapshot_by_risk(self) -> None:
        rt = _full_runtime()
        snap = rt.snapshot()
        assert len(snap.by_risk) > 0

    def test_snapshot_oldest(self) -> None:
        rt = _full_runtime()
        snap = rt.snapshot()
        assert snap.oldest_waiting_seconds > 0

    def test_snapshot_empty(self) -> None:
        rt = _build_runtime()
        snap = rt.snapshot()
        assert snap.total_pending == 0
        assert snap.by_source == {}

    def test_snapshot_to_dict(self) -> None:
        rt = _full_runtime()
        d = rt.snapshot().to_dict()
        assert "total_pending" in d
        assert "by_source" in d
        assert "generated_at" in d


# ── Decisions ────────────────────────────────────────────────────────────


class TestDecisions:
    def test_recent_decisions_empty(self) -> None:
        rt = _build_runtime()
        assert rt.recent_decisions() == []

    def test_recent_decisions_ordered(self) -> None:
        rt = _full_runtime()
        rt.approve("w-1", "governed_work")
        rt.reject("w-2", "governed_work", reason="No")
        decisions = rt.recent_decisions()
        assert len(decisions) == 2
        assert decisions[0].action == "rejected"
        assert decisions[1].action == "approved"

    def test_recent_decisions_limit(self) -> None:
        rt = _full_runtime()
        for i in range(5):
            rt.approve(f"w-{i}", "governed_work")
        assert len(rt.recent_decisions(limit=3)) == 3


# ── Graceful Degradation ────────────────────────────────────────────────


class TestGracefulDegradation:
    def test_single_source_only(self) -> None:
        rt = _build_runtime(governed_work=_mock_governed())
        items = rt.pending()
        assert len(items) == 2

    def test_broken_source_skipped(self) -> None:
        broken = MagicMock()
        broken.blocked.side_effect = RuntimeError("boom")
        rt = _build_runtime(governed_work=broken, approval_gate=_mock_gate())
        items = rt.pending()
        assert len(items) == 1

    def test_none_source_skipped(self) -> None:
        rt = _build_runtime(governed_work=None, approval_gate=_mock_gate())
        items = rt.pending()
        assert len(items) == 1

    def test_approve_missing_source(self) -> None:
        rt = _build_runtime()
        action = rt.approve("x", "governed_work")
        assert action.action == "error"

    def test_reject_missing_source(self) -> None:
        rt = _build_runtime()
        action = rt.reject("x", "governed_work")
        assert action.action == "error"


# ── Compounding PromotionStatus ──────────────────────────────────────────


class TestCompounding:
    def test_compounding_uses_enum(self) -> None:
        mock_comp = _mock_compounding()
        rt = _build_runtime(compounding=mock_comp)
        items = rt.pending()
        assert len(items) == 1
        assert items[0].source_type == ApprovalSourceType.KNOWLEDGE_PROMOTION

    def test_compounding_approve_routes(self) -> None:
        mock_comp = _mock_compounding()
        rt = _build_runtime(compounding=mock_comp)
        action = rt.approve("promo-1", "knowledge_promotion")
        assert action.action == "approved"

    def test_compounding_import_failure_graceful(self) -> None:
        mock_comp = MagicMock()
        mock_comp.list_candidates.side_effect = ImportError("No module")
        rt = _build_runtime(compounding=mock_comp)
        items = rt.pending(source_type="knowledge_promotion")
        assert items == []


# ── Reconciliation ───────────────────────────────────────────────────────


class TestReconciliation:
    def test_reconciliation_empty(self) -> None:
        rt = _build_runtime(reconciliation=_mock_reconciliation())
        items = rt.pending(source_type="reconciliation")
        assert items == []

    def test_reconciliation_with_proposals(self) -> None:
        mock_recon = MagicMock()
        sess = MagicMock()
        sess.proposals = [
            {"proposal_id": "rp-1", "title": "Merge divergent state", "status": "pending"},
        ]
        mock_recon._sessions = {"s-1": sess}
        rt = _build_runtime(reconciliation=mock_recon)
        items = rt.pending(source_type="reconciliation")
        assert len(items) == 1

    def test_reconciliation_filters_decided(self) -> None:
        mock_recon = MagicMock()
        sess = MagicMock()
        sess.proposals = [
            {"proposal_id": "rp-1", "title": "A", "status": "pending"},
            {"proposal_id": "rp-2", "title": "B", "status": "approved"},
        ]
        mock_recon._sessions = {"s-1": sess}
        rt = _build_runtime(reconciliation=mock_recon)
        items = rt.pending(source_type="reconciliation")
        assert len(items) == 1


# ── Serialization ────────────────────────────────────────────────────────


class TestSerialization:
    def test_unified_approval_to_dict(self) -> None:
        a = UnifiedApproval(
            source_type=ApprovalSourceType.GOVERNED_WORK,
            title="Test",
            risk_class="high",
        )
        d = a.to_dict()
        assert d["source_type"] == "governed_work"
        assert d["title"] == "Test"
        assert "approval_id" in d

    def test_approval_action_to_dict(self) -> None:
        a = ApprovalAction(
            approval_id="ua-1",
            source_type=ApprovalSourceType.TEMPLATE,
            action="approved",
        )
        d = a.to_dict()
        assert d["source_type"] == "template"
        assert d["action"] == "approved"

    def test_snapshot_to_dict(self) -> None:
        s = UnifiedApprovalSnapshot(total_pending=5, by_source={"governed_work": 3})
        d = s.to_dict()
        assert d["total_pending"] == 5
        assert d["by_source"]["governed_work"] == 3

    def test_unified_approval_auto_id(self) -> None:
        a = UnifiedApproval()
        assert a.approval_id.startswith("uappr-")

    def test_approval_action_auto_timestamp(self) -> None:
        a = ApprovalAction()
        assert a.timestamp > 0


# ── Source Types ─────────────────────────────────────────────────────────


class TestSourceTypes:
    def test_all_12_source_types(self) -> None:
        # Wave 1 added objective_plan (plan-acceptance decisions).
        # Wave 2 added execution_authorization (the bounded execution-authorization
        # decision) — the source the HUD execution card is composed from.
        assert len(ApprovalSourceType) == 12

    def test_source_type_values(self) -> None:
        """Pins the EXACT membership, deliberately — adding a decision source is
        a governance change and must be a conscious edit here, not a silent one.

        This test was stale: Wave 2 introduced `execution_authorization` and left the
        expected set at Wave 1's eleven, so it failed on the candidate while
        passing on the base. Caught by comparing shard failure counts against
        the Wave 1 merge base (8 there, 10 here) rather than accepting a
        `wave2_failures=0` summary.
        """
        expected = {
            "governed_work", "execution_intercept", "sandbox_gate",
            "strategic_recommendation", "knowledge_promotion",
            "memory_promotion", "template", "overnight",
            "automation", "reconciliation", "objective_plan",
            "execution_authorization",
        }
        actual = {s.value for s in ApprovalSourceType}
        assert actual == expected
