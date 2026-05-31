"""Diagnostic Engine — analyze ingested context for canonical truth state.

Compares claims across sources, detects contradictions, outdated claims,
missing context, and generates diagnostic reports with recommendations.
All analysis is deterministic — no LLM calls required.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.organism.source_registry import SourceRegistry
from substrate.organism.ingestion_job import IngestionJobStore, IngestedItem
from substrate.organism.context_diagnostic import (
    ContextDiagnosticReport,
    CanonicalClaim,
    ContextContradiction,
    ContradictionType,
    DiagnosticStatus,
    DiagnosticReportStore,
)
from substrate.organism.canonical_update import (
    CanonicalUpdateProposal,
    ProposalType,
    ProposalStatus,
    ProposalStore,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_ENTITY_KNOWLEDGE_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "entity_knowledge.json"
)


def _load_entity_knowledge() -> dict[str, Any]:
    try:
        with open(_ENTITY_KNOWLEDGE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"known_entities": {}, "expected_products": [], "expected_companies": [], "open_question_rules": []}


def _get_known_entities() -> dict[str, dict[str, str]]:
    return _load_entity_knowledge().get("known_entities", {})


def _get_expected_products() -> set[str]:
    return set(_load_entity_knowledge().get("expected_products", []))


def _get_expected_companies() -> set[str]:
    return set(_load_entity_knowledge().get("expected_companies", []))


class DiagnosticEngine:
    def __init__(
        self,
        registry: SourceRegistry | None = None,
        job_store: IngestionJobStore | None = None,
        report_store: DiagnosticReportStore | None = None,
        proposal_store: ProposalStore | None = None,
    ) -> None:
        self._registry = registry or SourceRegistry()
        self._job_store = job_store or IngestionJobStore()
        self._report_store = report_store or DiagnosticReportStore()
        self._proposal_store = proposal_store or ProposalStore()

    def build_diagnostic_report(self, scope: str = "full") -> ContextDiagnosticReport:
        report = ContextDiagnosticReport(scope=scope, status=DiagnosticStatus.RUNNING.value)
        sources = self._registry.list_sources()
        report.sources_analyzed = [s.source_id for s in sources]
        items = self._job_store.list_items()
        report.item_count = len(items)

        all_claims = self._collect_claims(items)
        report.canonical_claims = [c.to_dict() for c in all_claims if c.canonicality == "canonical"]
        report.competing_claims = [c.to_dict() for c in all_claims if c.canonicality == "competing"]

        outdated = self._detect_outdated_claims(all_claims)
        report.outdated_claims = [c.to_dict() for c in outdated]

        contradictions = self._detect_contradictions(all_claims)
        report.contradictions = [c.to_dict() for c in contradictions]

        report.missing_context = self._detect_missing_context(items)
        report.open_questions = self._detect_open_questions(items)

        entity_map = self._build_entity_map(items)
        report.entity_map = entity_map
        report.product_map = {k: v for k, v in entity_map.items() if v.get("type") in ("product", "projection")}
        report.project_map = {k: v for k, v in entity_map.items() if v.get("type") in ("company", "holding")}

        report.roadmap_implications = self._detect_roadmap_implications(items)
        report.work_packet_implications = self._detect_work_packet_implications(items)
        report.memory_implications = self._detect_memory_implications(items)

        proposals = self._recommend_canonical_updates(all_claims, contradictions, outdated)
        report.recommended_canonical_updates = [p.proposal_id for p in proposals]
        report.recommended_deprecations = [
            p.proposal_id for p in proposals
            if p.proposal_type == ProposalType.DEPRECATE_CLAIM.value
        ]
        report.recommended_work_packets = self._recommend_work_packets(items)
        report.recommended_operator_questions = self._recommend_operator_questions(items, contradictions)

        report.confidence = self._compute_confidence(report)
        report.status = DiagnosticStatus.COMPLETED.value
        self._report_store.save_report(report)
        return report

    def _collect_claims(self, items: list[IngestedItem]) -> list[CanonicalClaim]:
        claims: list[CanonicalClaim] = []
        seen: set[str] = set()
        for item in items:
            for claim_text in item.extracted_claims:
                normalized = claim_text.strip().lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                claim = CanonicalClaim(
                    claim_text=claim_text,
                    domain=self._classify_domain(claim_text),
                    entity_refs=item.extracted_entities,
                    source_ids=[item.source_id],
                    evidence=[item.content_ref],
                    confidence=item.confidence,
                    freshness=item.freshness,
                    canonicality="canonical" if item.freshness in ("fresh", "recent") else "unknown",
                )
                claims.append(claim)
        return claims

    def _detect_contradictions(self, claims: list[CanonicalClaim]) -> list[ContextContradiction]:
        contradictions: list[ContextContradiction] = []
        for i, a in enumerate(claims):
            for b in claims[i + 1:]:
                ctype = self._check_contradiction(a, b)
                if ctype:
                    contradictions.append(ContextContradiction(
                        claim_a=a.claim_text,
                        claim_b=b.claim_text,
                        source_a=a.source_ids[0] if a.source_ids else "",
                        source_b=b.source_ids[0] if b.source_ids else "",
                        contradiction_type=ctype,
                        severity="medium",
                        confidence=min(a.confidence, b.confidence),
                        recommended_resolution="Operator should decide which claim is current",
                        requires_operator_decision=True,
                    ))
        return contradictions

    def _check_contradiction(self, a: CanonicalClaim, b: CanonicalClaim) -> str | None:
        if a.freshness == "stale" and b.freshness in ("fresh", "recent"):
            a_words = set(a.claim_text.lower().split())
            b_words = set(b.claim_text.lower().split())
            if len(a_words & b_words) > 3:
                return ContradictionType.STALE_VS_CURRENT.value
        a_lower = a.claim_text.lower()
        b_lower = b.claim_text.lower()
        shared_entities = set(a.entity_refs) & set(b.entity_refs)
        if shared_entities:
            if ("not" in a_lower and "not" not in b_lower) or ("not" in b_lower and "not" not in a_lower):
                return ContradictionType.DIRECT_CONFLICT.value
            if a.domain == b.domain and a.canonicality != b.canonicality:
                return ContradictionType.SOURCE_OF_TRUTH_CONFLICT.value
        return None

    def _detect_outdated_claims(self, claims: list[CanonicalClaim]) -> list[CanonicalClaim]:
        return [c for c in claims if c.freshness == "stale"]

    def _detect_missing_context(self, items: list[IngestedItem]) -> list[str]:
        found_entities: set[str] = set()
        for item in items:
            found_entities.update(item.extracted_entities)
        missing: list[str] = []
        for entity in _get_expected_products() | _get_expected_companies():
            if entity not in found_entities:
                missing.append(f"No context found for expected entity: {entity}")
        return missing

    def _detect_open_questions(self, items: list[IngestedItem]) -> list[str]:
        questions: list[str] = []
        entities: set[str] = set()
        for item in items:
            entities.update(item.extracted_entities)
        knowledge = _load_entity_knowledge()
        for rule in knowledge.get("open_question_rules", []):
            required = rule.get("requires", [])
            if all(r in entities for r in required):
                questions.append(rule["question"])
        return questions

    def _build_entity_map(self, items: list[IngestedItem]) -> dict[str, Any]:
        entity_map: dict[str, Any] = {}
        found: set[str] = set()
        for item in items:
            found.update(item.extracted_entities)
        for entity_name in found:
            info = _get_known_entities().get(entity_name, {"type": "unknown", "description": ""})
            entity_map[entity_name] = {
                "type": info["type"],
                "description": info["description"],
                "found_in_sources": True,
            }
        for entity_name, info in _get_known_entities().items():
            if entity_name not in entity_map:
                entity_map[entity_name] = {
                    "type": info["type"],
                    "description": info["description"],
                    "found_in_sources": False,
                }
        return entity_map

    def _detect_roadmap_implications(self, items: list[IngestedItem]) -> list[str]:
        implications: list[str] = []
        for item in items:
            for claim in item.extracted_claims:
                if any(kw in claim.lower() for kw in ("phase", "roadmap", "milestone", "next")):
                    implications.append(f"Roadmap reference: {claim[:120]}")
                    if len(implications) >= 10:
                        return implications
        return implications

    def _detect_work_packet_implications(self, items: list[IngestedItem]) -> list[str]:
        implications: list[str] = []
        for item in items:
            for claim in item.extracted_claims:
                if any(kw in claim.lower() for kw in ("build", "implement", "create", "deploy", "fix")):
                    implications.append(f"Work candidate: {claim[:120]}")
                    if len(implications) >= 10:
                        return implications
        return implications

    def _detect_memory_implications(self, items: list[IngestedItem]) -> list[str]:
        return [
            f"Entity discovered: {e}"
            for item in items
            for e in item.extracted_entities[:5]
        ][:10]

    def _recommend_canonical_updates(
        self,
        claims: list[CanonicalClaim],
        contradictions: list[ContextContradiction],
        outdated: list[CanonicalClaim],
    ) -> list[CanonicalUpdateProposal]:
        proposals: list[CanonicalUpdateProposal] = []
        for contradiction in contradictions:
            prop = CanonicalUpdateProposal(
                proposal_type=ProposalType.SUPERSEDE_CLAIM.value,
                title=f"Resolve contradiction: {contradiction.claim_a[:60]}",
                description=f"Claims conflict: '{contradiction.claim_a[:80]}' vs '{contradiction.claim_b[:80]}'",
                current_state=contradiction.claim_a,
                proposed_state=contradiction.claim_b,
                source_ids=[contradiction.source_a, contradiction.source_b],
                evidence=[contradiction.claim_a, contradiction.claim_b],
                confidence=contradiction.confidence,
                risk_class="low",
                status=ProposalStatus.DRAFTED.value,
            )
            self._proposal_store.save_proposal(prop)
            proposals.append(prop)
        for claim in outdated:
            prop = CanonicalUpdateProposal(
                proposal_type=ProposalType.DEPRECATE_CLAIM.value,
                title=f"Deprecate stale claim: {claim.claim_text[:60]}",
                description=f"Claim is stale: '{claim.claim_text[:120]}'",
                current_state=claim.claim_text,
                proposed_state="[deprecated]",
                source_ids=claim.source_ids,
                evidence=claim.evidence,
                confidence=claim.confidence,
                risk_class="low",
                status=ProposalStatus.DRAFTED.value,
            )
            self._proposal_store.save_proposal(prop)
            proposals.append(prop)
        return proposals

    def _recommend_deprecations(self, outdated: list[CanonicalClaim]) -> list[str]:
        return [f"Deprecate: {c.claim_text[:80]}" for c in outdated]

    def _recommend_work_packets(self, items: list[IngestedItem]) -> list[str]:
        packets: list[str] = []
        for item in items:
            for wi in item.extracted_work_items:
                packets.append(wi[:120])
                if len(packets) >= 5:
                    return packets
        return packets

    def _recommend_operator_questions(
        self, items: list[IngestedItem], contradictions: list[ContextContradiction]
    ) -> list[str]:
        questions: list[str] = []
        for c in contradictions:
            if c.requires_operator_decision:
                questions.append(f"Which is correct: '{c.claim_a[:60]}' or '{c.claim_b[:60]}'?")
        return questions[:10]

    def _classify_domain(self, text: str) -> str:
        lower = text.lower()
        if any(kw in lower for kw in ("roadmap", "phase", "milestone")):
            return "roadmap"
        if any(kw in lower for kw in ("product", "feature", "capability")):
            return "product"
        if any(kw in lower for kw in ("company", "entity", "venture")):
            return "entity"
        if any(kw in lower for kw in ("deploy", "runtime", "service")):
            return "infrastructure"
        return "general"

    def _compute_confidence(self, report: ContextDiagnosticReport) -> float:
        if report.item_count == 0:
            return 0.0
        base = 0.5
        if report.contradictions:
            base -= 0.1 * min(len(report.contradictions), 3)
        if report.missing_context:
            base -= 0.05 * min(len(report.missing_context), 4)
        if len(report.canonical_claims) > 5:
            base += 0.1
        return max(0.0, min(1.0, base))
