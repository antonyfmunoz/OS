"""Phase 20 — Reality Intelligence tests.

Tests the read-only retrieval and explanation layer: query contract types,
intelligence engine, operator integration, provenance guarantee, and
read-only guarantee.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

import pytest

from substrate.reality_model.reality_query import (
    RealityEvidence,
    RealityQuery,
    RealityQueryResult,
    RealityQueryType,
)
from substrate.reality_model.reality_intelligence import RealityIntelligenceEngine


# ── Lightweight mocks ────────────────────────────────────────────────────


class _MockObservation:
    def __init__(
        self,
        content: str,
        domain: str = "general",
        confidence: float = 0.8,
        tags: list[str] | None = None,
        observed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = uuid4()
        self.content = content
        self.domain = domain
        self.confidence = confidence
        self.tags = tags or []
        self.observed_at = observed_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}

    def effective_confidence(self, now: datetime | None = None) -> float:
        return self.confidence


class _MockPattern:
    def __init__(
        self,
        name: str,
        domain: str,
        description: str,
        confidence: float = 0.9,
        evidence_count: int = 3,
        promoted_at: datetime | None = None,
        last_confirmed: datetime | None = None,
    ) -> None:
        self.id = uuid4()
        self.name = name
        self.domain = domain
        self.description = description
        self.confidence = confidence
        self.evidence_count = evidence_count
        self.promoted_at = promoted_at or datetime.now(timezone.utc)
        self.last_confirmed = last_confirmed or datetime.now(timezone.utc)

    def effective_confidence(self, now: datetime | None = None) -> float:
        return self.confidence


class _MockInstanceModel:
    def __init__(self, observations: list[_MockObservation] | None = None) -> None:
        self._observations = observations or []

    def query(self, text: str, limit: int = 10) -> list[_MockObservation]:
        text_lower = text.lower()
        matches = [o for o in self._observations if text_lower in o.content.lower()]
        return matches[:limit]

    def recent(self, limit: int = 20) -> list[_MockObservation]:
        return self._observations[-limit:]

    def list_by_domain(self, domain: str) -> list[_MockObservation]:
        return [o for o in self._observations if o.domain == domain]

    def all(self) -> list[_MockObservation]:
        return list(self._observations)

    def count(self) -> int:
        return len(self._observations)


class _MockCanonicalModel:
    def __init__(
        self,
        patterns: list[_MockPattern] | None = None,
        relationships: list[tuple[str, str, float]] | None = None,
    ) -> None:
        self._patterns = patterns or []
        self._relationships = relationships or []

    def search(self, query: str, limit: int = 10) -> list[_MockPattern]:
        q = query.lower()
        return [p for p in self._patterns if q in p.description.lower() or q in p.name.lower()][:limit]

    def list_by_domain(self, domain: str) -> list[_MockPattern]:
        return [p for p in self._patterns if p.domain == domain]

    def all(self) -> list[_MockPattern]:
        return list(self._patterns)

    def get_related(self, name: str) -> list[tuple[str, str, float]]:
        return [(t, r, s) for t, r, s in self._relationships if name == t.split("->")[0] or True]

    def get_by_name(self, name: str) -> _MockPattern | None:
        for p in self._patterns:
            if p.name == name:
                return p
        return None


@dataclass(frozen=True)
class _MockEvent:
    domain: Any
    event_type: str
    source: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    correlation_id: str | None = None


class _MockEventDomain:
    GOVERNANCE = "governance"
    EXECUTION = "execution"
    MEMORY = "memory"
    OPERATOR = "operator"

    def __init__(self, value: str) -> None:
        self.value = value


class _MockEventSpine:
    def __init__(self, events: list[_MockEvent] | None = None) -> None:
        self._events = events or []

    def replay(
        self,
        domains: set[Any] | None = None,
        since: float | None = None,
    ) -> list[_MockEvent]:
        result = []
        for event in self._events:
            if since is not None and event.timestamp <= since:
                continue
            if domains is not None:
                event_domain_val = event.domain.value if hasattr(event.domain, "value") else str(event.domain)
                domain_vals = set()
                for d in domains:
                    domain_vals.add(d.value if hasattr(d, "value") else str(d))
                if event_domain_val not in domain_vals:
                    continue
            result.append(event)
        return result

    def recent(self, limit: int = 50) -> list[_MockEvent]:
        return self._events[-limit:]


class _MockMemoryStore:
    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self._entries = entries or []

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q = query.lower()
        results = [e for e in self._entries if q in e.get("content", "").lower()]
        return results[:limit]

    def query_by_type(self, memory_type: str) -> list[dict[str, Any]]:
        return [e for e in self._entries if e.get("memory_type") == memory_type]


# ── Contract tests ───────────────────────────────────────────────────────


class TestRealityQueryContract:
    def test_query_type_values(self) -> None:
        assert RealityQueryType.WHY.value == "why"
        assert RealityQueryType.WHAT_CHANGED.value == "what_changed"
        assert RealityQueryType.EVIDENCE.value == "evidence"
        assert RealityQueryType.CONTRADICTIONS.value == "contradictions"
        assert RealityQueryType.LINEAGE.value == "lineage"
        assert RealityQueryType.DOMAIN_SUMMARY.value == "domain_summary"
        assert RealityQueryType.PRIORITIES.value == "priorities"
        assert len(RealityQueryType) == 7

    def test_query_defaults(self) -> None:
        q = RealityQuery(query_id="test-1", query_type=RealityQueryType.WHY)
        assert q.text == ""
        assert q.domain == ""
        assert q.entity == ""
        assert q.since_timestamp is None
        assert q.min_confidence == 0.0
        assert q.limit == 20

    def test_evidence_shape(self) -> None:
        e = RealityEvidence(
            source_type="instance_observation",
            source_id="obs-123",
            content="test content",
            confidence=0.85,
            domain="testing",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        assert e.source_id == "obs-123"
        assert e.metadata == {}

    def test_result_defaults(self) -> None:
        r = RealityQueryResult(query_id="rq-test", query_type="why")
        assert r.evidence == []
        assert r.confidence == 0.0
        assert r.reasoning == ""
        assert r.generated_at > 0
        assert r.sources_queried == []


# ── WHY query tests ──────────────────────────────────────────────────────


class TestWhyQuery:
    def _engine_with_obs(self, observations: list[_MockObservation]) -> RealityIntelligenceEngine:
        return RealityIntelligenceEngine(
            instance_model=_MockInstanceModel(observations),
        )

    def test_why_returns_matching_observations(self) -> None:
        obs = [
            _MockObservation("API latency is high", domain="infrastructure", confidence=0.9),
            _MockObservation("Database is healthy", domain="infrastructure", confidence=0.8),
        ]
        engine = self._engine_with_obs(obs)
        result = engine.why("API latency")
        assert len(result.evidence) == 1
        assert result.evidence[0].content == "API latency is high"
        assert result.evidence[0].source_type == "instance_observation"

    def test_why_includes_canonical_patterns(self) -> None:
        obs = [_MockObservation("deployment failed", domain="infrastructure", confidence=0.7)]
        patterns = [_MockPattern("deploy-gate", "infrastructure", "deployment requires approval", confidence=0.95)]
        engine = RealityIntelligenceEngine(
            instance_model=_MockInstanceModel(obs),
            canonical_model=_MockCanonicalModel(patterns),
        )
        result = engine.why("deployment")
        source_types = {e.source_type for e in result.evidence}
        assert "instance_observation" in source_types
        assert "canonical_pattern" in source_types

    def test_why_confidence_ordering(self) -> None:
        obs = [
            _MockObservation("low conf item", confidence=0.3),
            _MockObservation("high conf item", confidence=0.9),
            _MockObservation("mid conf item", confidence=0.6),
        ]
        engine = self._engine_with_obs(obs)
        result = engine.why("conf item")
        assert len(result.evidence) == 3
        confidences = [e.confidence for e in result.evidence]
        assert confidences == sorted(confidences, reverse=True)


# ── Contradiction detection ──────────────────────────────────────────────


class TestContradictionDetection:
    def test_detect_negation_pair(self) -> None:
        obs = [
            _MockObservation("service confirmed working", domain="infra", confidence=0.8),
            _MockObservation("service failed completely", domain="infra", confidence=0.8),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.find_contradictions(domain="infra")
        assert len(result.evidence) == 2
        assert result.evidence[0].metadata.get("contradicts")

    def test_no_contradiction_same_polarity(self) -> None:
        obs = [
            _MockObservation("service confirmed working", domain="infra", confidence=0.8),
            _MockObservation("service approved for production", domain="infra", confidence=0.9),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.find_contradictions(domain="infra")
        assert len(result.evidence) == 0

    def test_cross_domain_not_contradicted(self) -> None:
        obs = [
            _MockObservation("service confirmed", domain="infra", confidence=0.8),
            _MockObservation("service denied", domain="security", confidence=0.9),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.find_contradictions()
        assert len(result.evidence) == 0


# ── WHAT_CHANGED tests ───────────────────────────────────────────────────


class TestWhatChanged:
    def test_filters_by_timestamp(self) -> None:
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        new_time = datetime.now(timezone.utc) - timedelta(hours=1)
        obs = [
            _MockObservation("old event", observed_at=old_time, confidence=0.7),
            _MockObservation("new event", observed_at=new_time, confidence=0.8),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).timestamp()
        result = engine.what_changed(since=since)
        assert len(result.evidence) == 1
        assert result.evidence[0].content == "new event"

    def test_includes_events_since_timestamp(self) -> None:
        now = time.time()
        events = [
            _MockEvent(
                domain=_MockEventDomain("operator"),
                event_type="intent_routed",
                source="test",
                data={"action": "classified"},
                timestamp=now - 3600,
            ),
            _MockEvent(
                domain=_MockEventDomain("operator"),
                event_type="intent_routed",
                source="test",
                data={"action": "recent"},
                timestamp=now - 60,
            ),
        ]
        engine = RealityIntelligenceEngine(event_spine=_MockEventSpine(events))
        result = engine.what_changed(since=now - 300)
        assert len(result.evidence) == 1

    def test_empty_since_returns_all(self) -> None:
        obs = [
            _MockObservation("event a", confidence=0.7),
            _MockObservation("event b", confidence=0.8),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.what_changed(since=0.0)
        assert len(result.evidence) == 2


# ── LINEAGE trace tests ─────────────────────────────────────────────────


class TestLineageTrace:
    def test_traces_observation_to_event(self) -> None:
        obs = [_MockObservation("CPU throttle detected", domain="infrastructure", confidence=0.9)]
        events = [
            _MockEvent(
                domain=_MockEventDomain("governance"),
                event_type="risk_classified",
                source="governance.engine",
                data={"entity": "CPU throttle", "risk": "high"},
            ),
        ]
        engine = RealityIntelligenceEngine(
            instance_model=_MockInstanceModel(obs),
            event_spine=_MockEventSpine(events),
        )
        result = engine.trace_lineage("CPU throttle")
        source_types = {e.source_type for e in result.evidence}
        assert "instance_observation" in source_types
        assert "event" in source_types

    def test_lineage_chronological_order(self) -> None:
        old_time = datetime.now(timezone.utc) - timedelta(hours=10)
        new_time = datetime.now(timezone.utc) - timedelta(hours=1)
        obs = [
            _MockObservation("deploy failed", observed_at=new_time, confidence=0.8),
            _MockObservation("deploy started", observed_at=old_time, confidence=0.7),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.trace_lineage("deploy")
        timestamps = [e.timestamp for e in result.evidence]
        assert timestamps == sorted(timestamps)

    def test_lineage_empty_entity(self) -> None:
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel([]))
        result = engine.trace_lineage("nonexistent")
        assert len(result.evidence) == 0
        assert result.confidence == 0.0


# ── Priority ranking tests ──────────────────────────────────────────────


class TestPriorityRanking:
    def test_ranks_by_activity(self) -> None:
        obs = (
            [_MockObservation(f"infra issue {i}", domain="infrastructure", confidence=0.8) for i in range(10)]
            + [_MockObservation("marketing note", domain="marketing", confidence=0.5)]
        )
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.identify_priorities(limit=5)
        assert len(result.evidence) >= 1
        assert result.evidence[0].domain == "infrastructure"

    def test_empty_returns_no_priorities(self) -> None:
        engine = RealityIntelligenceEngine()
        result = engine.identify_priorities()
        assert len(result.evidence) == 0
        assert "No domains" in result.reasoning


# ── Domain summary tests ────────────────────────────────────────────────


class TestDomainSummary:
    def test_summarizes_by_domain(self) -> None:
        obs = [
            _MockObservation("infra item 1", domain="infrastructure", confidence=0.8),
            _MockObservation("infra item 2", domain="infrastructure", confidence=0.7),
            _MockObservation("other item", domain="marketing", confidence=0.5),
        ]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.summarize_domain("infrastructure")
        assert len(result.evidence) == 2
        assert all(e.domain == "infrastructure" for e in result.evidence)

    def test_summary_includes_canonical(self) -> None:
        patterns = [_MockPattern("infra-pattern", "infrastructure", "infra baseline", confidence=0.95)]
        engine = RealityIntelligenceEngine(canonical_model=_MockCanonicalModel(patterns))
        result = engine.summarize_domain("infrastructure")
        assert len(result.evidence) == 1
        assert result.evidence[0].source_type == "canonical_pattern"


# ── Provenance guarantee ────────────────────────────────────────────────


class TestProvenanceRequired:
    def test_all_evidence_has_source_id(self) -> None:
        obs = [
            _MockObservation("test obs", domain="testing", confidence=0.8),
        ]
        patterns = [_MockPattern("test-pat", "testing", "test pattern", confidence=0.9)]
        memory_entries = [
            {"memory_id": "mem-001", "content": "test memory", "confidence": 0.7},
        ]
        events = [
            _MockEvent(
                domain=_MockEventDomain("operator"),
                event_type="test_event",
                source="test",
                data={"key": "value"},
            ),
        ]
        engine = RealityIntelligenceEngine(
            instance_model=_MockInstanceModel(obs),
            canonical_model=_MockCanonicalModel(patterns),
            memory_store=_MockMemoryStore(memory_entries),
            event_spine=_MockEventSpine(events),
        )

        for qt in [
            RealityQueryType.WHY,
            RealityQueryType.EVIDENCE,
            RealityQueryType.WHAT_CHANGED,
        ]:
            result = engine.query(RealityQuery(
                query_id="prov-test",
                query_type=qt,
                text="test",
                entity="test",
            ))
            for ev in result.evidence:
                assert ev.source_id, f"Empty source_id in {qt.value} query: {ev}"

    def test_memory_without_id_excluded(self) -> None:
        entries = [
            {"content": "no id memory", "confidence": 0.7},
            {"memory_id": "mem-002", "content": "has id", "confidence": 0.8},
        ]
        engine = RealityIntelligenceEngine(memory_store=_MockMemoryStore(entries))
        result = engine.why("memory")
        for ev in result.evidence:
            assert ev.source_id != ""

    def test_priority_evidence_has_source_id(self) -> None:
        obs = [_MockObservation("test", domain="infra", confidence=0.8)]
        engine = RealityIntelligenceEngine(instance_model=_MockInstanceModel(obs))
        result = engine.identify_priorities()
        for ev in result.evidence:
            assert ev.source_id.startswith("priority-")


# ── Read-only guarantee ─────────────────────────────────────────────────


class TestReadOnlyGuarantee:
    def test_no_write_methods(self) -> None:
        engine = RealityIntelligenceEngine()
        write_patterns = [
            "write", "create", "update", "delete", "remove", "add",
            "insert", "dispatch", "execute", "run", "mutate", "emit",
        ]
        public_methods = [m for m in dir(engine) if not m.startswith("_")]
        for method in public_methods:
            for pattern in write_patterns:
                assert not method.lower().startswith(pattern), (
                    f"Engine has write-like method: {method}"
                )

    def test_query_doesnt_change_counts(self) -> None:
        obs = [
            _MockObservation("test observation", domain="testing", confidence=0.8),
        ]
        instance = _MockInstanceModel(obs)
        engine = RealityIntelligenceEngine(instance_model=instance)
        count_before = instance.count()
        engine.why("test")
        engine.find_evidence("test")
        engine.what_changed(since=0.0)
        engine.find_contradictions()
        engine.identify_priorities()
        assert instance.count() == count_before

    def test_no_execute_or_dispatch(self) -> None:
        engine = RealityIntelligenceEngine()
        assert not hasattr(engine, "execute")
        assert not hasattr(engine, "dispatch")
        assert not hasattr(engine, "run")
        assert not hasattr(engine, "emit")

    def test_engine_does_not_import_governance(self) -> None:
        import substrate.reality_model.reality_intelligence as mod
        source = open(mod.__file__).read()
        assert "GovernanceEngine" not in source
        assert "WorkPacket" not in source


# ── Graceful degradation ────────────────────────────────────────────────


class TestGracefulDegradation:
    def test_all_none_sources(self) -> None:
        engine = RealityIntelligenceEngine()
        result = engine.why("anything")
        assert result.evidence == []
        assert result.confidence == 0.0
        assert result.query_type == "why"

    def test_partial_sources(self) -> None:
        obs = [_MockObservation("partial test", domain="testing", confidence=0.7)]
        engine = RealityIntelligenceEngine(
            instance_model=_MockInstanceModel(obs),
            canonical_model=None,
            memory_store=None,
            event_spine=None,
        )
        result = engine.why("partial")
        assert len(result.evidence) == 1
        assert "instance" in result.sources_queried


# ── IntentRouter patterns ────────────────────────────────────────────────


class TestIntentRouterRealityPatterns:
    @pytest.fixture(autouse=True)
    def _load_router(self) -> None:
        from substrate.operator.intent_router import IntentRouter
        self.router = IntentRouter()

    def test_why_routes_observation(self) -> None:
        c = self.router.classify("why did the deployment fail")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9

    def test_what_changed_routes_observation(self) -> None:
        c = self.router.classify("what changed in the last 24 hours")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9

    def test_evidence_routes_observation(self) -> None:
        c = self.router.classify("find evidence for the claim about latency")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9

    def test_lineage_routes_observation(self) -> None:
        c = self.router.classify("trace the lineage of the auth decision")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9

    def test_priorities_routes_observation(self) -> None:
        c = self.router.classify("what are the priorities right now")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9

    def test_contradictions_routes_observation(self) -> None:
        c = self.router.classify("contradictions in infrastructure domain")
        assert c.route_type.value == "observation"
        assert c.confidence >= 0.9


# ── Operator E2E ─────────────────────────────────────────────────────────


class TestOperatorRealityE2E:
    def test_query_reality_method_exists(self) -> None:
        from substrate import Substrate
        s = Substrate()
        assert hasattr(s, "query_reality")
        assert callable(s.query_reality)

    @pytest.mark.asyncio
    async def test_query_reality_returns_dict(self) -> None:
        from substrate import Substrate
        s = Substrate()
        result = await s.query_reality("test query", query_type="why")
        assert isinstance(result, dict)
        assert "query_id" in result
        assert "evidence" in result
        assert "confidence" in result
        assert "sources_queried" in result


# ── No new authority ─────────────────────────────────────────────────────


class TestNoNewAuthority:
    def test_engine_has_no_execute(self) -> None:
        engine = RealityIntelligenceEngine()
        for attr in dir(engine):
            if attr.startswith("_"):
                continue
            assert "execute" not in attr.lower(), f"execute-like method: {attr}"
            assert "dispatch" not in attr.lower(), f"dispatch-like method: {attr}"

    def test_engine_has_no_run(self) -> None:
        engine = RealityIntelligenceEngine()
        public = [a for a in dir(engine) if not a.startswith("_")]
        assert "run" not in public
        assert "start" not in public
