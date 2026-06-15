"""Reality Intelligence Engine — read-only retrieval and explanation.

Queries InstanceRealityModel, CanonicalRealityModel, CanonicalMemoryStore,
and EventSpine to produce evidence-based, provenance-traced answers.

MUST NOT write to any system, create work packets, invoke governance,
or execute work. All logic is deterministic (regex/scoring/filtering).
Every returned RealityEvidence carries a non-empty source_id.

Phase 20. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from substrate.reality_model.reality_query import (
    RealityEvidence,
    RealityQuery,
    RealityQueryResult,
    RealityQueryType,
)

logger = logging.getLogger(__name__)

_NEGATION_KEYWORDS = frozenset({
    "not", "never", "no longer", "stopped", "failed",
    "rejected", "denied", "removed", "broken", "disabled",
})

_AFFIRMATION_KEYWORDS = frozenset({
    "always", "confirmed", "approved", "succeeded", "started",
    "accepted", "enabled", "working", "active", "completed",
})

_NEGATION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _NEGATION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_AFFIRMATION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _AFFIRMATION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


class RealityIntelligenceEngine:
    """Read-only intelligence layer over recorded reality.

    Queries four data sources via their public read APIs. Never accesses
    internal state. Gracefully degrades when sources are None.
    """

    def __init__(
        self,
        instance_model: Any | None = None,
        canonical_model: Any | None = None,
        memory_store: Any | None = None,
        event_spine: Any | None = None,
    ) -> None:
        self._instance = instance_model
        self._canonical = canonical_model
        self._memory = memory_store
        self._events = event_spine

    def query(self, rq: RealityQuery) -> RealityQueryResult:
        dispatch = {
            RealityQueryType.WHY: lambda: self.why(
                rq.entity or rq.text, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.WHAT_CHANGED: lambda: self.what_changed(
                rq.since_timestamp or 0.0, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.EVIDENCE: lambda: self.find_evidence(
                rq.entity or rq.text, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.CONTRADICTIONS: lambda: self.find_contradictions(
                rq.domain, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.LINEAGE: lambda: self.trace_lineage(
                rq.entity or rq.text, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.DOMAIN_SUMMARY: lambda: self.summarize_domain(
                rq.domain, rq.limit, rq.min_confidence,
            ),
            RealityQueryType.PRIORITIES: lambda: self.identify_priorities(
                rq.limit, rq.min_confidence,
            ),
        }
        handler = dispatch.get(rq.query_type)
        if handler is None:
            return RealityQueryResult(
                query_id=rq.query_id,
                query_type=rq.query_type.value,
                reasoning=f"Unknown query type: {rq.query_type}",
            )
        result = handler()
        result.query_id = rq.query_id
        return result

    # ── Public query methods ──────────────────────────────────────────────

    def why(
        self,
        entity: str,
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        sources: list[str] = []
        evidence: list[RealityEvidence] = []

        evidence.extend(self._search_instance(entity, limit, min_confidence))
        if evidence:
            sources.append("instance")

        canonical_ev = self._search_canonical(entity, limit, min_confidence)
        evidence.extend(canonical_ev)
        if canonical_ev:
            sources.append("canonical")

        memory_ev = self._search_memory(entity, limit)
        evidence.extend(memory_ev)
        if memory_ev:
            sources.append("memory")

        event_ev = self._search_events(entity, since=None, domains=None)
        evidence.extend(event_ev)
        if event_ev:
            sources.append("events")

        evidence = self._filter_min_confidence(evidence, min_confidence)
        evidence.sort(key=lambda e: e.confidence, reverse=True)
        evidence = evidence[:limit]

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.WHY.value,
            evidence=evidence,
            confidence=self._aggregate_confidence(evidence),
            reasoning=self._why_reasoning(entity, evidence, sources),
            sources_queried=sources,
        )

    def what_changed(
        self,
        since: float,
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        sources: list[str] = []
        evidence: list[RealityEvidence] = []

        if self._instance is not None:
            now = datetime.now(timezone.utc)
            since_dt = datetime.fromtimestamp(since, tz=timezone.utc) if since > 0 else None
            for obs in self._instance.recent(limit=200):
                if since_dt and obs.observed_at < since_dt:
                    continue
                ev = self._obs_to_evidence(obs, now)
                evidence.append(ev)
            if evidence:
                sources.append("instance")

        if self._canonical is not None:
            since_dt = datetime.fromtimestamp(since, tz=timezone.utc) if since > 0 else None
            for pat in self._canonical.all():
                if since_dt and pat.last_confirmed < since_dt:
                    continue
                ev = self._pattern_to_evidence(pat)
                evidence.append(ev)
            if "canonical" not in sources and any(
                e.source_type == "canonical_pattern" for e in evidence
            ):
                sources.append("canonical")

        event_ev = self._search_events("", since=since, domains=None)
        evidence.extend(event_ev)
        if event_ev:
            sources.append("events")

        evidence = self._filter_min_confidence(evidence, min_confidence)
        evidence.sort(key=lambda e: e.timestamp, reverse=True)
        evidence = evidence[:limit]

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.WHAT_CHANGED.value,
            evidence=evidence,
            confidence=self._aggregate_confidence(evidence),
            reasoning=f"Found {len(evidence)} changes since {datetime.fromtimestamp(since, tz=timezone.utc).isoformat() if since > 0 else 'epoch'} across {', '.join(sources) or 'no sources'}",
            sources_queried=sources,
        )

    def find_evidence(
        self,
        entity: str,
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        sources: list[str] = []
        evidence: list[RealityEvidence] = []

        evidence.extend(self._search_instance(entity, limit, min_confidence))
        if evidence:
            sources.append("instance")

        canonical_ev = self._search_canonical(entity, limit, min_confidence)
        evidence.extend(canonical_ev)
        if canonical_ev:
            sources.append("canonical")

        if self._canonical is not None:
            for ev_item in canonical_ev:
                related = self._canonical.get_related(ev_item.metadata.get("name", ""))
                for rel_name, rel_type, strength in related:
                    pattern = self._canonical.get_by_name(rel_name)
                    if pattern:
                        rel_ev = self._pattern_to_evidence(pattern)
                        rel_ev.metadata["relationship_type"] = rel_type
                        rel_ev.metadata["relationship_strength"] = strength
                        evidence.append(rel_ev)

        memory_ev = self._search_memory(entity, limit)
        evidence.extend(memory_ev)
        if memory_ev:
            sources.append("memory")

        event_ev = self._search_events(entity, since=None, domains=None)
        evidence.extend(event_ev)
        if event_ev:
            sources.append("events")

        evidence = self._filter_min_confidence(evidence, min_confidence)
        evidence.sort(key=lambda e: e.confidence, reverse=True)
        evidence = evidence[:limit]

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.EVIDENCE.value,
            evidence=evidence,
            confidence=self._aggregate_confidence(evidence),
            reasoning=f"Found {len(evidence)} evidence items for '{entity}' across {', '.join(sources) or 'no sources'}",
            sources_queried=sources,
        )

    def find_contradictions(
        self,
        domain: str = "",
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        if self._instance is None:
            return RealityQueryResult(
                query_id="",
                query_type=RealityQueryType.CONTRADICTIONS.value,
                reasoning="No instance model available",
                sources_queried=[],
            )

        if domain:
            observations = self._instance.list_by_domain(domain)
        else:
            observations = self._instance.all()

        now = datetime.now(timezone.utc)
        observations = [
            obs for obs in observations
            if obs.effective_confidence(now) >= min_confidence
        ]

        cap = min(len(observations), limit * 10)
        observations = observations[-cap:]

        contradictions: list[RealityEvidence] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, obs_a in enumerate(observations):
            if len(contradictions) >= limit * 2:
                break
            for obs_b in observations[i + 1:]:
                if len(contradictions) >= limit * 2:
                    break
                pair_key = (str(obs_a.id), str(obs_b.id))
                if pair_key in seen_pairs:
                    continue
                if self._detect_negation_pair(obs_a, obs_b):
                    seen_pairs.add(pair_key)
                    ev_a = self._obs_to_evidence(obs_a, now)
                    ev_a.metadata["contradicts"] = str(obs_b.id)
                    ev_b = self._obs_to_evidence(obs_b, now)
                    ev_b.metadata["contradicts"] = str(obs_a.id)
                    contradictions.extend([ev_a, ev_b])

        contradictions = contradictions[:limit]

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.CONTRADICTIONS.value,
            evidence=contradictions,
            confidence=self._aggregate_confidence(contradictions),
            reasoning=f"Found {len(contradictions) // 2} contradiction pairs in domain '{domain or 'all'}' from {len(observations)} observations",
            sources_queried=["instance"],
        )

    def trace_lineage(
        self,
        entity: str,
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        sources: list[str] = []
        chain: list[RealityEvidence] = []

        instance_ev = self._search_instance(entity, limit, min_confidence)
        chain.extend(instance_ev)
        if instance_ev:
            sources.append("instance")

        if self._events is not None:
            try:
                from substrate.organism.event_spine import EventDomain
                gov_events = self._events.replay(
                    domains={EventDomain.GOVERNANCE, EventDomain.EXECUTION, EventDomain.MEMORY},
                )
                entity_lower = entity.lower()
                for event in gov_events:
                    data_str = str(event.data).lower()
                    if entity_lower in data_str:
                        ev = self._event_to_evidence(event)
                        chain.append(ev)
                if any(e.source_type == "event" for e in chain):
                    sources.append("events")
            except Exception as exc:
                logger.debug("trace_lineage event query failed: %s", exc)

        if self._canonical is not None:
            canonical_ev = self._search_canonical(entity, limit, min_confidence)
            chain.extend(canonical_ev)
            if canonical_ev:
                sources.append("canonical")
            for ev_item in canonical_ev:
                name = ev_item.metadata.get("name", "")
                if name:
                    for rel_name, rel_type, strength in self._canonical.get_related(name):
                        pattern = self._canonical.get_by_name(rel_name)
                        if pattern:
                            rel_ev = self._pattern_to_evidence(pattern)
                            rel_ev.metadata["lineage_link"] = rel_type
                            chain.append(rel_ev)

        chain = self._filter_min_confidence(chain, min_confidence)
        chain.sort(key=lambda e: e.timestamp)
        chain = chain[:limit]

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.LINEAGE.value,
            evidence=chain,
            confidence=self._aggregate_confidence(chain),
            reasoning=self._lineage_reasoning(entity, chain, sources),
            sources_queried=sources,
        )

    def summarize_domain(
        self,
        domain: str,
        limit: int = 20,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        sources: list[str] = []
        evidence: list[RealityEvidence] = []

        if self._instance is not None:
            now = datetime.now(timezone.utc)
            for obs in self._instance.list_by_domain(domain):
                ev = self._obs_to_evidence(obs, now)
                evidence.append(ev)
            if evidence:
                sources.append("instance")

        if self._canonical is not None:
            for pat in self._canonical.list_by_domain(domain):
                ev = self._pattern_to_evidence(pat)
                evidence.append(ev)
            if any(e.source_type == "canonical_pattern" for e in evidence):
                sources.append("canonical")

        memory_ev = self._search_memory(domain, limit)
        evidence.extend(memory_ev)
        if memory_ev:
            sources.append("memory")

        if self._events is not None:
            try:
                from substrate.organism.event_spine import EventDomain
                domain_map = {d.value: d for d in EventDomain}
                event_domain = domain_map.get(domain)
                if event_domain:
                    events = self._events.replay(domains={event_domain})
                    for event in events[-limit:]:
                        evidence.append(self._event_to_evidence(event))
                    if events:
                        sources.append("events")
            except Exception:
                pass

        evidence = self._filter_min_confidence(evidence, min_confidence)
        evidence.sort(key=lambda e: e.confidence, reverse=True)
        evidence = evidence[:limit]

        obs_count = sum(1 for e in evidence if e.source_type == "instance_observation")
        pat_count = sum(1 for e in evidence if e.source_type == "canonical_pattern")

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.DOMAIN_SUMMARY.value,
            evidence=evidence,
            confidence=self._aggregate_confidence(evidence),
            reasoning=f"Domain '{domain}': {obs_count} observations, {pat_count} patterns, {len(evidence)} total items across {', '.join(sources) or 'no sources'}",
            sources_queried=sources,
        )

    def identify_priorities(
        self,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> RealityQueryResult:
        domains = self._get_all_domains()
        if not domains:
            return RealityQueryResult(
                query_id="",
                query_type=RealityQueryType.PRIORITIES.value,
                reasoning="No domains found across any data source",
                sources_queried=[],
            )

        sources: list[str] = []
        domain_scores: list[tuple[str, float, dict[str, Any]]] = []
        now = datetime.now(timezone.utc)

        for domain in domains:
            obs_count = 0
            decay_total = 0.0
            contradiction_count = 0
            governance_count = 0

            if self._instance is not None:
                obs_list = self._instance.list_by_domain(domain)
                obs_count = len(obs_list)
                for obs in obs_list:
                    eff = obs.effective_confidence(now)
                    if obs.confidence > 0:
                        decay_total += 1.0 - (eff / obs.confidence)
                if "instance" not in sources and obs_count > 0:
                    sources.append("instance")

            if self._events is not None:
                try:
                    from substrate.organism.event_spine import EventDomain as ED
                    gov_events = self._events.replay(domains={ED.GOVERNANCE})
                    for event in gov_events:
                        data_str = str(event.data).lower()
                        if domain.lower() in data_str:
                            governance_count += 1
                    if "events" not in sources and governance_count > 0:
                        sources.append("events")
                except Exception:
                    pass

            decay_ratio = (decay_total / obs_count) if obs_count > 0 else 0.0

            raw_score = (
                (min(obs_count, 50) / 50.0) * 0.3
                + decay_ratio * 0.2
                + (min(contradiction_count, 10) / 10.0) * 0.3
                + (min(governance_count, 10) / 10.0) * 0.2
            )

            domain_scores.append((domain, raw_score, {
                "observation_count": obs_count,
                "decay_ratio": round(decay_ratio, 3),
                "contradiction_count": contradiction_count,
                "governance_activity": governance_count,
            }))

        domain_scores.sort(key=lambda x: x[1], reverse=True)
        domain_scores = domain_scores[:limit]

        max_score = domain_scores[0][1] if domain_scores else 1.0
        if max_score == 0:
            max_score = 1.0

        evidence: list[RealityEvidence] = []
        for domain, raw_score, factors in domain_scores:
            normalized = round(raw_score / max_score, 3)
            evidence.append(RealityEvidence(
                source_type="priority_ranking",
                source_id=f"priority-{domain}",
                content=f"Domain '{domain}' priority score: {normalized}",
                confidence=normalized,
                domain=domain,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=factors,
            ))

        return RealityQueryResult(
            query_id="",
            query_type=RealityQueryType.PRIORITIES.value,
            evidence=evidence,
            confidence=self._aggregate_confidence(evidence),
            reasoning=f"Ranked {len(evidence)} domains by observation volume, confidence decay, contradictions, and governance activity",
            sources_queried=sources,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _search_instance(
        self, text: str, limit: int, min_confidence: float,
    ) -> list[RealityEvidence]:
        if self._instance is None or not text:
            return []
        now = datetime.now(timezone.utc)
        results = self._instance.query(text, limit=limit)
        evidence = [self._obs_to_evidence(obs, now) for obs in results]
        return self._filter_min_confidence(evidence, min_confidence)

    def _search_canonical(
        self, text: str, limit: int, min_confidence: float,
    ) -> list[RealityEvidence]:
        if self._canonical is None or not text:
            return []
        results = self._canonical.search(text, limit=limit)
        evidence = [self._pattern_to_evidence(p) for p in results]
        return self._filter_min_confidence(evidence, min_confidence)

    def _search_memory(self, text: str, limit: int) -> list[RealityEvidence]:
        if self._memory is None or not text:
            return []
        try:
            results = self._memory.search(text, limit=limit)
            evidence: list[RealityEvidence] = []
            for entry in results:
                memory_id = entry.get("memory_id", "")
                if not memory_id:
                    continue
                evidence.append(RealityEvidence(
                    source_type="memory",
                    source_id=memory_id,
                    content=entry.get("content", ""),
                    confidence=float(entry.get("confidence", 0.5)),
                    domain=entry.get("primitive_type", "memory"),
                    timestamp=entry.get("timestamp", ""),
                    metadata={
                        k: v for k, v in entry.items()
                        if k in ("label", "memory_type", "source_document_id")
                    },
                ))
            return evidence
        except Exception as exc:
            logger.debug("memory search failed: %s", exc)
            return []

    def _search_events(
        self,
        text: str,
        since: float | None,
        domains: set[Any] | None,
    ) -> list[RealityEvidence]:
        if self._events is None:
            return []
        try:
            events = self._events.replay(domains=domains, since=since)
            text_lower = text.lower() if text else ""
            evidence: list[RealityEvidence] = []
            for event in events:
                if text_lower:
                    searchable = f"{event.event_type} {event.source} {str(event.data)}".lower()
                    if text_lower not in searchable:
                        continue
                evidence.append(self._event_to_evidence(event))
            return evidence
        except Exception as exc:
            logger.debug("event search failed: %s", exc)
            return []

    def _obs_to_evidence(self, obs: Any, now: datetime | None = None) -> RealityEvidence:
        now = now or datetime.now(timezone.utc)
        return RealityEvidence(
            source_type="instance_observation",
            source_id=str(obs.id),
            content=obs.content,
            confidence=obs.effective_confidence(now),
            domain=obs.domain,
            timestamp=obs.observed_at.isoformat(),
            metadata={k: v for k, v in (obs.metadata or {}).items()},
        )

    def _pattern_to_evidence(self, pattern: Any) -> RealityEvidence:
        return RealityEvidence(
            source_type="canonical_pattern",
            source_id=str(pattern.id),
            content=pattern.description,
            confidence=pattern.effective_confidence(),
            domain=pattern.domain,
            timestamp=pattern.promoted_at.isoformat(),
            metadata={
                "name": pattern.name,
                "evidence_count": pattern.evidence_count,
            },
        )

    def _event_to_evidence(self, event: Any) -> RealityEvidence:
        return RealityEvidence(
            source_type="event",
            source_id=event.event_id,
            content=f"{event.event_type}: {str(event.data)[:500]}",
            confidence=0.9,
            domain=event.domain.value if hasattr(event.domain, "value") else str(event.domain),
            timestamp=datetime.fromtimestamp(event.timestamp, tz=timezone.utc).isoformat(),
            metadata={"source": event.source, "event_type": event.event_type},
        )

    def _detect_negation_pair(self, obs_a: Any, obs_b: Any) -> bool:
        if obs_a.domain != obs_b.domain:
            return False
        a_text = obs_a.content.lower()
        b_text = obs_b.content.lower()
        a_neg = bool(_NEGATION_RE.search(a_text))
        a_aff = bool(_AFFIRMATION_RE.search(a_text))
        b_neg = bool(_NEGATION_RE.search(b_text))
        b_aff = bool(_AFFIRMATION_RE.search(b_text))
        return (a_neg and b_aff) or (a_aff and b_neg)

    def _filter_min_confidence(
        self, evidence: list[RealityEvidence], min_confidence: float,
    ) -> list[RealityEvidence]:
        if min_confidence <= 0.0:
            return evidence
        return [e for e in evidence if e.confidence >= min_confidence]

    def _aggregate_confidence(self, evidence: list[RealityEvidence]) -> float:
        if not evidence:
            return 0.0
        total = sum(e.confidence for e in evidence)
        return round(total / len(evidence), 4)

    def _get_all_domains(self) -> list[str]:
        domains: set[str] = set()
        if self._instance is not None:
            for obs in self._instance.all():
                domains.add(obs.domain)
        if self._canonical is not None:
            for pat in self._canonical.all():
                domains.add(pat.domain)
        return sorted(domains)

    def _why_reasoning(
        self, entity: str, evidence: list[RealityEvidence], sources: list[str],
    ) -> str:
        by_source: dict[str, int] = {}
        for e in evidence:
            by_source[e.source_type] = by_source.get(e.source_type, 0) + 1
        parts = [f"{count} {stype}" for stype, count in sorted(by_source.items())]
        return f"Found {len(evidence)} evidence items for '{entity}' ({', '.join(parts)}) across {', '.join(sources) or 'no sources'}"

    def _lineage_reasoning(
        self, entity: str, chain: list[RealityEvidence], sources: list[str],
    ) -> str:
        by_source: dict[str, int] = {}
        for e in chain:
            by_source[e.source_type] = by_source.get(e.source_type, 0) + 1
        parts = [f"{count} {stype}" for stype, count in sorted(by_source.items())]
        return f"Traced lineage for '{entity}': {len(chain)} links ({', '.join(parts)}) across {', '.join(sources) or 'no sources'}, ordered chronologically"
