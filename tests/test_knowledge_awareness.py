"""Tests for Campaign 6.4 — Knowledge Awareness Runtime."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

import pytest

from substrate.organism.knowledge_awareness_runtime import (
    KnowledgeAwarenessRuntime,
    KnowledgeEntry,
    KnowledgeSnapshot,
    KnowledgeType,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def runtime():
    return KnowledgeAwarenessRuntime()


@pytest.fixture
def rich_content():
    return """# Architecture

## Decision: Use Clerk for identity

We decided to use Clerk as the identity provider for all projections.

## Constraint: Multi-tenant isolation

The system must enforce tenant isolation at every layer.

## Convention: deterministic-first

All classification and routing must be deterministic before AI enhancement.

## Lesson: never hardcode device names

Hardcoded device names caused drift across 6+ labels in the cockpit UI.

## Rule: dependency direction is one-way

substrate never imports from transports, adapters, or services.
"""


# ── KnowledgeType Tests ──────────────────────────────────────────────────


class TestKnowledgeType:
    def test_enum_values(self):
        assert KnowledgeType.DECISION.value == "decision"
        assert KnowledgeType.CONSTRAINT.value == "constraint"
        assert KnowledgeType.CONVENTION.value == "convention"
        assert KnowledgeType.LESSON_LEARNED.value == "lesson_learned"
        assert KnowledgeType.ARCHITECTURE_RULE.value == "architecture_rule"

    def test_is_str_enum(self):
        assert isinstance(KnowledgeType.DECISION, str)


# ── KnowledgeEntry Tests ─────────────────────────────────────────────────


class TestKnowledgeEntry:
    def test_to_dict(self):
        entry = KnowledgeEntry(
            knowledge_id="kn-123",
            knowledge_type="decision",
            summary="Use Clerk",
            entity_refs=["proj-creatoros"],
        )
        d = entry.to_dict()
        assert d["knowledge_id"] == "kn-123"
        assert d["knowledge_type"] == "decision"
        assert d["entity_refs"] == ["proj-creatoros"]

    def test_defaults(self):
        entry = KnowledgeEntry(knowledge_id="x", knowledge_type="decision", summary="test")
        assert entry.entity_refs == []
        assert entry.confidence == 0.8

    def test_default_factory_isolation(self):
        e1 = KnowledgeEntry(knowledge_id="a", knowledge_type="decision", summary="a")
        e2 = KnowledgeEntry(knowledge_id="b", knowledge_type="decision", summary="b")
        e1.entity_refs.append("proj-x")
        assert "proj-x" not in e2.entity_refs


# ── KnowledgeSnapshot Tests ──────────────────────────────────────────────


class TestKnowledgeSnapshot:
    def test_to_dict(self):
        snap = KnowledgeSnapshot(
            total=3,
            by_type={"decision": 2, "constraint": 1},
            recent=[KnowledgeEntry(knowledge_id="kn-1", knowledge_type="decision", summary="x")],
            detected_at=1000.0,
        )
        d = snap.to_dict()
        assert d["total"] == 3
        assert len(d["recent"]) == 1

    def test_defaults(self):
        snap = KnowledgeSnapshot(total=0)
        assert snap.by_type == {}
        assert snap.recent == []


# ── Extraction Tests ─────────────────────────────────────────────────────


class TestExtraction:
    def test_extracts_decisions(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        decisions = [e for e in entries if e.knowledge_type == "decision"]
        assert len(decisions) >= 1
        assert any("clerk" in d.summary.lower() for d in decisions)

    def test_extracts_constraints(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        constraints = [e for e in entries if e.knowledge_type == "constraint"]
        assert len(constraints) >= 1

    def test_extracts_conventions(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        conventions = [e for e in entries if e.knowledge_type == "convention"]
        assert len(conventions) >= 1

    def test_extracts_lessons(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        lessons = [e for e in entries if e.knowledge_type == "lesson_learned"]
        assert len(lessons) >= 1

    def test_extracts_rules(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        rules = [e for e in entries if e.knowledge_type == "architecture_rule"]
        assert len(rules) >= 1

    def test_empty_content(self, runtime):
        entries = runtime.extract_from_content("")
        assert entries == []

    def test_no_markers(self, runtime):
        entries = runtime.extract_from_content("# Just a heading\n\nSome regular text.")
        assert entries == []

    def test_short_summaries_skipped(self, runtime):
        entries = runtime.extract_from_content("Decision: ab")
        assert entries == []

    def test_stores_entries(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        assert len(runtime.list_entries()) >= 5

    def test_source_id_preserved(self, runtime):
        entries = runtime.extract_from_content(
            "## Decision: Use Clerk for auth",
            source_id="art-123",
        )
        if entries:
            assert entries[0].source_artifact_id == "art-123"

    def test_entity_refs_preserved(self, runtime):
        entries = runtime.extract_from_content(
            "## Decision: Use Clerk for auth",
            entity_refs=["proj-creatoros"],
        )
        if entries:
            assert "proj-creatoros" in entries[0].entity_refs

    def test_deterministic_ids(self, runtime):
        entries1 = runtime.extract_from_content("## Decision: Use Clerk for auth")
        runtime._entries.clear()
        entries2 = runtime.extract_from_content("## Decision: Use Clerk for auth")
        if entries1 and entries2:
            assert entries1[0].knowledge_id == entries2[0].knowledge_id


# ── Query Tests ───────────────────────────────────────────────────────────


class TestQueries:
    def test_find_decisions(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        decisions = runtime.find_decisions()
        assert all(d.knowledge_type == "decision" for d in decisions)

    def test_find_constraints(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        constraints = runtime.find_constraints()
        assert all(c.knowledge_type == "constraint" for c in constraints)

    def test_find_conventions(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        conventions = runtime.find_conventions()
        assert all(c.knowledge_type == "convention" for c in conventions)

    def test_find_lessons(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        lessons = runtime.find_lessons()
        assert all(l.knowledge_type == "lesson_learned" for l in lessons)

    def test_find_rules(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        rules = runtime.find_rules()
        assert all(r.knowledge_type == "architecture_rule" for r in rules)

    def test_find_for_entity(self, runtime):
        runtime.extract_from_content(
            "## Decision: Use Clerk\n\nDetails here.",
            entity_refs=["proj-creatoros"],
        )
        found = runtime.find_for_entity("proj-creatoros")
        assert len(found) >= 1

    def test_find_for_entity_no_match(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        assert runtime.find_for_entity("proj-nonexistent") == []

    def test_list_entries_all(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        all_entries = runtime.list_entries()
        assert len(all_entries) >= 5

    def test_list_entries_filter_type(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        decisions = runtime.list_entries(knowledge_type="decision")
        assert all(e.knowledge_type == "decision" for e in decisions)

    def test_list_entries_filter_entity(self, runtime):
        runtime.extract_from_content(
            "## Decision: Use Clerk",
            entity_refs=["proj-x"],
        )
        runtime.extract_from_content(
            "## Constraint: Multi-tenant",
            entity_refs=["proj-y"],
        )
        found = runtime.list_entries(entity_id="proj-x")
        assert all("proj-x" in e.entity_refs for e in found)

    def test_get(self, runtime, rich_content):
        entries = runtime.extract_from_content(rich_content)
        if entries:
            found = runtime.get(entries[0].knowledge_id)
            assert found is not None
            assert found.knowledge_id == entries[0].knowledge_id

    def test_get_missing(self, runtime):
        assert runtime.get("nonexistent") is None


# ── Scan Tests ────────────────────────────────────────────────────────────


class TestScan:
    def test_scan_empty(self, runtime):
        snap = runtime.scan_knowledge()
        assert snap.total == 0

    def test_scan_after_extraction(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        snap = runtime.scan_knowledge()
        assert snap.total >= 5
        assert snap.detected_at > 0

    def test_scan_by_type_counts(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        snap = runtime.scan_knowledge()
        assert "decision" in snap.by_type
        assert "constraint" in snap.by_type

    def test_scan_recent_limited(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        snap = runtime.scan_knowledge()
        assert len(snap.recent) <= 20

    def test_snapshot_returns_dict(self, runtime, rich_content):
        runtime.extract_from_content(rich_content)
        s = runtime.snapshot()
        assert isinstance(s, dict)
        assert "total" in s


# ── ID Generation Tests ──────────────────────────────────────────────────


class TestIdGeneration:
    def test_deterministic(self):
        id1 = KnowledgeAwarenessRuntime._generate_id("decision", "Use Clerk")
        id2 = KnowledgeAwarenessRuntime._generate_id("decision", "Use Clerk")
        assert id1 == id2

    def test_different_for_different_inputs(self):
        id1 = KnowledgeAwarenessRuntime._generate_id("decision", "Use Clerk")
        id2 = KnowledgeAwarenessRuntime._generate_id("constraint", "Multi-tenant")
        assert id1 != id2

    def test_starts_with_kn(self):
        kid = KnowledgeAwarenessRuntime._generate_id("decision", "Test")
        assert kid.startswith("kn-")
