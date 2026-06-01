"""Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel tests.

90+ tests covering all models, engines, routes, security, and proofs.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest


# ── Helpers ────────────────────────────────────────────────────────────


def _temp_path(name: str = "test.jsonl") -> str:
    td = tempfile.mkdtemp()
    return os.path.join(td, name)


# ═══════════════════════════════════════════════════════════════════════
# Source Registry (Tasks 2)
# ═══════════════════════════════════════════════════════════════════════


class TestSourceRegistry:
    def test_source_serialization(self):
        from substrate.organism.source_registry import ContextSource, SourceType

        src = ContextSource(
            source_type=SourceType.AUDIT_DOC.value,
            title="Test Audit",
            location_ref="/tmp/test",
        )
        d = src.to_dict()
        assert d["source_type"] == "audit_doc"
        assert d["title"] == "Test Audit"
        restored = ContextSource.from_dict(d)
        assert restored.title == "Test Audit"

    def test_source_auto_id(self):
        from substrate.organism.source_registry import ContextSource

        src = ContextSource(title="Auto ID")
        assert src.source_id.startswith("src-")

    def test_registry_register_and_list(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        reg = SourceRegistry(path=_temp_path())
        src = reg.register(ContextSource(title="Test", location_ref="/tmp/x"))
        assert reg.count() == 1
        assert reg.get(src.source_id) is not None
        assert len(reg.list_sources()) == 1

    def test_registry_dedup_by_location(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        reg = SourceRegistry(path=_temp_path())
        reg.register(ContextSource(source_type="audit_doc", title="A", location_ref="/tmp/a"))
        reg.register(ContextSource(source_type="audit_doc", title="B", location_ref="/tmp/a"))
        assert reg.count() == 1

    def test_sync_policy_values(self):
        from substrate.organism.source_registry import SyncPolicy

        assert SyncPolicy.READ_ONLY.value == "read_only"
        assert SyncPolicy.CANONICAL_SOURCE.value == "canonical_source"
        assert SyncPolicy.IGNORE.value == "ignore"

    def test_canonicality_values(self):
        from substrate.organism.source_registry import Canonicality

        assert Canonicality.CANONICAL.value == "canonical"
        assert Canonicality.SUPERSEDED.value == "superseded"

    def test_registry_mark_ingested(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        reg = SourceRegistry(path=_temp_path())
        src = reg.register(ContextSource(title="Test"))
        assert reg.mark_ingested(src.source_id)
        updated = reg.get(src.source_id)
        assert updated.status == "ingested"
        assert updated.last_ingested_at > 0

    def test_registry_filter_by_type(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        reg = SourceRegistry(path=_temp_path())
        reg.register(ContextSource(source_type="audit_doc", title="A"))
        reg.register(ContextSource(source_type="local_doc", title="B"))
        assert len(reg.list_sources(source_type="audit_doc")) == 1

    def test_registry_summary(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        reg = SourceRegistry(path=_temp_path())
        reg.register(ContextSource(source_type="audit_doc", title="A"))
        s = reg.summary()
        assert s["total"] == 1
        assert "audit_doc" in s["by_type"]

    def test_registry_persistence(self):
        from substrate.organism.source_registry import SourceRegistry, ContextSource

        path = _temp_path()
        reg1 = SourceRegistry(path=path)
        reg1.register(ContextSource(title="Persist Test"))
        reg2 = SourceRegistry(path=path)
        assert reg2.count() == 1


# ═══════════════════════════════════════════════════════════════════════
# Ingestion Job (Task 3)
# ═══════════════════════════════════════════════════════════════════════


class TestIngestionJob:
    def test_job_serialization(self):
        from substrate.organism.ingestion_job import IngestionJob, JobType

        job = IngestionJob(job_type=JobType.SCAN.value, scope="test")
        d = job.to_dict()
        assert d["job_type"] == "scan"
        restored = IngestionJob.from_dict(d)
        assert restored.scope == "test"

    def test_item_serialization(self):
        from substrate.organism.ingestion_job import IngestedItem

        item = IngestedItem(title="Test Item", summary="A test")
        d = item.to_dict()
        assert d["title"] == "Test Item"
        restored = IngestedItem.from_dict(d)
        assert restored.summary == "A test"

    def test_item_raw_content_default_false(self):
        from substrate.organism.ingestion_job import IngestedItem

        item = IngestedItem()
        assert item.raw_content_stored is False

    def test_job_store_create_and_list(self):
        from substrate.organism.ingestion_job import IngestionJobStore, IngestionJob

        store = IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl"))
        job = store.create_job(IngestionJob(scope="test"))
        assert store.count_jobs() == 1
        assert store.get_job(job.job_id) is not None

    def test_job_store_status_update(self):
        from substrate.organism.ingestion_job import IngestionJobStore, IngestionJob, JobStatus

        store = IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl"))
        job = store.create_job(IngestionJob())
        store.update_job_status(job.job_id, JobStatus.RUNNING.value)
        updated = store.get_job(job.job_id)
        assert updated.status == "running"
        assert updated.started_at > 0

    def test_job_store_add_items(self):
        from substrate.organism.ingestion_job import IngestionJobStore, IngestionJob, IngestedItem

        store = IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl"))
        job = store.create_job(IngestionJob())
        store.add_item(IngestedItem(job_id=job.job_id, title="A"))
        store.add_item(IngestedItem(job_id=job.job_id, title="B"))
        assert store.count_items() == 2
        assert len(store.get_items_for_job(job.job_id)) == 2


# ═══════════════════════════════════════════════════════════════════════
# Context Ingestion Engine (Task 4)
# ═══════════════════════════════════════════════════════════════════════


class TestContextIngestionEngine:
    def test_seed_local_sources(self):
        from substrate.organism.context_ingestion_engine import ContextIngestionEngine
        from substrate.organism.source_registry import SourceRegistry
        from substrate.organism.ingestion_job import IngestionJobStore

        engine = ContextIngestionEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
        )
        seeds = engine.seed_local_sources()
        assert len(seeds) >= 1

    def test_local_audit_ingestion(self, tmp_path):
        from substrate.organism.context_ingestion_engine import ContextIngestionEngine
        from substrate.organism.source_registry import SourceRegistry, ContextSource
        from substrate.organism.ingestion_job import IngestionJobStore

        audit_dir = tmp_path / "audits"
        audit_dir.mkdir()
        (audit_dir / "test_audit.md").write_text("UMH is the universal substrate. EOS handles companies.")

        engine = ContextIngestionEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
        )
        src = engine.register_source(ContextSource(
            source_type="audit_doc", title="Test", location_ref=str(audit_dir)
        ))
        job = engine.run_local_audit_ingestion(src.source_id)
        assert job is not None
        assert job.ingested_items == 1

    def test_size_limit_enforcement(self, tmp_path):
        from substrate.organism.context_ingestion_engine import ContextIngestionEngine, _is_within_size_limit

        big_file = tmp_path / "huge.md"
        big_file.write_text("x" * (1024 * 1024))
        assert not _is_within_size_limit(str(big_file))

    def test_extension_allowlist(self):
        from substrate.organism.context_ingestion_engine import _is_allowed_extension

        assert _is_allowed_extension("test.md")
        assert _is_allowed_extension("data.json")
        assert not _is_allowed_extension("binary.exe")
        assert not _is_allowed_extension("image.png")

    def test_secret_redaction(self):
        from substrate.organism.context_ingestion_engine import _redact_secrets

        text = "api_key=sk-abc123xyz password: hunter2"
        result = _redact_secrets(text)
        assert "sk-abc123" not in result
        assert "[REDACTED]" in result

    def test_duplicate_prevention(self):
        from substrate.organism.context_ingestion_engine import ContextIngestionEngine
        from substrate.organism.source_registry import SourceRegistry, ContextSource
        from substrate.organism.ingestion_job import IngestionJobStore, IngestionJob, JobStatus

        js = IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl"))
        engine = ContextIngestionEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=js,
        )
        src = engine.register_source(ContextSource(title="Dup Test"))
        job = IngestionJob(source_id=src.source_id, status=JobStatus.COMPLETED.value, completed_at=time.time())
        js.create_job(job)
        assert engine.prevent_duplicate_ingestion(src.source_id)

    def test_safe_path_check(self):
        from substrate.organism.context_ingestion_engine import _is_safe_path

        assert _is_safe_path("/opt/OS/docs/test.md")
        assert not _is_safe_path("/opt/OS/.env")
        assert not _is_safe_path("/opt/OS/credentials.json")


# ═══════════════════════════════════════════════════════════════════════
# Context Diagnostic (Task 5)
# ═══════════════════════════════════════════════════════════════════════


class TestContextDiagnostic:
    def test_claim_serialization(self):
        from substrate.organism.context_diagnostic import CanonicalClaim

        claim = CanonicalClaim(claim_text="UMH is universal", domain="infrastructure")
        d = claim.to_dict()
        assert d["claim_text"] == "UMH is universal"
        restored = CanonicalClaim.from_dict(d)
        assert restored.domain == "infrastructure"

    def test_contradiction_serialization(self):
        from substrate.organism.context_diagnostic import ContextContradiction, ContradictionType

        c = ContextContradiction(
            claim_a="A", claim_b="B",
            contradiction_type=ContradictionType.DIRECT_CONFLICT.value,
        )
        d = c.to_dict()
        assert d["contradiction_type"] == "direct_conflict"
        assert d["requires_operator_decision"] is True

    def test_report_serialization(self):
        from substrate.organism.context_diagnostic import ContextDiagnosticReport

        rpt = ContextDiagnosticReport(scope="test")
        d = rpt.to_dict()
        assert d["scope"] == "test"
        restored = ContextDiagnosticReport.from_dict(d)
        assert restored.scope == "test"

    def test_report_store(self):
        from substrate.organism.context_diagnostic import DiagnosticReportStore, ContextDiagnosticReport

        store = DiagnosticReportStore(path=_temp_path())
        rpt = store.save_report(ContextDiagnosticReport(scope="test"))
        assert store.count() == 1
        assert store.get_report(rpt.report_id) is not None

    def test_contradiction_type_values(self):
        from substrate.organism.context_diagnostic import ContradictionType

        assert ContradictionType.STALE_VS_CURRENT.value == "stale_vs_current"
        assert ContradictionType.ROADMAP_DRIFT.value == "roadmap_drift"


# ═══════════════════════════════════════════════════════════════════════
# Diagnostic Engine (Task 6)
# ═══════════════════════════════════════════════════════════════════════


class TestDiagnosticEngine:
    def test_build_report(self):
        from substrate.organism.diagnostic_engine import DiagnosticEngine
        from substrate.organism.source_registry import SourceRegistry
        from substrate.organism.ingestion_job import IngestionJobStore
        from substrate.organism.context_diagnostic import DiagnosticReportStore
        from substrate.organism.canonical_update import ProposalStore

        engine = DiagnosticEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
            report_store=DiagnosticReportStore(path=_temp_path()),
            proposal_store=ProposalStore(path=_temp_path()),
        )
        report = engine.build_diagnostic_report(scope="test")
        assert report.status == "completed"
        assert report.scope == "test"

    def test_missing_context_detection(self):
        from unittest.mock import patch
        from substrate.organism.diagnostic_engine import DiagnosticEngine
        from substrate.organism.source_registry import SourceRegistry
        from substrate.organism.ingestion_job import IngestionJobStore
        from substrate.organism.context_diagnostic import DiagnosticReportStore
        from substrate.organism.canonical_update import ProposalStore

        engine = DiagnosticEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
            report_store=DiagnosticReportStore(path=_temp_path()),
            proposal_store=ProposalStore(path=_temp_path()),
        )
        test_knowledge = {
            "known_entities": {"TestPlatform": {"type": "platform", "description": "test"}},
            "expected_products": ["TestPlatform"],
            "expected_companies": ["TestCorp"],
            "open_question_rules": [],
        }
        with patch("substrate.organism.diagnostic_engine._load_entity_knowledge", return_value=test_knowledge):
            report = engine.build_diagnostic_report()
        assert len(report.missing_context) > 0


# ═══════════════════════════════════════════════════════════════════════
# Canonical Update Proposal (Task 7)
# ═══════════════════════════════════════════════════════════════════════


class TestCanonicalUpdate:
    def test_proposal_serialization(self):
        from substrate.organism.canonical_update import CanonicalUpdateProposal, ProposalType

        prop = CanonicalUpdateProposal(
            proposal_type=ProposalType.PROMOTE_CLAIM.value,
            title="Test Proposal",
        )
        d = prop.to_dict()
        assert d["proposal_type"] == "promote_claim"
        assert d["approval_required"] is True

    def test_no_auto_apply(self):
        from substrate.organism.canonical_update import CanonicalUpdateProposal, ProposalStatus

        prop = CanonicalUpdateProposal()
        assert prop.approval_required is True
        assert prop.status == ProposalStatus.DRAFTED.value

    def test_proposal_store_approve(self):
        from substrate.organism.canonical_update import ProposalStore, CanonicalUpdateProposal

        store = ProposalStore(path=_temp_path())
        prop = store.save_proposal(CanonicalUpdateProposal(title="Test"))
        assert store.approve(prop.proposal_id)
        updated = store.get_proposal(prop.proposal_id)
        assert updated.status == "approved"
        assert updated.decided_at > 0

    def test_proposal_store_reject(self):
        from substrate.organism.canonical_update import ProposalStore, CanonicalUpdateProposal

        store = ProposalStore(path=_temp_path())
        prop = store.save_proposal(CanonicalUpdateProposal(title="Test"))
        assert store.reject(prop.proposal_id)
        assert store.get_proposal(prop.proposal_id).status == "rejected"

    def test_pending_count(self):
        from substrate.organism.canonical_update import ProposalStore, CanonicalUpdateProposal, ProposalStatus

        store = ProposalStore(path=_temp_path())
        store.save_proposal(CanonicalUpdateProposal(status=ProposalStatus.PENDING_OPERATOR_REVIEW.value))
        store.save_proposal(CanonicalUpdateProposal(status=ProposalStatus.DRAFTED.value))
        assert store.pending_count() == 1

    def test_affected_objects(self):
        from substrate.organism.canonical_update import CanonicalUpdateProposal

        prop = CanonicalUpdateProposal(
            affected_entities=["EOS", "UMH"],
            affected_work_packets=["wp-1"],
            affected_roadmap_phases=["13.3"],
        )
        d = prop.to_dict()
        assert len(d["affected_entities"]) == 2
        assert len(d["affected_work_packets"]) == 1


# ═══════════════════════════════════════════════════════════════════════
# Reconciliation Session (Task 8)
# ═══════════════════════════════════════════════════════════════════════


class TestReconciliationSession:
    def test_session_serialization(self):
        from substrate.organism.reconciliation_session import ReconciliationSession, ReconciliationMode

        sess = ReconciliationSession(topic="test", mode=ReconciliationMode.EXPLORATION.value)
        d = sess.to_dict()
        assert d["topic"] == "test"
        assert d["mode"] == "exploration"

    def test_decision_serialization(self):
        from substrate.organism.reconciliation_session import ReconciliationDecision

        dec = ReconciliationDecision(question="Q?", operator_answer="A")
        d = dec.to_dict()
        assert d["question"] == "Q?"
        assert d["operator_answer"] == "A"

    def test_session_store(self):
        from substrate.organism.reconciliation_session import ReconciliationSessionStore, ReconciliationSession

        store = ReconciliationSessionStore(
            sessions_path=_temp_path("s.jsonl"),
            decisions_path=_temp_path("d.jsonl"),
        )
        sess = store.create_session(ReconciliationSession(topic="test"))
        assert store.count() == 1
        assert store.get_session(sess.session_id) is not None

    def test_session_complete(self):
        from substrate.organism.reconciliation_session import ReconciliationSessionStore, ReconciliationSession

        store = ReconciliationSessionStore(
            sessions_path=_temp_path("s.jsonl"),
            decisions_path=_temp_path("d.jsonl"),
        )
        sess = store.create_session(ReconciliationSession(topic="test"))
        assert store.complete_session(sess.session_id, "Done")
        updated = store.get_session(sess.session_id)
        assert updated.status == "completed"

    def test_add_decision(self):
        from substrate.organism.reconciliation_session import (
            ReconciliationSessionStore, ReconciliationSession, ReconciliationDecision,
        )

        store = ReconciliationSessionStore(
            sessions_path=_temp_path("s.jsonl"),
            decisions_path=_temp_path("d.jsonl"),
        )
        sess = store.create_session(ReconciliationSession(topic="test"))
        dec = store.add_decision(ReconciliationDecision(session_id=sess.session_id, question="Q?"))
        decisions = store.get_decisions_for_session(sess.session_id)
        assert len(decisions) == 1


# ═══════════════════════════════════════════════════════════════════════
# Reconciliation Engine (Task 9)
# ═══════════════════════════════════════════════════════════════════════


class TestReconciliationEngine:
    def _make_engine(self):
        from substrate.organism.reconciliation_engine import ReconciliationEngine
        from substrate.organism.source_registry import SourceRegistry
        from substrate.organism.ingestion_job import IngestionJobStore
        from substrate.organism.context_diagnostic import DiagnosticReportStore
        from substrate.organism.canonical_update import ProposalStore
        from substrate.organism.reconciliation_session import ReconciliationSessionStore

        return ReconciliationEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
            report_store=DiagnosticReportStore(path=_temp_path()),
            proposal_store=ProposalStore(path=_temp_path()),
            session_store=ReconciliationSessionStore(
                sessions_path=_temp_path("s.jsonl"), decisions_path=_temp_path("d.jsonl")
            ),
        )

    def test_start_session(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test")
        assert sess.session_id.startswith("recon-")

    def test_exploration_mode(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test", mode="exploration")
        assert engine.is_exploration_mode(sess.session_id)

    def test_reconciliation_mode(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test", mode="reconciliation")
        assert not engine.is_exploration_mode(sess.session_id)

    def test_decision_mode(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test", mode="decision")
        engine.set_mode(sess.session_id, "decision")
        assert not engine.is_exploration_mode(sess.session_id)

    def test_no_silent_canon_mutation(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test", mode="reconciliation")
        engine.attach_sources(sess.session_id)
        engine.run_diagnostic(sess.session_id)
        proposals = engine.generate_canonical_update_proposals(sess.session_id)
        for p in proposals:
            assert p.get("status") != "applied"

    def test_propagation_preview(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test")
        preview = engine.preview_propagation(sess.session_id)
        assert preview["dry_run"] is True

    def test_generate_session_summary(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test")
        summary = engine.generate_session_summary(sess.session_id)
        assert "test" in summary

    def test_complete_session(self):
        engine = self._make_engine()
        sess = engine.start_session(topic="test")
        assert engine.complete_session(sess.session_id)


# ═══════════════════════════════════════════════════════════════════════
# DEX Integration (Task 10)
# ═══════════════════════════════════════════════════════════════════════


class TestDexReconciliation:
    def test_classify_exploration(self):
        from substrate.organism.dex_reconciliation import classify_reconciliation_intent

        assert classify_reconciliation_intent("I'm just thinking out loud") == "exploration"
        assert classify_reconciliation_intent("Maybe we could try this") == "exploration"

    def test_classify_reconciliation(self):
        from substrate.organism.dex_reconciliation import classify_reconciliation_intent

        assert classify_reconciliation_intent("Actually EOS also handles portfolios") == "reconciliation"
        assert classify_reconciliation_intent("This doc is outdated") == "reconciliation"

    def test_classify_decision(self):
        from substrate.organism.dex_reconciliation import classify_reconciliation_intent

        assert classify_reconciliation_intent("Canonize this change") == "decision"
        assert classify_reconciliation_intent("Approve this update") == "decision"

    def test_classify_query(self):
        from substrate.organism.dex_reconciliation import classify_reconciliation_intent

        assert classify_reconciliation_intent("What do you understand about my empire?") == "query"

    def test_classify_none(self):
        from substrate.organism.dex_reconciliation import classify_reconciliation_intent

        assert classify_reconciliation_intent("Hello there") == "none"

    def test_exploration_vs_canonization(self):
        from substrate.organism.dex_reconciliation import DexReconciliation

        dex = DexReconciliation()
        result = dex.process_operator_input("Just exploring: maybe EOS also manages portfolios")
        assert result["intent"] == "exploration"
        assert result.get("canon_safe", False) is True

    def test_reconciliation_creates_proposals(self):
        from substrate.organism.dex_reconciliation import DexReconciliation

        dex = DexReconciliation()
        result = dex.process_operator_input("Actually EOS handles multiple portfolios")
        assert result["intent"] == "reconciliation"
        assert "session_id" in result

    def test_decision_requires_approval(self):
        from substrate.organism.dex_reconciliation import DexReconciliation

        dex = DexReconciliation()
        result = dex.process_operator_input("Canonize that EOS includes portfolios")
        assert result["intent"] == "decision"
        assert result.get("approval_required", False) is True


# ═══════════════════════════════════════════════════════════════════════
# Environment Discovery (Addendum)
# ═══════════════════════════════════════════════════════════════════════


class TestEnvironmentDiscovery:
    def test_device_serialization(self):
        from substrate.organism.environment_discovery import DeviceEnvironment, DeviceType

        dev = DeviceEnvironment(device_name="VPS", device_type=DeviceType.VPS.value)
        d = dev.to_dict()
        assert d["device_name"] == "VPS"
        assert d["device_type"] == "vps"

    def test_app_serialization(self):
        from substrate.organism.environment_discovery import ApplicationInventoryItem, AppType

        app = ApplicationInventoryItem(app_name="VSCode", app_type=AppType.DEVELOPER_TOOL.value)
        d = app.to_dict()
        assert d["app_name"] == "VSCode"

    def test_scope_serialization(self):
        from substrate.organism.environment_discovery import FilesystemScope

        scope = FilesystemScope(path="/opt/OS", label="UMH Repo")
        d = scope.to_dict()
        assert d["path"] == "/opt/OS"
        assert d["allowed"] is False

    def test_store_register_device(self):
        from substrate.organism.environment_discovery import EnvironmentDiscoveryStore, DeviceEnvironment

        store = EnvironmentDiscoveryStore(
            devices_path=_temp_path("d.jsonl"),
            apps_path=_temp_path("a.jsonl"),
            scopes_path=_temp_path("s.jsonl"),
        )
        dev = store.register_device(DeviceEnvironment(device_name="Test"))
        assert len(store.list_devices()) == 1

    def test_store_register_app_dedup(self):
        from substrate.organism.environment_discovery import EnvironmentDiscoveryStore, ApplicationInventoryItem

        store = EnvironmentDiscoveryStore(
            devices_path=_temp_path("d.jsonl"),
            apps_path=_temp_path("a.jsonl"),
            scopes_path=_temp_path("s.jsonl"),
        )
        store.register_app(ApplicationInventoryItem(app_name="VSCode"))
        store.register_app(ApplicationInventoryItem(app_name="vscode"))
        assert len(store.list_apps()) == 1

    def test_scope_grant_deny(self):
        from substrate.organism.environment_discovery import EnvironmentDiscoveryStore, FilesystemScope

        store = EnvironmentDiscoveryStore(
            devices_path=_temp_path("d.jsonl"),
            apps_path=_temp_path("a.jsonl"),
            scopes_path=_temp_path("s.jsonl"),
        )
        scope = store.register_scope(FilesystemScope(path="/tmp/test"))
        assert not scope.allowed
        store.grant_scope(scope.scope_id)
        assert store.get_scope(scope.scope_id).allowed is True
        store.deny_scope(scope.scope_id)
        assert store.get_scope(scope.scope_id).allowed is False

    def test_default_blocked_patterns(self):
        from substrate.organism.environment_discovery import FilesystemScope

        scope = FilesystemScope()
        assert ".env" in scope.blocked_patterns
        assert "credentials" in scope.blocked_patterns

    def test_filesystem_metadata_only_default(self):
        from substrate.organism.environment_discovery import FilesystemScope, ScopeStatus

        scope = FilesystemScope()
        assert scope.permission_required is True
        assert scope.status == ScopeStatus.PENDING_PERMISSION.value


# ═══════════════════════════════════════════════════════════════════════
# Permission Dialogue (Addendum)
# ═══════════════════════════════════════════════════════════════════════


class TestPermissionDialogue:
    def test_request_creation(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(
            requested_action="scan_filesystem",
            reason="To discover project structure",
            what_umh_will_do="List file names only",
        )
        assert req.request_id.startswith("perm-")
        assert req.status == "pending"

    def test_deny_permission(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(requested_action="scan", reason="test")
        engine.decide(req.request_id, "deny")
        assert not engine.is_permitted(req.request_id)

    def test_approve_permission(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(requested_action="scan", reason="test")
        engine.decide(req.request_id, "read_only")
        assert engine.is_permitted(req.request_id)
        assert engine.get_effective_scope(req.request_id) == "read_only"

    def test_revoke_permission(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(requested_action="scan", reason="test")
        engine.decide(req.request_id, "read_only")
        assert engine.is_permitted(req.request_id)
        engine.revoke(req.request_id)
        assert not engine.is_permitted(req.request_id)

    def test_ask_later(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(requested_action="scan", reason="test")
        engine.decide(req.request_id, "ask_later")
        assert req.request_id in [r.request_id for r in engine.list_requests(status="deferred")]

    def test_remember_preference(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(
            requested_action="scan_filesystem",
            reason="test",
            source_type="local_doc",
        )
        engine.decide(req.request_id, "metadata_only", remember=True)
        req2 = engine.create_request(
            requested_action="scan_filesystem",
            reason="test again",
            source_type="local_doc",
        )
        assert req2.status == "approved"

    def test_socratic_dialogue_rendering(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        req = engine.create_request(
            requested_action="scan",
            reason="To discover files",
            what_umh_will_do="List file names",
            what_umh_will_not_do="No content reading",
        )
        dialogue = req.to_dialogue()
        assert "question" in dialogue
        assert "options" in dialogue
        assert "recommended" in dialogue

    def test_no_silent_expansion(self):
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        engine = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        assert engine.pending_count() == 0
        req = engine.create_request(requested_action="expand_scope", reason="test")
        assert engine.pending_count() == 1
        assert not engine.is_permitted(req.request_id)


# ═══════════════════════════════════════════════════════════════════════
# Cross-Source Reconciler (Addendum)
# ═══════════════════════════════════════════════════════════════════════


class TestCrossSourceReconciler:
    def test_detect_signal(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler, SignalType

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        sig = reconciler.detect_signal(
            signal_type=SignalType.APP_USAGE_DETECTED.value,
            source_ids=["src-1"],
            entities=["Figma"],
            inferred_relationship="Figma may be active design tool",
            evidence=["Found Figma exports"],
        )
        assert sig.signal_id.startswith("xsig-")
        assert sig.requires_operator_confirmation is True

    def test_subscription_signal_requires_permission(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        sig = reconciler.detect_subscription_signal(
            app_name="Figma",
            source_ids=["email-1"],
            evidence=["$12.99/mo charge"],
        )
        assert sig.sensitivity == "financial"
        assert sig.requires_permission is True

    def test_confirm_requires_permission(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler
        from substrate.organism.permission_dialogue import SocraticPermissionEngine

        perm = SocraticPermissionEngine(
            requests_path=_temp_path("r.jsonl"),
            preferences_path=_temp_path("p.jsonl"),
        )
        reconciler = CrossSourceReconciler(
            permission_engine=perm,
            signals_path=_temp_path(),
        )
        sig = reconciler.detect_subscription_signal("Figma", ["src-1"], ["evidence"])
        reconciler.request_permission_for_signal(sig.signal_id)
        assert not reconciler.confirm_signal(sig.signal_id)

    def test_canonize_requires_confirmation(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        sig = reconciler.detect_signal(
            signal_type="app_usage_detected",
            source_ids=["src-1"],
            entities=["VSCode"],
            inferred_relationship="VSCode is active",
            evidence=["found"],
            sensitivity="internal",
        )
        result = reconciler.canonize_signal(sig.signal_id)
        assert result is None

    def test_unused_subscription_detection(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        sig = reconciler.detect_unused_subscription("OldApp", ["src-1"], ["email receipt"])
        assert sig.signal_type == "paid_but_unused_tool"

    def test_cleanup_candidates(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        reconciler.detect_unused_subscription("OldApp", ["src-1"], ["receipt"])
        candidates = reconciler.generate_cleanup_candidates()
        assert len(candidates) == 1
        assert candidates[0]["type"] == "subscription_cleanup"


# ═══════════════════════════════════════════════════════════════════════
# Sync Policy (Task 12)
# ═══════════════════════════════════════════════════════════════════════


class TestSyncPolicy:
    def test_policy_serialization(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy, WritePolicy

        pol = ExternalSyncPolicy(source_type="google_drive", write_policy=WritePolicy.DISABLED.value)
        d = pol.to_dict()
        assert d["write_policy"] == "disabled"

    def test_read_only_evaluation(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy, WritePolicy

        pol = ExternalSyncPolicy(write_policy=WritePolicy.DISABLED.value)
        result = pol.evaluate_operation("write_doc")
        assert not result["allowed"]
        assert result["reason"] == "writes_disabled"

    def test_operator_approved_evaluation(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy, WritePolicy

        pol = ExternalSyncPolicy(write_policy=WritePolicy.OPERATOR_APPROVED.value, approval_required=True)
        result = pol.evaluate_operation("read_doc")
        assert not result["allowed"]
        assert result["reason"] == "approval_required"

    def test_blocked_operation(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy

        pol = ExternalSyncPolicy(blocked_operations=["delete"])
        result = pol.evaluate_operation("delete")
        assert not result["allowed"]
        assert result["reason"] == "operation_blocked"

    def test_no_external_write_in_phase_13_3(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy, WritePolicy

        pol = ExternalSyncPolicy(write_policy=WritePolicy.DISABLED.value)
        for op in ["write_doc", "write_sheet", "write_email"]:
            assert not pol.evaluate_operation(op)["allowed"]

    def test_conflict_policies(self):
        from substrate.organism.sync_policy import ConflictPolicy

        assert ConflictPolicy.ASK_OPERATOR.value == "ask_operator"
        assert ConflictPolicy.PREFER_UMH.value == "prefer_umh"
        assert ConflictPolicy.CREATE_CONTRADICTION.value == "create_contradiction"

    def test_policy_store(self):
        from substrate.organism.sync_policy import SyncPolicyStore, ExternalSyncPolicy

        store = SyncPolicyStore(path=_temp_path())
        pol = store.save_policy(ExternalSyncPolicy(source_type="google_drive"))
        assert store.count() == 1
        assert store.get_policy(pol.policy_id) is not None


# ═══════════════════════════════════════════════════════════════════════
# API / Security (Task 13)
# ═══════════════════════════════════════════════════════════════════════


class TestAPIRoutes:
    def test_route_file_imports(self):
        from transports.api import cockpit_context_assimilation_routes

        assert hasattr(cockpit_context_assimilation_routes, "configure")
        assert hasattr(cockpit_context_assimilation_routes, "context_assimilation_router")

    def test_bridge_actions_registered(self):
        from transports.api.organism_bridge import _ACTIONS

        expected = [
            "organism.context_assimilation",
            "organism.context_assimilation.sources",
            "organism.context_assimilation.ingest",
            "organism.context_assimilation.diagnostics",
            "organism.context_assimilation.proposals",
            "organism.context_assimilation.reconciliation_sessions",
            "organism.context_assimilation.start_reconciliation",
            "organism.context_assimilation.sync_policies",
            "organism.context_assimilation.permissions",
            "organism.context_assimilation.environment",
            "organism.context_assimilation.cross_source",
            "organism.context_assimilation.instantiation_diagnostic",
        ]
        for action in expected:
            assert action in _ACTIONS, f"Missing bridge action: {action}"

    def test_invalid_ids_safe(self):
        from substrate.organism.canonical_update import ProposalStore

        store = ProposalStore(path=_temp_path())
        assert not store.approve("nonexistent-id")
        assert not store.reject("nonexistent-id")

    def test_path_traversal_safe(self):
        from substrate.organism.context_ingestion_engine import _is_safe_path

        assert _is_safe_path("/opt/OS/docs/test.md")
        assert not _is_safe_path("/opt/OS/.env")

    def test_no_raw_traceback_in_bridge(self):
        from transports.api.organism_bridge import _context_assimilation_diagnostic_detail

        result = _context_assimilation_diagnostic_detail({"report_id": "nonexistent"})
        assert "traceback" not in json.dumps(result).lower()

    def test_cockpit_mounted(self):
        import ast
        with open("transports/api/cockpit.py") as f:
            content = f.read()
        assert "cockpit_context_assimilation_routes" in content
        assert "_mount_context_assimilation_router" in content


# ═══════════════════════════════════════════════════════════════════════
# Cockpit Shape (Task 14)
# ═══════════════════════════════════════════════════════════════════════


class TestCockpitShape:
    def test_context_summary_shape(self):
        from transports.api.organism_bridge import _context_assimilation

        result = _context_assimilation({})
        assert result["success"] is True
        data = result["data"]
        assert "sources" in data
        assert "ingestion" in data
        assert "diagnostics" in data
        assert "proposals" in data
        assert "sessions" in data
        assert "permissions" in data
        assert "environment" in data
        assert "cross_source" in data
        assert data["external_writes_disabled"] is True

    def test_sources_shape(self):
        from transports.api.organism_bridge import _context_assimilation_sources

        result = _context_assimilation_sources({})
        assert result["success"] is True

    def test_diagnostics_shape(self):
        from transports.api.organism_bridge import _context_assimilation_diagnostics

        result = _context_assimilation_diagnostics({})
        assert result["success"] is True

    def test_proposals_shape(self):
        from transports.api.organism_bridge import _context_assimilation_proposals

        result = _context_assimilation_proposals({})
        assert result["success"] is True

    def test_sessions_shape(self):
        from transports.api.organism_bridge import _context_assimilation_sessions

        result = _context_assimilation_sessions({})
        assert result["success"] is True

    def test_permissions_shape(self):
        from transports.api.organism_bridge import _context_assimilation_permissions

        result = _context_assimilation_permissions({})
        assert result["success"] is True

    def test_environment_shape(self):
        from transports.api.organism_bridge import _context_assimilation_environment

        result = _context_assimilation_environment({})
        assert result["success"] is True

    def test_cross_source_shape(self):
        from transports.api.organism_bridge import _context_assimilation_cross_source

        result = _context_assimilation_cross_source({})
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════════
# No-Fake-Data / Invariant Checks
# ═══════════════════════════════════════════════════════════════════════


class TestInvariants:
    def test_no_auto_apply_anywhere(self):
        from substrate.organism.canonical_update import CanonicalUpdateProposal

        prop = CanonicalUpdateProposal()
        assert prop.approval_required is True
        assert prop.status != "applied"

    def test_no_external_write_in_sync_policy(self):
        from substrate.organism.sync_policy import ExternalSyncPolicy, WritePolicy

        pol = ExternalSyncPolicy(write_policy=WritePolicy.DISABLED.value)
        assert not pol.evaluate_operation("write_anything")["allowed"]

    def test_exploration_does_not_create_proposals(self):
        from substrate.organism.dex_reconciliation import DexReconciliation

        dex = DexReconciliation()
        result = dex.process_operator_input("Just thinking about maybe trying something new")
        assert result["intent"] == "exploration"
        assert result.get("proposals_count", 0) == 0

    def test_no_silent_canon_mutation_invariant(self):
        from substrate.organism.reconciliation_engine import ReconciliationEngine
        from substrate.organism.source_registry import SourceRegistry
        from substrate.organism.ingestion_job import IngestionJobStore
        from substrate.organism.context_diagnostic import DiagnosticReportStore
        from substrate.organism.canonical_update import ProposalStore, ProposalStatus
        from substrate.organism.reconciliation_session import ReconciliationSessionStore

        ps = ProposalStore(path=_temp_path())
        engine = ReconciliationEngine(
            registry=SourceRegistry(path=_temp_path()),
            job_store=IngestionJobStore(jobs_path=_temp_path("j.jsonl"), items_path=_temp_path("i.jsonl")),
            report_store=DiagnosticReportStore(path=_temp_path()),
            proposal_store=ps,
            session_store=ReconciliationSessionStore(
                sessions_path=_temp_path("s.jsonl"), decisions_path=_temp_path("d.jsonl")
            ),
        )
        sess = engine.start_session(topic="test", mode="reconciliation")
        engine.attach_sources(sess.session_id)
        engine.run_diagnostic(sess.session_id)
        engine.generate_canonical_update_proposals(sess.session_id)
        for prop in ps.list_proposals():
            assert prop.status != ProposalStatus.APPLIED.value

    def test_permission_required_for_filesystem(self):
        from substrate.organism.environment_discovery import FilesystemScope

        scope = FilesystemScope(path="/home/user/Documents")
        assert scope.permission_required is True
        assert scope.allowed is False

    def test_sensitive_cross_linking_requires_confirmation(self):
        from substrate.organism.cross_source_reconciler import CrossSourceReconciler

        reconciler = CrossSourceReconciler(signals_path=_temp_path())
        sig = reconciler.detect_subscription_signal("Figma", ["email"], ["$12/mo"])
        assert sig.requires_operator_confirmation is True
        assert sig.requires_permission is True
