"""Phase 82 — Storage + Memory Discipline v1 tests.

150-230 tests covering storage contracts, policy, gateway, memory discipline,
promotion policy, write validator, audit, views, store compatibility,
observability, API, and CLI integration.
"""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

sys.path.insert(0, "/opt/OS")


# ── 1. Storage Contracts ──────────────────────────────────────────


class TestStorageRecordType(unittest.TestCase):
    def test_all_21_types(self):
        from umh.storage.contracts import StorageRecordType

        self.assertEqual(len(StorageRecordType), 21)

    def test_normalize_known(self):
        from umh.storage.contracts import StorageRecordType, normalize_storage_record_type

        self.assertEqual(normalize_storage_record_type("trace"), StorageRecordType.TRACE)

    def test_normalize_unknown(self):
        from umh.storage.contracts import StorageRecordType, normalize_storage_record_type

        self.assertEqual(normalize_storage_record_type("nonsense"), StorageRecordType.UNKNOWN)

    def test_normalize_case_insensitive(self):
        from umh.storage.contracts import StorageRecordType, normalize_storage_record_type

        self.assertEqual(normalize_storage_record_type("FEEDBACK"), StorageRecordType.FEEDBACK)


class TestStorageScope(unittest.TestCase):
    def test_all_9_scopes(self):
        from umh.storage.contracts import StorageScope

        self.assertEqual(len(StorageScope), 9)

    def test_normalize_scope(self):
        from umh.storage.contracts import StorageScope, normalize_storage_scope

        self.assertEqual(normalize_storage_scope("user"), StorageScope.USER)
        self.assertEqual(normalize_storage_scope("bad"), StorageScope.UNKNOWN)


class TestStorageMutability(unittest.TestCase):
    def test_all_7_mutabilities(self):
        from umh.storage.contracts import StorageMutability

        self.assertEqual(len(StorageMutability), 7)


class TestStorageSource(unittest.TestCase):
    def test_all_12_sources(self):
        from umh.storage.contracts import StorageSource

        self.assertEqual(len(StorageSource), 12)


class TestStorageOperation(unittest.TestCase):
    def test_all_9_operations(self):
        from umh.storage.contracts import StorageOperation

        self.assertEqual(len(StorageOperation), 9)


class TestStorageBackendType(unittest.TestCase):
    def test_all_8_backend_types(self):
        from umh.storage.contracts import StorageBackendType

        self.assertEqual(len(StorageBackendType), 8)


class TestClampConfidence(unittest.TestCase):
    def test_clamp_in_range(self):
        from umh.storage.contracts import clamp_confidence

        self.assertEqual(clamp_confidence(0.5), 0.5)

    def test_clamp_below(self):
        from umh.storage.contracts import clamp_confidence

        self.assertEqual(clamp_confidence(-1.0), 0.0)

    def test_clamp_above(self):
        from umh.storage.contracts import clamp_confidence

        self.assertEqual(clamp_confidence(2.0), 1.0)


class TestStorageRecordDescriptor(unittest.TestCase):
    def test_create_descriptor(self):
        from umh.storage.contracts import (
            StorageRecordDescriptor,
            StorageRecordType,
            StorageScope,
        )

        d = StorageRecordDescriptor(
            record_id="test_1",
            record_type=StorageRecordType.TRACE,
            scope=StorageScope.USER,
        )
        self.assertEqual(d.record_id, "test_1")
        self.assertEqual(d.record_type, StorageRecordType.TRACE)

    def test_to_dict_roundtrip(self):
        from umh.storage.contracts import (
            StorageRecordDescriptor,
            StorageRecordType,
        )

        d = StorageRecordDescriptor(
            record_id="rd_1",
            record_type=StorageRecordType.FEEDBACK,
        )
        data = d.to_dict()
        d2 = StorageRecordDescriptor.from_dict(data)
        self.assertEqual(d2.record_id, "rd_1")
        self.assertEqual(d2.record_type, StorageRecordType.FEEDBACK)

    def test_defaults(self):
        from umh.storage.contracts import (
            StorageBackendType,
            StorageMutability,
            StorageRecordDescriptor,
            StorageRecordType,
            StorageScope,
            StorageSource,
        )

        d = StorageRecordDescriptor(record_id="x")
        self.assertEqual(d.record_type, StorageRecordType.UNKNOWN)
        self.assertEqual(d.scope, StorageScope.UNKNOWN)
        self.assertEqual(d.mutability, StorageMutability.UNKNOWN)
        self.assertEqual(d.source, StorageSource.UNKNOWN)
        self.assertEqual(d.backend_type, StorageBackendType.UNKNOWN)


class TestStorageWriteRequest(unittest.TestCase):
    def test_to_dict(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageWriteRequest,
        )

        d = StorageRecordDescriptor(record_id="w1")
        req = StorageWriteRequest(
            request_id="req_1",
            descriptor=d,
            operation=StorageOperation.APPEND,
        )
        data = req.to_dict()
        self.assertEqual(data["request_id"], "req_1")
        self.assertEqual(data["operation"], "append")


class TestStorageWriteResult(unittest.TestCase):
    def test_to_dict(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageWriteResult

        d = StorageRecordDescriptor(record_id="wr1")
        result = StorageWriteResult(
            request_id="rr_1",
            allowed=True,
            status="written",
            descriptor=d,
        )
        data = result.to_dict()
        self.assertTrue(data["allowed"])
        self.assertEqual(data["status"], "written")


class TestStorageReadRequest(unittest.TestCase):
    def test_effective_limit(self):
        from umh.storage.contracts import StorageReadRequest

        req = StorageReadRequest(request_id="sr_1")
        self.assertEqual(req.effective_limit(), 50)

        req2 = StorageReadRequest(request_id="sr_2", limit=1000)
        self.assertEqual(req2.effective_limit(), 500)


class TestStorageReadResult(unittest.TestCase):
    def test_to_dict(self):
        from umh.storage.contracts import StorageReadResult

        r = StorageReadResult(request_id="srr_1", records=[], total_returned=0)
        data = r.to_dict()
        self.assertEqual(data["total_returned"], 0)


# ── 2. Storage Policy ────────────────────────────────────────────


class TestStoragePolicy(unittest.TestCase):
    def test_default_policy(self):
        from umh.storage.contracts import StorageRecordType
        from umh.storage.policy import build_default_storage_policy

        p = build_default_storage_policy()
        self.assertIn(StorageRecordType.TRACE, p.append_only_types)
        self.assertIn(StorageRecordType.MEMORY_CANDIDATE, p.promotable_types)
        self.assertIn(StorageRecordType.SESSION_STATE, p.mutable_types)

    def test_to_dict(self):
        from umh.storage.policy import build_default_storage_policy

        p = build_default_storage_policy()
        d = p.to_dict()
        self.assertIn("append_only_types", d)
        self.assertIn("mutable_types", d)


class TestClassifyRecordMutability(unittest.TestCase):
    def test_trace_is_append_only(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.TRACE),
            StorageMutability.APPEND_ONLY,
        )

    def test_outcome_is_append_only(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.OUTCOME),
            StorageMutability.APPEND_ONLY,
        )

    def test_feedback_is_append_only(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.FEEDBACK),
            StorageMutability.APPEND_ONLY,
        )

    def test_audit_record_is_append_only(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.AUDIT_RECORD),
            StorageMutability.APPEND_ONLY,
        )

    def test_session_state_is_mutable(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.SESSION_STATE),
            StorageMutability.MUTABLE,
        )

    def test_memory_candidate_is_promotable(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.MEMORY_CANDIDATE),
            StorageMutability.PROMOTABLE,
        )

    def test_ontology_primitive_is_immutable(self):
        from umh.storage.contracts import StorageMutability, StorageRecordType
        from umh.storage.policy import classify_record_mutability

        self.assertEqual(
            classify_record_mutability(StorageRecordType.ONTOLOGY_PRIMITIVE),
            StorageMutability.IMMUTABLE,
        )


class TestIsAppendOnly(unittest.TestCase):
    def test_trace_yes(self):
        from umh.storage.contracts import StorageRecordType
        from umh.storage.policy import is_append_only

        self.assertTrue(is_append_only(StorageRecordType.TRACE))

    def test_session_no(self):
        from umh.storage.contracts import StorageRecordType
        from umh.storage.policy import is_append_only

        self.assertFalse(is_append_only(StorageRecordType.SESSION_STATE))


class TestEvaluateStorageOperation(unittest.TestCase):
    def test_delete_always_denied(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t1", record_type=StorageRecordType.TRACE)
        result = evaluate_storage_operation(
            d, StorageOperation.DELETE, build_default_storage_policy()
        )
        self.assertFalse(result.allowed)

    def test_read_always_allowed(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t2", record_type=StorageRecordType.TRACE)
        result = evaluate_storage_operation(
            d, StorageOperation.READ, build_default_storage_policy()
        )
        self.assertTrue(result.allowed)

    def test_append_on_append_only_allowed(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t3", record_type=StorageRecordType.TRACE)
        result = evaluate_storage_operation(
            d, StorageOperation.APPEND, build_default_storage_policy()
        )
        self.assertTrue(result.allowed)

    def test_update_on_append_only_denied(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t4", record_type=StorageRecordType.FEEDBACK)
        result = evaluate_storage_operation(
            d, StorageOperation.UPDATE, build_default_storage_policy()
        )
        self.assertFalse(result.allowed)

    def test_immutable_denies_write(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(
            record_id="t5", record_type=StorageRecordType.ONTOLOGY_PRIMITIVE
        )
        result = evaluate_storage_operation(
            d, StorageOperation.WRITE, build_default_storage_policy()
        )
        self.assertFalse(result.allowed)

    def test_mutable_allows_update(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t6", record_type=StorageRecordType.SESSION_STATE)
        result = evaluate_storage_operation(
            d, StorageOperation.UPDATE, build_default_storage_policy()
        )
        self.assertTrue(result.allowed)

    def test_unknown_type_denies_writes(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t7", record_type=StorageRecordType.UNKNOWN)
        result = evaluate_storage_operation(
            d, StorageOperation.WRITE, build_default_storage_policy()
        )
        self.assertFalse(result.allowed)

    def test_list_always_allowed(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(record_id="t8", record_type=StorageRecordType.UNKNOWN)
        result = evaluate_storage_operation(
            d, StorageOperation.LIST, build_default_storage_policy()
        )
        self.assertTrue(result.allowed)


# ── 3. Storage Gateway ────────────────────────────────────────────


class TestInMemoryStorageBackend(unittest.TestCase):
    def test_append_and_read(self):
        from umh.storage.contracts import StorageRecordDescriptor
        from umh.storage.gateway import InMemoryStorageBackend

        be = InMemoryStorageBackend()
        d = StorageRecordDescriptor(record_id="imr_1")
        be.append(d, {"key": "value"})
        rec = be.read("imr_1")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["payload"]["key"], "value")

    def test_read_missing(self):
        from umh.storage.gateway import InMemoryStorageBackend

        be = InMemoryStorageBackend()
        self.assertIsNone(be.read("missing"))

    def test_update_existing(self):
        from umh.storage.contracts import StorageRecordDescriptor
        from umh.storage.gateway import InMemoryStorageBackend

        be = InMemoryStorageBackend()
        d = StorageRecordDescriptor(record_id="imr_2")
        be.append(d, {"v": 1})
        d2 = StorageRecordDescriptor(record_id="imr_2")
        self.assertTrue(be.update(d2, {"v": 2}))
        self.assertEqual(be.read("imr_2")["payload"]["v"], 2)

    def test_update_missing(self):
        from umh.storage.contracts import StorageRecordDescriptor
        from umh.storage.gateway import InMemoryStorageBackend

        be = InMemoryStorageBackend()
        d = StorageRecordDescriptor(record_id="missing")
        self.assertFalse(be.update(d, {}))

    def test_list_descriptors(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import InMemoryStorageBackend

        be = InMemoryStorageBackend()
        d1 = StorageRecordDescriptor(record_id="l1", record_type=StorageRecordType.TRACE)
        d2 = StorageRecordDescriptor(record_id="l2", record_type=StorageRecordType.FEEDBACK)
        be.append(d1)
        be.append(d2)
        all_descs = be.list_descriptors()
        self.assertEqual(len(all_descs), 2)
        typed = be.list_descriptors(record_type=StorageRecordType.TRACE)
        self.assertEqual(len(typed), 1)


class TestStorageGateway(unittest.TestCase):
    def test_append_trace(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_1", record_type=StorageRecordType.TRACE)
        result = gw.append(d, {"data": 1})
        self.assertTrue(result.allowed)
        self.assertEqual(result.status, "written")

    def test_update_trace_denied(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_2", record_type=StorageRecordType.TRACE)
        gw.append(d)
        result = gw.update(d)
        self.assertFalse(result.allowed)

    def test_delete_always_denied(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
            StorageWriteRequest,
        )
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_3", record_type=StorageRecordType.SESSION_STATE)
        req = StorageWriteRequest(
            request_id="del_1",
            descriptor=d,
            operation=StorageOperation.DELETE,
        )
        result = gw.write(req)
        self.assertFalse(result.allowed)

    def test_audit_log(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_4", record_type=StorageRecordType.TRACE)
        gw.append(d)
        audit = gw.audit()
        self.assertGreater(len(audit), 0)
        self.assertEqual(audit[0]["operation"], "append")

    def test_read_by_id(self):
        from umh.storage.contracts import (
            StorageReadRequest,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_5", record_type=StorageRecordType.FEEDBACK)
        gw.append(d, {"note": "test"})
        req = StorageReadRequest(request_id="rd_1", record_id="gw_5")
        result = gw.read(req)
        self.assertEqual(result.total_returned, 1)

    def test_read_missing(self):
        from umh.storage.contracts import StorageReadRequest
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        req = StorageReadRequest(request_id="rd_2", record_id="missing_id")
        result = gw.read(req)
        self.assertEqual(result.total_returned, 0)

    def test_to_dict(self):
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = gw.to_dict()
        self.assertIn("backend_count", d)
        self.assertIn("policy", d)

    def test_promote_disabled(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(
            record_id="gw_6", record_type=StorageRecordType.MEMORY_CANDIDATE
        )
        gw.append(d)
        result = gw.promote(d)
        self.assertFalse(result.allowed)

    def test_update_mutable_allowed(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_7", record_type=StorageRecordType.SESSION_STATE)
        gw.append(d, {"v": 1})
        result = gw.update(d, {"v": 2})
        self.assertTrue(result.allowed)


# ── 4. Memory Discipline ─────────────────────────────────────────


class TestMemoryRecordType(unittest.TestCase):
    def test_all_11_types(self):
        from umh.memory.discipline import MemoryRecordType

        self.assertEqual(len(MemoryRecordType), 11)

    def test_normalize(self):
        from umh.memory.discipline import MemoryRecordType, normalize_memory_record_type

        self.assertEqual(normalize_memory_record_type("episodic"), MemoryRecordType.EPISODIC)
        self.assertEqual(normalize_memory_record_type("junk"), MemoryRecordType.UNKNOWN)


class TestMemoryScope(unittest.TestCase):
    def test_all_6_scopes(self):
        from umh.memory.discipline import MemoryScope

        self.assertEqual(len(MemoryScope), 6)


class TestMemoryStatus(unittest.TestCase):
    def test_all_7_statuses(self):
        from umh.memory.discipline import MemoryStatus

        self.assertEqual(len(MemoryStatus), 7)


class TestMemoryWritePolicy(unittest.TestCase):
    def test_defaults(self):
        from umh.memory.discipline import build_default_memory_write_policy

        p = build_default_memory_write_policy()
        self.assertFalse(p.allow_auto_promotion)
        self.assertTrue(p.require_source)
        self.assertTrue(p.require_confidence)
        self.assertAlmostEqual(p.min_confidence, 0.2)

    def test_to_dict(self):
        from umh.memory.discipline import build_default_memory_write_policy

        p = build_default_memory_write_policy()
        d = p.to_dict()
        self.assertIn("allow_auto_promotion", d)
        self.assertFalse(d["allow_auto_promotion"])


class TestMemoryRecord(unittest.TestCase):
    def test_create_and_to_dict(self):
        from umh.memory.discipline import MemoryRecord

        r = MemoryRecord(memory_id="mem_test1", content="test content", source="system")
        d = r.to_dict()
        self.assertEqual(d["memory_id"], "mem_test1")
        self.assertEqual(d["content"], "test content")

    def test_from_dict_roundtrip(self):
        from umh.memory.discipline import MemoryRecord

        r = MemoryRecord(memory_id="mem_test2", content="hello", source="user")
        d = r.to_dict()
        r2 = MemoryRecord.from_dict(d)
        self.assertEqual(r2.memory_id, "mem_test2")
        self.assertEqual(r2.content, "hello")


class TestClampConfidenceMemory(unittest.TestCase):
    def test_clamp(self):
        from umh.memory.discipline import clamp_confidence

        self.assertEqual(clamp_confidence(0.5), 0.5)
        self.assertEqual(clamp_confidence(-0.5), 0.0)
        self.assertEqual(clamp_confidence(1.5), 1.0)


class TestClassifyMemoryCandidate(unittest.TestCase):
    def test_episodic(self):
        from umh.memory.discipline import MemoryRecordType, classify_memory_candidate

        @dataclass
        class FakeCandidate:
            memory_type: str = "episodic"

        self.assertEqual(classify_memory_candidate(FakeCandidate()), MemoryRecordType.EPISODIC)

    def test_unknown(self):
        from umh.memory.discipline import MemoryRecordType, classify_memory_candidate

        @dataclass
        class FakeCandidate:
            memory_type: str = "something_weird"

        self.assertEqual(classify_memory_candidate(FakeCandidate()), MemoryRecordType.UNKNOWN)

    def test_none_type(self):
        from umh.memory.discipline import MemoryRecordType, classify_memory_candidate

        self.assertEqual(classify_memory_candidate(object()), MemoryRecordType.UNKNOWN)


class TestCreateMemoryRecordFromCandidate(unittest.TestCase):
    def test_creates_needs_review(self):
        from umh.memory.discipline import MemoryStatus, create_memory_record_from_candidate

        @dataclass
        class FakeCandidate:
            candidate_id: str = "cand_1"
            content: str = "Test content"
            confidence: float = 0.7
            evidence: list[str] = field(default_factory=lambda: ["ev1"])
            memory_type: str = "episodic"
            user_id: str = "u1"
            session_id: str = "s1"
            reason: str = "because"
            source: str = ""

        record = create_memory_record_from_candidate(FakeCandidate())
        self.assertEqual(record.status, MemoryStatus.NEEDS_REVIEW)
        self.assertEqual(record.content, "Test content")
        self.assertTrue(record.memory_id.startswith("mem_"))


class TestIsMemoryPromotable(unittest.TestCase):
    def test_promotable_with_evidence(self):
        from umh.memory.discipline import is_memory_promotable

        @dataclass
        class FakeCandidate:
            confidence: float = 0.5
            content: str = "some content"
            evidence: list[str] = field(default_factory=lambda: ["e1"])

        self.assertTrue(is_memory_promotable(FakeCandidate()))

    def test_not_promotable_low_confidence(self):
        from umh.memory.discipline import is_memory_promotable

        @dataclass
        class FakeCandidate:
            confidence: float = 0.1
            content: str = "content"
            evidence: list[str] = field(default_factory=lambda: ["e1"])

        self.assertFalse(is_memory_promotable(FakeCandidate()))

    def test_not_promotable_no_content(self):
        from umh.memory.discipline import is_memory_promotable

        @dataclass
        class FakeCandidate:
            confidence: float = 0.5
            content: str = ""
            evidence: list[str] = field(default_factory=lambda: ["e1"])

        self.assertFalse(is_memory_promotable(FakeCandidate()))


class TestValidateMemoryRecord(unittest.TestCase):
    def test_valid_record(self):
        from umh.memory.discipline import MemoryRecord, validate_memory_record

        r = MemoryRecord(
            memory_id="mem_v1",
            content="test",
            source="system",
            confidence=0.5,
            evidence=["ev1"],
        )
        issues = validate_memory_record(r)
        self.assertEqual(issues, [])

    def test_missing_source(self):
        from umh.memory.discipline import MemoryRecord, validate_memory_record

        r = MemoryRecord(memory_id="mem_v2", content="test", source="", evidence=["e"])
        issues = validate_memory_record(r)
        self.assertTrue(any("source" in i for i in issues))

    def test_no_content(self):
        from umh.memory.discipline import MemoryRecord, validate_memory_record

        r = MemoryRecord(memory_id="mem_v3", content="", source="system", evidence=["e"])
        issues = validate_memory_record(r)
        self.assertTrue(any("content" in i for i in issues))

    def test_promoted_status_flagged(self):
        from umh.memory.discipline import MemoryRecord, MemoryStatus, validate_memory_record

        r = MemoryRecord(
            memory_id="mem_v4",
            content="test",
            source="system",
            status=MemoryStatus.PROMOTED,
            evidence=["e"],
        )
        issues = validate_memory_record(r)
        self.assertTrue(any("promotion" in i.lower() for i in issues))


class TestExplainMemoryWriteDecision(unittest.TestCase):
    def test_explain(self):
        from umh.memory.discipline import explain_memory_write_decision

        @dataclass
        class FakeCandidate:
            confidence: float = 0.5
            content: str = "hello"
            evidence: list[str] = field(default_factory=lambda: ["e1"])
            memory_type: str = "episodic"

        result = explain_memory_write_decision(FakeCandidate())
        self.assertIn("memory_type", result)
        self.assertIn("promotable", result)
        self.assertFalse(result["auto_promotion_enabled"])


# ── 5. Promotion Policy ──────────────────────────────────────────


class TestPromotionDecisionStatus(unittest.TestCase):
    def test_all_6_statuses(self):
        from umh.memory.promotion_policy import PromotionDecisionStatus

        self.assertEqual(len(PromotionDecisionStatus), 6)


class TestEvaluateMemoryCandidateForPromotion(unittest.TestCase):
    def test_auto_promotion_disabled(self):
        from umh.memory.promotion_policy import (
            PromotionDecisionStatus,
            evaluate_memory_candidate_for_promotion,
        )

        @dataclass
        class FakeCandidate:
            candidate_id: str = "c1"
            user_id: str = "u1"
            confidence: float = 0.8
            evidence: list[str] = field(default_factory=lambda: ["e1"])
            content: str = "hello"

        decision = evaluate_memory_candidate_for_promotion(FakeCandidate())
        self.assertEqual(decision.status, PromotionDecisionStatus.DISABLED)

    def test_insufficient_evidence(self):
        from umh.memory.discipline import MemoryWritePolicy
        from umh.memory.promotion_policy import (
            PromotionDecisionStatus,
            evaluate_memory_candidate_for_promotion,
        )

        policy = MemoryWritePolicy(allow_auto_promotion=True)

        @dataclass
        class FakeCandidate:
            candidate_id: str = "c2"
            user_id: str = "u2"
            confidence: float = 0.8
            evidence: list[str] = field(default_factory=list)
            content: str = "hello"

        decision = evaluate_memory_candidate_for_promotion(FakeCandidate(), policy)
        self.assertEqual(decision.status, PromotionDecisionStatus.INSUFFICIENT_EVIDENCE)

    def test_needs_review_when_enabled(self):
        from umh.memory.discipline import MemoryWritePolicy
        from umh.memory.promotion_policy import (
            PromotionDecisionStatus,
            evaluate_memory_candidate_for_promotion,
        )

        policy = MemoryWritePolicy(allow_auto_promotion=True)

        @dataclass
        class FakeCandidate:
            candidate_id: str = "c3"
            user_id: str = "u3"
            confidence: float = 0.8
            evidence: list[str] = field(default_factory=lambda: ["ev"])
            content: str = "hello"

        decision = evaluate_memory_candidate_for_promotion(FakeCandidate(), policy)
        self.assertEqual(decision.status, PromotionDecisionStatus.NEEDS_REVIEW)

    def test_to_dict_roundtrip(self):
        from umh.memory.promotion_policy import MemoryPromotionDecision, PromotionDecisionStatus

        d = MemoryPromotionDecision(
            decision_id="mpd_1",
            status=PromotionDecisionStatus.DISABLED,
            reason="test",
        )
        data = d.to_dict()
        d2 = MemoryPromotionDecision.from_dict(data)
        self.assertEqual(d2.decision_id, "mpd_1")
        self.assertEqual(d2.status, PromotionDecisionStatus.DISABLED)


# ── 6. Write Validator ───────────────────────────────────────────


class TestValidateMemorySource(unittest.TestCase):
    def test_empty_source(self):
        from umh.memory.write_validator import validate_memory_source

        issues = validate_memory_source("")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")

    def test_valid_source(self):
        from umh.memory.write_validator import validate_memory_source

        issues = validate_memory_source("system")
        self.assertEqual(len(issues), 0)


class TestValidateMemoryConfidence(unittest.TestCase):
    def test_clamped(self):
        from umh.memory.write_validator import validate_memory_confidence

        issues = validate_memory_confidence(1.5)
        self.assertTrue(any("clamped" in i.message.lower() for i in issues))

    def test_below_minimum(self):
        from umh.memory.write_validator import validate_memory_confidence

        issues = validate_memory_confidence(0.05, min_confidence=0.2)
        self.assertTrue(any("below" in i.message.lower() for i in issues))


class TestValidateMemoryEvidence(unittest.TestCase):
    def test_no_evidence(self):
        from umh.memory.write_validator import validate_memory_evidence

        issues = validate_memory_evidence(None)
        self.assertEqual(len(issues), 1)

    def test_with_evidence(self):
        from umh.memory.write_validator import validate_memory_evidence

        issues = validate_memory_evidence(["e1"])
        self.assertEqual(len(issues), 0)


class TestValidateNoAutoPromotion(unittest.TestCase):
    def test_promoted_status_blocked(self):
        from umh.memory.write_validator import validate_no_auto_promotion

        @dataclass
        class Fake:
            status: str = "promoted"

        issues = validate_no_auto_promotion(Fake())
        self.assertTrue(any("promoted" in i.message.lower() for i in issues))

    def test_non_promoted_ok(self):
        from umh.memory.write_validator import validate_no_auto_promotion

        @dataclass
        class Fake:
            status: str = "candidate"

        issues = validate_no_auto_promotion(Fake())
        self.assertEqual(len(issues), 0)


class TestValidateMemoryCandidate(unittest.TestCase):
    def test_valid_candidate(self):
        from umh.memory.write_validator import validate_memory_candidate

        @dataclass
        class Fake:
            candidate_id: str = "c1"
            content: str = "hello"
            source: str = "system"
            confidence: float = 0.5
            evidence: list[str] = field(default_factory=lambda: ["e1"])

        result = validate_memory_candidate(Fake())
        self.assertTrue(result.valid)

    def test_invalid_no_source(self):
        from umh.memory.write_validator import validate_memory_candidate

        @dataclass
        class Fake:
            candidate_id: str = "c2"
            content: str = "hello"
            source: str = ""
            confidence: float = 0.5
            evidence: list[str] = field(default_factory=list)

        result = validate_memory_candidate(Fake())
        self.assertTrue(len(result.issues) > 0)


class TestValidateMemoryWrite(unittest.TestCase):
    def test_valid_write(self):
        from umh.memory.discipline import MemoryRecord
        from umh.memory.write_validator import validate_memory_write

        r = MemoryRecord(
            memory_id="mw_1",
            content="test",
            source="system",
            confidence=0.5,
            evidence=["e1"],
        )
        result = validate_memory_write(r)
        self.assertTrue(result.valid)

    def test_invalid_no_content(self):
        from umh.memory.discipline import MemoryRecord
        from umh.memory.write_validator import validate_memory_write

        r = MemoryRecord(
            memory_id="mw_2",
            content="",
            source="system",
            confidence=0.5,
            evidence=["e1"],
        )
        result = validate_memory_write(r)
        self.assertFalse(result.valid)


# ── 7. Storage Audit ─────────────────────────────────────────────


class TestStorageAuditSeverity(unittest.TestCase):
    def test_severity_constants(self):
        from umh.storage.audit import StorageAuditSeverity

        self.assertEqual(StorageAuditSeverity.INFO, "info")
        self.assertEqual(StorageAuditSeverity.CRITICAL, "critical")


class TestScanForDirectFileWrites(unittest.TestCase):
    def test_detects_open_write(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_direct_file_writes

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = open('file.txt', 'w')\n")
            f.flush()
            findings = scan_for_direct_file_writes([Path(f.name)])
        self.assertTrue(len(findings) > 0)
        self.assertEqual(findings[0].finding_type, "direct_file_write")

    def test_ignores_comments(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_direct_file_writes

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# open('file.txt', 'w')\n")
            f.flush()
            findings = scan_for_direct_file_writes([Path(f.name)])
        self.assertEqual(len(findings), 0)


class TestScanForJsonDumpWrites(unittest.TestCase):
    def test_detects_json_dump(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_json_dump_writes

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("json.dump(data, fp)\n")
            f.flush()
            findings = scan_for_json_dump_writes([Path(f.name)])
        self.assertTrue(len(findings) > 0)

    def test_ignores_json_dumps(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_json_dump_writes

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("result = json.dumps(data)\n")
            f.flush()
            findings = scan_for_json_dump_writes([Path(f.name)])
        self.assertEqual(len(findings), 0)


class TestScanForDeleteClearPop(unittest.TestCase):
    def test_detects_os_remove(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_delete_clear_pop_methods

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("os.remove(path)\n")
            f.flush()
            findings = scan_for_delete_clear_pop_methods([Path(f.name)])
        self.assertTrue(len(findings) > 0)


class TestScanForAppendOnlyViolations(unittest.TestCase):
    def test_detects_delete_from_traces(self):
        import tempfile
        from pathlib import Path

        from umh.storage.audit import scan_for_append_only_violations

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('cursor.execute("DELETE FROM traces WHERE id=1")\n')
            f.flush()
            findings = scan_for_append_only_violations([Path(f.name)])
        self.assertTrue(len(findings) > 0)
        self.assertEqual(findings[0].severity, "error")


class TestAuditStorageBoundaries(unittest.TestCase):
    def test_returns_report(self):
        from umh.storage.audit import audit_storage_boundaries

        report = audit_storage_boundaries(root_path="/opt/OS/umh")
        self.assertIsNotNone(report.generated_at)
        self.assertGreaterEqual(report.total_findings, 0)


class TestStorageAuditFinding(unittest.TestCase):
    def test_to_dict(self):
        from umh.storage.audit import StorageAuditFinding

        f = StorageAuditFinding(
            finding_id="saf_test1",
            severity="warning",
            finding_type="test",
            message="test finding",
        )
        d = f.to_dict()
        self.assertEqual(d["finding_id"], "saf_test1")


# ── 8. Views ─────────────────────────────────────────────────────


class TestStorageDescriptorView(unittest.TestCase):
    def test_build_descriptor_view(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.views import build_descriptor_view

        d = StorageRecordDescriptor(record_id="dv_1", record_type=StorageRecordType.TRACE)
        view = build_descriptor_view(d)
        self.assertEqual(view.record_id, "dv_1")
        self.assertEqual(view.record_type, "trace")

    def test_to_dict(self):
        from umh.storage.contracts import StorageRecordDescriptor
        from umh.storage.views import build_descriptor_view

        d = StorageRecordDescriptor(record_id="dv_2")
        view = build_descriptor_view(d)
        data = view.to_dict()
        self.assertIn("record_id", data)


class TestStorageHealthView(unittest.TestCase):
    def test_build_health_view(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.views import build_storage_health_view

        descs = [
            StorageRecordDescriptor(record_id="h1", record_type=StorageRecordType.TRACE),
            StorageRecordDescriptor(record_id="h2", record_type=StorageRecordType.SESSION_STATE),
        ]
        view = build_storage_health_view(descs)
        self.assertEqual(view.total_records, 2)
        self.assertEqual(view.append_only_count, 1)
        self.assertEqual(view.mutable_count, 1)

    def test_to_dict(self):
        from umh.storage.views import build_storage_health_view

        view = build_storage_health_view([])
        data = view.to_dict()
        self.assertIn("total_records", data)
        self.assertEqual(data["total_records"], 0)


class TestStorageAuditView(unittest.TestCase):
    def test_build_audit_view(self):
        from umh.storage.audit import StorageAuditFinding, StorageAuditReport
        from umh.storage.views import build_storage_audit_view

        report = StorageAuditReport(
            generated_at="2026-01-01",
            findings=[
                StorageAuditFinding(finding_id="f1", severity="warning", finding_type="test"),
            ],
            total_findings=1,
            warning_count=1,
        )
        view = build_storage_audit_view(report)
        self.assertEqual(view.total_findings, 1)
        self.assertEqual(view.warning_count, 1)


class TestMemoryCandidateDisciplineView(unittest.TestCase):
    def test_build_view(self):
        from umh.memory.views import build_candidate_discipline_view

        @dataclass
        class Fake:
            candidate_id: str = "cd_1"
            content: str = "test content"
            confidence: float = 0.7
            evidence: list[str] = field(default_factory=lambda: ["e1"])
            memory_type: str = "episodic"
            reason: str = "test reason"

        view = build_candidate_discipline_view(Fake())
        self.assertEqual(view.candidate_id, "cd_1")
        self.assertTrue(view.promotable)
        self.assertEqual(view.memory_type, "episodic")

    def test_not_promotable(self):
        from umh.memory.views import build_candidate_discipline_view

        @dataclass
        class Fake:
            candidate_id: str = "cd_2"
            content: str = ""
            confidence: float = 0.1
            evidence: list[str] = field(default_factory=list)
            memory_type: str = "unknown"
            reason: str = ""

        view = build_candidate_discipline_view(Fake())
        self.assertFalse(view.promotable)
        self.assertTrue(len(view.validation_issues) > 0)


class TestMemoryDisciplineHealthView(unittest.TestCase):
    def test_build_health_view(self):
        from umh.memory.views import build_memory_discipline_health_view

        view = build_memory_discipline_health_view()
        self.assertFalse(view.auto_promotion_enabled)
        self.assertEqual(view.total_candidates, 0)

    def test_to_dict(self):
        from umh.memory.views import build_memory_discipline_health_view

        view = build_memory_discipline_health_view()
        data = view.to_dict()
        self.assertIn("auto_promotion_enabled", data)
        self.assertIn("policy_summary", data)


# ── 9. Store Compatibility ───────────────────────────────────────


class TestTraceStoreExportDescriptors(unittest.TestCase):
    def test_export_from_in_memory(self):
        from umh.control.trace_store import InMemoryTraceStore, export_storage_descriptors

        store = InMemoryTraceStore()
        store.create_trace(user_id="u1", input_summary="test")
        descs = export_storage_descriptors(store)
        self.assertEqual(len(descs), 1)
        self.assertEqual(descs[0].record_type.value, "trace")


class TestFeedbackStoreExportDescriptors(unittest.TestCase):
    def test_export_outcomes(self):
        from umh.feedback.outcome import OutcomeRecord, OutcomeStatus
        from umh.feedback.store import FeedbackStore, export_storage_descriptors

        store = FeedbackStore()
        store.append_outcome(
            OutcomeRecord(
                outcome_id="oc_1",
                trace_id="t1",
                user_id="u1",
                status=OutcomeStatus.SUCCESS,
            )
        )
        descs = export_storage_descriptors(store)
        has_outcome = any(d.record_type.value == "outcome" for d in descs)
        self.assertTrue(has_outcome)


class TestSessionStoreExportDescriptors(unittest.TestCase):
    def test_export_sessions(self):
        from umh.workstation.session_state import SessionStore, export_storage_descriptors

        store = SessionStore()
        store.create_session(user_id="u1")
        descs = export_storage_descriptors(store)
        self.assertEqual(len(descs), 1)
        self.assertEqual(descs[0].record_type.value, "session_state")


class TestDeviceRegistryExportDescriptors(unittest.TestCase):
    def test_export_devices(self):
        from umh.workstation.device_registry import (
            DeviceRecord,
            DeviceRegistry,
            export_storage_descriptors,
        )

        reg = DeviceRegistry()
        reg.register_device(DeviceRecord(device_id="dev1", name="VPS"))
        descs = export_storage_descriptors(reg)
        self.assertEqual(len(descs), 1)
        self.assertEqual(descs[0].record_type.value, "device_registry")

    def test_none_registry(self):
        from umh.workstation.device_registry import export_storage_descriptors

        descs = export_storage_descriptors(None)
        self.assertEqual(len(descs), 0)


class TestEnvironmentRegistryExportDescriptors(unittest.TestCase):
    def test_export_environments(self):
        from umh.workstation.environment_registry import (
            WorkstationEnvironmentRecord,
            WorkstationEnvironmentRegistry,
            export_storage_descriptors,
        )

        reg = WorkstationEnvironmentRegistry()
        reg.register_environment(
            WorkstationEnvironmentRecord(
                environment_id="local",
                name="Local",
            )
        )
        descs = export_storage_descriptors(reg)
        self.assertEqual(len(descs), 1)
        self.assertEqual(descs[0].record_type.value, "environment_registry")


# ── 10. Registry/Ontology Compatibility ──────────────────────────


class TestOntologyPrimitivesExportDescriptors(unittest.TestCase):
    def test_export(self):
        from umh.ontology.primitives import export_storage_descriptors

        descs = export_storage_descriptors()
        self.assertGreater(len(descs), 0)
        self.assertEqual(descs[0].record_type.value, "ontology_primitive")
        self.assertEqual(descs[0].mutability.value, "immutable")


class TestOntologyLawsExportDescriptors(unittest.TestCase):
    def test_export(self):
        from umh.ontology.laws import export_storage_descriptors

        descs = export_storage_descriptors()
        self.assertGreater(len(descs), 0)
        self.assertEqual(descs[0].record_type.value, "ontology_law")


class TestRegistryCatalogExportDescriptors(unittest.TestCase):
    def test_export(self):
        from umh.registry.catalog import export_storage_descriptors

        descs = export_storage_descriptors()
        self.assertGreaterEqual(len(descs), 0)


# ── 11. Observability Integration ────────────────────────────────


class TestCheckStorageGateway(unittest.TestCase):
    def test_none_unavailable(self):
        from umh.observability.system_status import check_storage_gateway

        cs = check_storage_gateway(None)
        self.assertFalse(cs.available)

    def test_with_gateway(self):
        from umh.observability.system_status import check_storage_gateway
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        cs = check_storage_gateway(gw)
        self.assertTrue(cs.available)
        self.assertEqual(cs.status, "ok")


class TestCheckMemoryDiscipline(unittest.TestCase):
    def test_available(self):
        from umh.observability.system_status import check_memory_discipline

        cs = check_memory_discipline()
        self.assertTrue(cs.available)
        self.assertEqual(cs.status, "ok")
        self.assertIn("auto_promotion", cs.detail)


class TestBuildSystemStatusWithPhase82(unittest.TestCase):
    def test_includes_storage_and_memory(self):
        from umh.observability.system_status import build_system_status
        from umh.storage.gateway import StorageGateway

        status = build_system_status(storage_gateway=StorageGateway())
        d = status.to_dict()
        self.assertIn("storage_gateway_status", d)
        self.assertIn("memory_discipline_status", d)
        self.assertEqual(d["storage_gateway_status"], "ok")
        self.assertEqual(d["memory_discipline_status"], "ok")


class TestOperatorDashboardPhase82Fields(unittest.TestCase):
    def test_dashboard_has_storage_memory_fields(self):
        from umh.interface.views import OperatorDashboardSnapshot

        snap = OperatorDashboardSnapshot(user_id="u1")
        d = snap.to_dict()
        self.assertIn("storage_summary", d)
        self.assertIn("memory_discipline_summary", d)


# ── 12. API Integration ──────────────────────────────────────────


class TestApiEndpointsExist(unittest.TestCase):
    def test_storage_endpoints_registered(self):
        from umh.control.api import app

        paths = [r.path for r in app.routes if hasattr(r, "path")]
        self.assertIn("/storage/status", paths)
        self.assertIn("/storage/descriptors", paths)
        self.assertIn("/storage/audit", paths)
        self.assertIn("/storage/policy", paths)

    def test_memory_discipline_endpoints_registered(self):
        from umh.control.api import app

        paths = [r.path for r in app.routes if hasattr(r, "path")]
        self.assertIn("/memory/discipline/status", paths)
        self.assertIn("/memory/discipline/policy", paths)
        self.assertIn("/memory/discipline/promotion-policy", paths)


# ── 13. CLI Integration ──────────────────────────────────────────


class TestCliParserHasCommands(unittest.TestCase):
    def test_storage_commands(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        # Check that the subparsers include the storage commands
        choices = parser._subparsers._group_actions[0].choices
        self.assertIn("storage-status", choices)
        self.assertIn("storage-descriptors", choices)
        self.assertIn("storage-audit", choices)
        self.assertIn("storage-policy", choices)

    def test_memory_discipline_commands(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertIn("memory-discipline-status", choices)
        self.assertIn("memory-discipline-policy", choices)


class TestCliStorageStatus(unittest.TestCase):
    def test_runs(self):
        from umh.control.cli import main

        rc = main(["storage-status", "--json"])
        self.assertEqual(rc, 0)


class TestCliStoragePolicy(unittest.TestCase):
    def test_runs(self):
        from umh.control.cli import main

        rc = main(["storage-policy", "--json"])
        self.assertEqual(rc, 0)


class TestCliMemoryDisciplineStatus(unittest.TestCase):
    def test_runs(self):
        from umh.control.cli import main

        rc = main(["memory-discipline-status", "--json"])
        self.assertEqual(rc, 0)


class TestCliMemoryDisciplinePolicy(unittest.TestCase):
    def test_runs(self):
        from umh.control.cli import main

        rc = main(["memory-discipline-policy", "--json"])
        self.assertEqual(rc, 0)


# ── 14. Cross-cutting invariants ─────────────────────────────────


class TestInvariantAppendOnlyTypesDenyUpdate(unittest.TestCase):
    """INV-521: Append-only types deny UPDATE."""

    def test_all_append_only_deny_update(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import (
            _APPEND_ONLY_TYPES,
            build_default_storage_policy,
            evaluate_storage_operation,
        )

        policy = build_default_storage_policy()
        for rt in _APPEND_ONLY_TYPES:
            d = StorageRecordDescriptor(record_id="inv_test", record_type=rt)
            result = evaluate_storage_operation(d, StorageOperation.UPDATE, policy)
            self.assertFalse(result.allowed, f"{rt.value} should deny UPDATE")


class TestInvariantDeleteAlwaysDenied(unittest.TestCase):
    """INV-522: DELETE always denied."""

    def test_delete_denied_for_all_types(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        policy = build_default_storage_policy()
        for rt in StorageRecordType:
            d = StorageRecordDescriptor(record_id="del_test", record_type=rt)
            result = evaluate_storage_operation(d, StorageOperation.DELETE, policy)
            self.assertFalse(result.allowed, f"{rt.value} should deny DELETE")


class TestInvariantAutoPromotionDisabled(unittest.TestCase):
    """INV-523: Auto-promotion disabled by default."""

    def test_default_policy_no_auto_promotion(self):
        from umh.memory.discipline import build_default_memory_write_policy

        mp = build_default_memory_write_policy()
        self.assertFalse(mp.allow_auto_promotion)


class TestInvariantImmutableDeniesAllWrites(unittest.TestCase):
    """INV-524: Immutable types deny all writes."""

    def test_immutable_denies_write_update(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import (
            _IMMUTABLE_TYPES,
            build_default_storage_policy,
            evaluate_storage_operation,
        )

        policy = build_default_storage_policy()
        for rt in _IMMUTABLE_TYPES:
            for op in (StorageOperation.WRITE, StorageOperation.UPDATE, StorageOperation.APPEND):
                d = StorageRecordDescriptor(record_id="imm_test", record_type=rt)
                result = evaluate_storage_operation(d, op, policy)
                self.assertFalse(result.allowed, f"{rt.value} should deny {op.value}")


class TestInvariantGatewayEnforcesPolicy(unittest.TestCase):
    """INV-525: Gateway enforces policy on every write."""

    def test_all_writes_go_through_policy(self):
        from umh.storage.contracts import StorageRecordDescriptor, StorageRecordType
        from umh.storage.gateway import StorageGateway

        gw = StorageGateway()
        d = StorageRecordDescriptor(record_id="gw_inv", record_type=StorageRecordType.TRACE)
        gw.append(d, {"x": 1})
        audit = gw.audit()
        self.assertEqual(len(audit), 1)
        self.assertIn("allowed", audit[0])


class TestInvariantReadAlwaysAllowed(unittest.TestCase):
    """INV-526: READ is always allowed."""

    def test_read_for_all_types(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        policy = build_default_storage_policy()
        for rt in StorageRecordType:
            d = StorageRecordDescriptor(record_id="rd_inv", record_type=rt)
            result = evaluate_storage_operation(d, StorageOperation.READ, policy)
            self.assertTrue(result.allowed, f"{rt.value} should allow READ")


class TestInvariantPromotionRequiresFutureEngine(unittest.TestCase):
    """INV-527: PROMOTE on PROMOTABLE requires future engine."""

    def test_promote_denied_on_candidate(self):
        from umh.storage.contracts import (
            StorageOperation,
            StorageRecordDescriptor,
            StorageRecordType,
        )
        from umh.storage.policy import build_default_storage_policy, evaluate_storage_operation

        d = StorageRecordDescriptor(
            record_id="prom_inv", record_type=StorageRecordType.MEMORY_CANDIDATE
        )
        result = evaluate_storage_operation(
            d, StorageOperation.PROMOTE, build_default_storage_policy()
        )
        self.assertFalse(result.allowed)


class TestInvariantMemoryRecordNeverAutoPromoted(unittest.TestCase):
    """INV-528: MemoryRecord created from candidate starts as NEEDS_REVIEW."""

    def test_never_promoted_status(self):
        from umh.memory.discipline import MemoryStatus, create_memory_record_from_candidate

        @dataclass
        class Fake:
            candidate_id: str = "inv_c"
            content: str = "test"
            confidence: float = 0.8
            evidence: list[str] = field(default_factory=lambda: ["e"])
            memory_type: str = "episodic"
            user_id: str = "u1"
            session_id: str = ""
            reason: str = ""
            source: str = ""

        record = create_memory_record_from_candidate(Fake())
        self.assertEqual(record.status, MemoryStatus.NEEDS_REVIEW)
        self.assertNotEqual(record.status, MemoryStatus.PROMOTED)


if __name__ == "__main__":
    unittest.main()
