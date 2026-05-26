"""GenericIngestionOrchestrator — source-agnostic canonical pipeline.

Sequences: perceive → interpret → decompose → bridge → map → persist → query.
Uses existing contract classes from core.ontology and execution.bridge.
No source-specific logic inside — source abstraction handles that.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveRelationship,
    PrimitiveType,
    RelationshipType,
)
import substrate.understanding.domains.business  # noqa: F401  — auto-registers BusinessBridge
from substrate.understanding.domains.contract import DomainProjection
from substrate.understanding.domains.registry import default_registry as _bridge_registry
from substrate.governance.policy.authority_tier import T5_DEFAULT, get_authority_tier
from substrate.understanding.perception.source import RawContent, Source
from substrate.execution.bridge.memory_scope_contracts import (
    MemoryScope,
    MemoryScopeAssignment,
    PromotionPath,
)


@dataclass
class Signal:
    """Perception output."""

    signal_id: str
    source_path: str
    source_type: str
    content_sha256: str
    content_length: dict[str, int]
    timestamp_utc: str
    perceive_duration_ms: float
    authority_tier: int = T5_DEFAULT

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "content_sha256": self.content_sha256,
            "content_length": self.content_length,
            "timestamp_utc": self.timestamp_utc,
            "perceive_duration_ms": self.perceive_duration_ms,
            "authority_tier": self.authority_tier,
            "entry_point_invoked": {
                "module": "runtime.ingestion.orchestrator",
                "function": "GenericIngestionOrchestrator._perceive",
            },
        }


@dataclass
class InterpretationResult:
    """Interpretation output."""

    signal_id: str
    inferred_document_type: str
    inferred_domains: list[str]
    confidence: float
    structural_features: dict[str, Any]
    intent_candidates: list[str]
    interpret_duration_ms: float
    authority_tier: int = T5_DEFAULT

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "inferred_document_type": self.inferred_document_type,
            "inferred_domains": self.inferred_domains,
            "confidence": self.confidence,
            "structural_features": self.structural_features,
            "intent_candidates": self.intent_candidates,
            "interpret_duration_ms": self.interpret_duration_ms,
            "authority_tier": self.authority_tier,
            "entry_point_invoked": {
                "module": "runtime.ingestion.orchestrator",
                "function": "GenericIngestionOrchestrator._interpret",
            },
        }


@dataclass
class WorldUpdate:
    """World model mapping output."""

    signal_id: str
    entities_added: list[dict[str, Any]]
    entities_updated: list[dict[str, Any]]
    facts_written: list[dict[str, Any]]
    conflicts_with_existing_state: list[str]
    map_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "entities_added": self.entities_added,
            "entities_updated": self.entities_updated,
            "facts_written": self.facts_written,
            "conflicts_with_existing_state": self.conflicts_with_existing_state,
            "map_duration_ms": self.map_duration_ms,
            "entry_point_invoked": {
                "module": "runtime.ingestion.orchestrator",
                "function": "GenericIngestionOrchestrator._map",
            },
        }


@dataclass
class MemoryWrite:
    """Memory persistence output."""

    signal_id: str
    new_canonical_memory_entry_id: str
    governance_decision: str
    governance_scope: dict[str, Any]
    provenance_chain: dict[str, str]
    confidence_score: float
    timestamp_utc: str
    persist_duration_ms: float
    memories_jsonl_before: int
    memories_jsonl_after: int
    memory_ids_written: list[str] = field(default_factory=list)
    entries_written: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "new_canonical_memory_entry_id": self.new_canonical_memory_entry_id,
            "governance_decision": self.governance_decision,
            "governance_scope": self.governance_scope,
            "provenance_chain": self.provenance_chain,
            "confidence_score": self.confidence_score,
            "timestamp_utc": self.timestamp_utc,
            "persist_duration_ms": self.persist_duration_ms,
            "memories_jsonl_before": self.memories_jsonl_before,
            "memories_jsonl_after": self.memories_jsonl_after,
            "memory_ids_written": self.memory_ids_written,
            "entries_written": self.entries_written,
        }


@dataclass
class PromotionReceipt:
    """Promotion receipt output."""

    receipt_id: str
    candidate_id: str
    decision: str
    reason: str
    confidence: float
    promoter: str
    timestamp: str
    rollback_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "candidate_id": self.candidate_id,
            "decision": self.decision,
            "reason": self.reason,
            "confidence": self.confidence,
            "promoter": self.promoter,
            "timestamp": self.timestamp,
            "rollback_reference": self.rollback_reference,
        }


@dataclass
class QueryProof:
    """Query-back verification output."""

    signal_id: str
    query_string: str
    query_derivation: str
    retrieval_method: str
    retrieved_entries: list[dict[str, Any]]
    new_entry_appears_in_results: bool
    new_entry_rank: int | None
    total_entries_searched: int
    query_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "query_string": self.query_string,
            "query_derivation": self.query_derivation,
            "retrieval_method": self.retrieval_method,
            "retrieved_entries": self.retrieved_entries,
            "new_entry_appears_in_results": self.new_entry_appears_in_results,
            "new_entry_rank": self.new_entry_rank,
            "total_entries_searched": self.total_entries_searched,
            "query_duration_ms": self.query_duration_ms,
        }


# NOTE: The canonical IngestionResult is a Pydantic model in substrate.types
# (simple: source_uri, observations_count, projections_count, success, error).
# This is the pipeline-scoped version with full stage-by-stage detail.
from substrate.types import IngestionResult as CanonicalIngestionResult  # noqa: F401


@dataclass
class IngestionResult:
    """Complete result of a generic ingestion cycle."""

    signal: Signal | None = None
    interpretation: InterpretationResult | None = None
    decomposition: DecompositionResult | None = None
    projections: list[DomainProjection] = field(default_factory=list)
    world_update: WorldUpdate | None = None
    memory_write: MemoryWrite | None = None
    promotion_receipt: PromotionReceipt | None = None
    promotion_receipts: list[PromotionReceipt] = field(default_factory=list)
    query_proof: QueryProof | None = None
    cycle_duration_ms: float = 0.0
    verdict: str = "NOT_STARTED"
    error_trace: str = ""
    failed_stage: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.to_dict() if self.signal else None,
            "interpretation": self.interpretation.to_dict() if self.interpretation else None,
            "decomposition": self.decomposition.to_dict() if self.decomposition else None,
            "projections": [p.to_dict() for p in self.projections],
            "world_update": self.world_update.to_dict() if self.world_update else None,
            "memory_write": self.memory_write.to_dict() if self.memory_write else None,
            "promotion_receipt": self.promotion_receipt.to_dict()
            if self.promotion_receipt
            else None,
            "promotion_receipts": [r.to_dict() for r in self.promotion_receipts],
            "query_proof": self.query_proof.to_dict() if self.query_proof else None,
            "cycle_duration_ms": self.cycle_duration_ms,
            "verdict": self.verdict,
            "error_trace": self.error_trace,
            "failed_stage": self.failed_stage,
        }


# Domain keyword bank for interpretation
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "architecture": ["architecture", "domain", "module", "spine", "layer"],
    "runtime": ["runtime", "execution", "cognitive", "loop", "agent"],
    "governance": ["governance", "authority", "constraint", "policy", "approval"],
    "memory": ["memory", "canonical", "persistence", "store", "retrieval"],
    "ingestion": ["ingestion", "perceive", "interpret", "decompose", "pipeline"],
    "transport": ["transport", "relay", "session", "dispatch", "channel"],
    "identity": ["identity", "soul", "ai_name", "principle", "agent_type"],
    "testing": ["test", "pytest", "fixture", "assertion", "coverage"],
    "deployment": ["docker", "container", "deploy", "service", "cron"],
    "knowledge": ["wiki", "palace", "knowledge", "codebase", "navigation"],
}


class GenericIngestionOrchestrator:
    """Source-agnostic ingestion orchestrator.

    Sequences the canonical pipeline using existing contract classes.
    No source-specific logic. Dependencies injected.
    """

    def __init__(
        self,
        memory_store_path: Path,
        proof_dir: Path | None = None,
    ) -> None:
        self._memory_store_path = memory_store_path
        self._memories_path = memory_store_path / "memories.jsonl"
        self._receipts_path = memory_store_path / "promotion_receipts.jsonl"
        self._index_path = memory_store_path / "index.json"
        self._summary_path = memory_store_path / "promotion_summary.json"
        self._proof_dir = proof_dir

    def ingest(self, source: Source) -> IngestionResult:
        """Run the full canonical pipeline on a source."""
        result = IngestionResult()
        cycle_start = time.monotonic()

        try:
            if not source.exists():
                result.verdict = "FAILED_AT_PERCEIVE"
                result.error_trace = f"Source does not exist: {source.source_id}"
                return result

            raw = source.read()
            meta = source.metadata()
            ts_utc = datetime.now(timezone.utc).isoformat()

            result.signal = self._perceive(raw, meta, ts_utc, source.authority_tier)
            print(f"[ingestion-orchestrator] perceive: {result.signal.signal_id}")

            result.interpretation = self._interpret(result.signal, raw)
            print(
                f"[ingestion-orchestrator] interpret: {result.interpretation.inferred_document_type}"
            )

            result.decomposition = self._decompose(result.signal, result.interpretation, raw)
            print(
                f"[ingestion-orchestrator] decompose: {len(result.decomposition.observations)} observations"
            )

            result.projections = self._bridge(result.decomposition)
            print(f"[ingestion-orchestrator] bridge: {len(result.projections)} projections")

            result.world_update = self._map(result.signal, result.decomposition, ts_utc)
            print(
                f"[ingestion-orchestrator] map: {len(result.world_update.entities_added)} entities"
            )

            mem_write, receipts = self._persist(
                result.signal,
                result.decomposition,
                result.projections,
                result.world_update,
                raw,
                meta,
                ts_utc,
            )
            result.memory_write = mem_write
            result.promotion_receipts = receipts
            result.promotion_receipt = receipts[0] if receipts else None
            print(f"[ingestion-orchestrator] persist: {mem_write.entries_written} entries")

            result.query_proof = self._query_back(result.signal, result.memory_write, raw)
            print(f"[ingestion-orchestrator] query: rank={result.query_proof.new_entry_rank}")

            result.verdict = "COMPLETE_CYCLE"

        except Exception as exc:
            result.error_trace = traceback.format_exc()
            if result.signal is None:
                result.failed_stage = "perceive"
                result.verdict = "FAILED_AT_PERCEIVE"
            elif result.interpretation is None:
                result.failed_stage = "interpret"
                result.verdict = "FAILED_AT_INTERPRET"
            elif result.decomposition is None:
                result.failed_stage = "decompose"
                result.verdict = "FAILED_AT_DECOMPOSE"
            elif result.world_update is None:
                result.failed_stage = "map"
                result.verdict = "FAILED_AT_MAP"
            elif result.memory_write is None:
                result.failed_stage = "persist"
                result.verdict = "FAILED_AT_PERSIST"
            else:
                result.failed_stage = "query"
                result.verdict = "FAILED_AT_QUERY"
            print(f"[ingestion-orchestrator] FAILED: {exc}")

        result.cycle_duration_ms = round((time.monotonic() - cycle_start) * 1000, 2)

        if self._proof_dir is not None:
            self._write_proofs(result)

        return result

    def _perceive(
        self, raw: RawContent, meta: dict[str, Any], ts_utc: str, authority_tier: int = T5_DEFAULT
    ) -> Signal:
        t0 = time.monotonic()
        lines = raw.content.count("\n") + 1
        words = len(raw.content.split())
        chars = len(raw.content)
        signal_id = f"SIG-{uuid.uuid4().hex[:12]}"
        dur = round((time.monotonic() - t0) * 1000, 2)
        return Signal(
            signal_id=signal_id,
            source_path=meta.get("path", "unknown"),
            source_type=meta.get("content_type", "text/plain"),
            content_sha256=raw.sha256,
            content_length={"chars": chars, "words": words, "lines": lines},
            timestamp_utc=ts_utc,
            perceive_duration_ms=dur,
            authority_tier=authority_tier,
        )

    def _interpret(self, signal: Signal, raw: RawContent) -> InterpretationResult:
        t0 = time.monotonic()
        text = raw.content
        has_yaml = text.startswith("---")
        has_headings = "## " in text or "# " in text
        has_code = "```" in text
        has_wikilinks = "[[" in text
        heading_count = text.count("\n## ") + text.count("\n# ")

        doc_type = "structured_operational_document" if has_yaml else "markdown_prose"
        if not has_headings and not has_code:
            doc_type = "plain_text"

        text_lower = text.lower()
        domains = []
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits >= 2:
                domains.append(domain)
        confidence = min(0.95, 0.6 + 0.08 * len(domains))

        intent_candidates = []
        if has_headings and heading_count >= 3:
            intent_candidates.append("reference_document — structured multi-section content")
        if "must" in text_lower or "never" in text_lower or "always" in text_lower:
            intent_candidates.append("protocol_or_policy — contains prescriptive directives")

        dur = round((time.monotonic() - t0) * 1000, 2)
        return InterpretationResult(
            signal_id=signal.signal_id,
            inferred_document_type=doc_type,
            inferred_domains=domains,
            confidence=confidence,
            structural_features={
                "has_yaml_frontmatter": has_yaml,
                "heading_count": heading_count,
                "has_code_blocks": has_code,
                "has_wikilinks": has_wikilinks,
            },
            intent_candidates=intent_candidates,
            interpret_duration_ms=dur,
            authority_tier=signal.authority_tier,
        )

    # Valid enum values for LLM prompt and validation
    _PRIMITIVE_TYPES = {t.value for t in PrimitiveType}
    _RELATIONSHIP_TYPES = {t.value for t in RelationshipType}

    _EXTRACTION_PROMPT = """\
You are a document decomposition engine. Extract structured observations from the document below.

Each observation is a typed primitive with a semantic label, description, evidence, and confidence score.

VALID primitive_type values: {primitive_types}
VALID relationship_type values: {relationship_types}

RULES:
- label: semantic name (≤80 chars). NOT raw text. No markdown formatting (no #, **, backticks). Self-contained.
- description: adds context beyond label (≤300 chars). NOT a copy of label. NOT raw text.
- evidence: verbatim span from the document (≤300 chars). Quoted, not paraphrased.
- source_reference: "{source_path}:<locator>" where locator is line range, section name, or paragraph index.
- confidence: 0.85-0.95 for direct extraction, 0.70-0.85 for inferred.
- is_inferred: true only if synthesized from multiple signals, false if directly stated.
- Produce 4-10 observations spanning at least 3 distinct primitive types.
- Produce at least 1 relationship per 3 observations. Each relationship must have a semantic basis.
- Prescriptive content (must/never/always) → constraint observations.
- Procedural content (steps, sequences) → action observations.
- Declarative state (X is Y, X has Z) → state observations.

Return ONLY valid JSON matching this schema:
{{
  "observations": [
    {{
      "primitive_type": "<type>",
      "label": "<semantic label>",
      "description": "<semantic description>",
      "confidence": <float>,
      "source_reference": "<path:locator>",
      "evidence": "<verbatim span>",
      "is_inferred": <bool>
    }}
  ],
  "relationships": [
    {{
      "from_index": <int>,
      "to_index": <int>,
      "relationship_type": "<type>",
      "confidence": <float>,
      "description": "<why this relationship exists>"
    }}
  ]
}}

from_index and to_index are 0-based indices into the observations array.

DOCUMENT SOURCE: {source_path}
---
{content}
---"""

    def _decompose(
        self,
        signal: Signal,
        interp: InterpretationResult,
        raw: RawContent,
    ) -> DecompositionResult:
        t0 = time.monotonic()
        decomp_id = f"decomp-{uuid.uuid4().hex[:16]}"

        result = self._decompose_llm(signal, interp, raw, decomp_id)
        if result is None:
            logging.getLogger(__name__).warning(
                "[decompose] LLM extraction failed, falling back to heuristic"
            )
            result = self._decompose_heuristic(signal, interp, raw, decomp_id)

        for obs in result.observations:
            obs.authority_tier = interp.authority_tier

        result.compute_coverage()
        dur = round((time.monotonic() - t0) * 1000, 2)

        result._duration_ms = dur  # type: ignore[attr-defined]
        result._signal_id = signal.signal_id  # type: ignore[attr-defined]
        result._counts = {  # type: ignore[attr-defined]
            "entities": len(result.observations),
            "concepts": len(set(o.primitive_type.value for o in result.observations)),
            "relationships": len(result.relationships),
        }
        return result

    def _decompose_llm(
        self,
        signal: Signal,
        interp: InterpretationResult,
        raw: RawContent,
        decomp_id: str,
    ) -> DecompositionResult | None:
        """LLM-based semantic extraction. Returns None on failure."""
        log = logging.getLogger(__name__)

        content = raw.content
        if len(content) > 12000:
            content = content[:12000]

        prompt = self._EXTRACTION_PROMPT.format(
            primitive_types=", ".join(sorted(self._PRIMITIVE_TYPES)),
            relationship_types=", ".join(sorted(self._RELATIONSHIP_TYPES)),
            source_path=signal.source_path,
            content=content,
        )

        for attempt in range(2):
            try:
                from adapters.models.model_router import call_with_fallback, TaskType

                result = call_with_fallback(
                    prompt=prompt,
                    system="You are a structured data extraction engine. Return only valid JSON.",
                    task_type=TaskType.ANALYSIS,
                )
                raw_output = result.output.strip()
                parsed = self._parse_extraction_output(raw_output, signal, raw.sha256, decomp_id)
                if parsed is not None:
                    return parsed
                log.warning("[decompose] LLM output failed validation (attempt %d)", attempt + 1)
            except Exception as exc:
                log.warning("[decompose] LLM call failed (attempt %d): %s", attempt + 1, exc)

        return None

    def _parse_extraction_output(
        self,
        raw_output: str,
        signal: Signal,
        content_hash: str,
        decomp_id: str,
    ) -> DecompositionResult | None:
        """Parse and validate LLM JSON output into typed observations."""
        # Extract JSON from possible markdown code fence
        text = raw_output
        if "```" in text:
            start = text.find("```")
            first_newline = text.find("\n", start)
            end = text.find("```", first_newline)
            if first_newline != -1 and end != -1:
                text = text[first_newline + 1 : end]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict) or "observations" not in data:
            return None

        raw_obs = data["observations"]
        if not isinstance(raw_obs, list) or len(raw_obs) < 2:
            return None

        observations: list[PrimitiveObservation] = []
        for item in raw_obs[:10]:
            ptype = item.get("primitive_type", "")
            if ptype not in self._PRIMITIVE_TYPES:
                continue
            label = str(item.get("label", ""))[:80].strip()
            description = str(item.get("description", ""))[:300].strip()
            if not label or not description or label == description:
                continue
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType(ptype),
                    label=label,
                    description=description,
                    confidence=max(0.0, min(1.0, float(item.get("confidence", 0.8)))),
                    source_reference=str(item.get("source_reference", signal.source_path))[:200],
                    evidence=str(item.get("evidence", ""))[:300],
                    is_inferred=bool(item.get("is_inferred", False)),
                )
            )

        if len(observations) < 2:
            return None

        # Validate type coverage — need at least 2 distinct types
        type_set = {o.primitive_type.value for o in observations}
        if len(type_set) < 2:
            return None

        relationships: list[PrimitiveRelationship] = []
        for rel in data.get("relationships", [])[:8]:
            rtype = rel.get("relationship_type", "")
            if rtype not in self._RELATIONSHIP_TYPES:
                continue
            from_idx = rel.get("from_index")
            to_idx = rel.get("to_index")
            if not isinstance(from_idx, int) or not isinstance(to_idx, int):
                continue
            if from_idx < 0 or from_idx >= len(observations):
                continue
            if to_idx < 0 or to_idx >= len(observations):
                continue
            if from_idx == to_idx:
                continue
            relationships.append(
                PrimitiveRelationship(
                    from_observation_id=observations[from_idx].observation_id,
                    to_observation_id=observations[to_idx].observation_id,
                    relationship_type=RelationshipType(rtype),
                    confidence=max(0.0, min(1.0, float(rel.get("confidence", 0.8)))),
                    description=str(rel.get("description", ""))[:200],
                )
            )

        return DecompositionResult(
            decomposition_id=decomp_id,
            source_content_hash=content_hash,
            observations=observations,
            relationships=relationships,
            decomposition_confidence=round(
                sum(o.confidence for o in observations) / len(observations), 2
            ),
        )

    def _decompose_heuristic(
        self,
        signal: Signal,
        interp: InterpretationResult,
        raw: RawContent,
        decomp_id: str,
    ) -> DecompositionResult:
        """Heuristic fallback — shallow but zero-cost extraction."""
        text = raw.content
        lines = text.split("\n")

        observations: list[PrimitiveObservation] = []
        headings = [(i, l.lstrip("#").strip()) for i, l in enumerate(lines) if l.startswith("#")]

        if headings:
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType.STATE,
                    label=f"Document has {len(headings)} sections",
                    description=f"Structured document with sections: {', '.join(h[1][:50] for h in headings[:8])}",
                    confidence=0.95,
                    source_reference=f"{signal.source_path}:headings",
                    evidence="; ".join(h[1][:40] for h in headings[:5]),
                    is_inferred=False,
                )
            )

        for domain in interp.inferred_domains[:3]:
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType.RESOURCE,
                    label=f"Domain coverage: {domain}",
                    description=f"Document covers the {domain} domain based on keyword analysis.",
                    confidence=interp.confidence,
                    source_reference=f"{signal.source_path}:domain:{domain}",
                    evidence=f"Domain {domain} detected via keyword overlap",
                    is_inferred=False,
                )
            )

        constraint_phrases = [
            l.strip()
            for l in lines
            if any(w in l.lower() for w in ["must", "never", "always", "required", "forbidden"])
        ]
        for phrase in constraint_phrases[:3]:
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType.CONSTRAINT,
                    label=phrase[:80],
                    description=phrase[:200],
                    confidence=0.85,
                    source_reference=f"{signal.source_path}:constraint",
                    evidence=phrase[:200],
                    is_inferred=False,
                )
            )

        if interp.intent_candidates:
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType.GOAL,
                    label=f"Document intent: {interp.intent_candidates[0][:60]}",
                    description=interp.intent_candidates[0],
                    confidence=0.80,
                    source_reference=f"{signal.source_path}:intent",
                    evidence=interp.intent_candidates[0],
                    is_inferred=True,
                )
            )

        if not observations:
            observations.append(
                PrimitiveObservation(
                    observation_id=f"obs-{uuid.uuid4().hex[:8]}",
                    primitive_type=PrimitiveType.SIGNAL,
                    label=f"Document ingested: {signal.source_path.split('/')[-1]}",
                    description=f"Content ingested from {signal.source_path} ({signal.content_length['words']} words).",
                    confidence=0.70,
                    source_reference=signal.source_path,
                    evidence=text[:200],
                    is_inferred=False,
                )
            )

        relationships: list[PrimitiveRelationship] = []
        if len(observations) >= 2:
            relationships.append(
                PrimitiveRelationship(
                    from_observation_id=observations[0].observation_id,
                    to_observation_id=observations[1].observation_id,
                    relationship_type=RelationshipType.ENABLES,
                    confidence=0.80,
                    description="Document structure enables domain coverage identification.",
                )
            )

        return DecompositionResult(
            decomposition_id=decomp_id,
            source_content_hash=raw.sha256,
            observations=observations,
            relationships=relationships,
            decomposition_confidence=round(
                sum(o.confidence for o in observations) / max(len(observations), 1), 2
            ),
        )

    def _map(
        self,
        signal: Signal,
        decomp: DecompositionResult,
        ts_utc: str,
    ) -> WorldUpdate:
        t0 = time.monotonic()
        entities = []
        facts = []
        for obs in decomp.observations:
            entity_id = f"ent-{uuid.uuid4().hex[:8]}"
            entities.append(
                {
                    "entity_id": entity_id,
                    "observation_id": obs.observation_id,
                    "primitive_type": obs.primitive_type.value,
                    "label": obs.label,
                    "status": "added",
                }
            )
            facts.append(
                {
                    "fact_id": f"fact-{uuid.uuid4().hex[:8]}",
                    "entity_id": entity_id,
                    "statement": obs.description,
                    "source": f"{signal.source_path} via {signal.signal_id}",
                    "timestamp": ts_utc,
                    "confidence": obs.confidence,
                    "evidence": obs.evidence[:200],
                }
            )
        dur = round((time.monotonic() - t0) * 1000, 2)
        return WorldUpdate(
            signal_id=signal.signal_id,
            entities_added=entities,
            entities_updated=[],
            facts_written=facts,
            conflicts_with_existing_state=[],
            map_duration_ms=dur,
        )

    def _bridge(self, decomp: DecompositionResult) -> list[DomainProjection]:
        """Run all registered domain bridges over decomposition observations."""
        projections: list[DomainProjection] = []
        bridges = _bridge_registry.get_all()
        if not bridges:
            return projections
        for obs in decomp.observations:
            for bridge in bridges:
                projection = bridge.bridge(obs)
                if projection is not None:
                    projections.append(projection)
        return projections

    def _persist(
        self,
        signal: Signal,
        decomp: DecompositionResult,
        projections: list[DomainProjection],
        world: WorldUpdate,
        raw: RawContent,
        meta: dict[str, Any],
        ts_utc: str,
    ) -> tuple[MemoryWrite, list[PromotionReceipt]]:
        t0 = time.monotonic()

        before_count = (
            len(self._memories_path.read_text().strip().split("\n"))
            if self._memories_path.exists()
            else 0
        )

        if not decomp.observations:
            raise ValueError("No observations to persist")

        scope = MemoryScopeAssignment(
            source_id=signal.signal_id,
            assigned_scope=MemoryScope.PROJECT_MEMORY,
            promotion_path=PromotionPath.SOURCE_TO_INSTANCE_MEMORY,
            notes="Generic orchestrator ingestion. Project-scoped.",
        )

        doc_id = f"local-{raw.sha256[:16]}"
        all_memory_ids: list[str] = []
        all_receipts: list[PromotionReceipt] = []
        first_memory_id = ""
        first_candidate_id = ""
        first_receipt_id = ""
        best_obs = max(decomp.observations, key=lambda o: o.confidence)

        index = None
        if self._index_path.exists():
            index = json.loads(self._index_path.read_text())

        summary = None
        if self._summary_path.exists():
            summary = json.loads(self._summary_path.read_text())

        with open(self._memories_path, "a") as mem_f, open(self._receipts_path, "a") as rec_f:
            for obs in decomp.observations:
                memory_id = f"mem-{uuid.uuid4().hex[:16]}"
                candidate_id = f"cand-{uuid.uuid4().hex[:16]}"
                receipt_id = f"receipt-{uuid.uuid4().hex[:16]}"

                if not first_memory_id:
                    first_memory_id = memory_id
                    first_candidate_id = candidate_id
                    first_receipt_id = receipt_id

                memory_entry = {
                    "memory_id": memory_id,
                    "candidate_id": candidate_id,
                    "memory_type": "canonical",
                    "primitive_type": obs.primitive_type.value,
                    "label": obs.label,
                    "content": obs.description,
                    "confidence": obs.confidence,
                    "authority_tier": obs.authority_tier,
                    "source_document_id": doc_id,
                    "source_content_hash": raw.sha256,
                    "source_decomposition_id": decomp.decomposition_id,
                    "promotion_receipt_id": receipt_id,
                    "provenance": {
                        "source_reference": obs.source_reference,
                        "evidence": obs.evidence,
                        "is_inferred": obs.is_inferred,
                    },
                    "lineage": {
                        "candidate_id": candidate_id,
                        "decomposition_id": decomp.decomposition_id,
                        "document_id": doc_id,
                        "document_path": meta.get("path", "unknown"),
                        "content_hash": raw.sha256,
                        "classification_reason": f"{obs.primitive_type.value} is structurally canonical",
                    },
                    "timestamp": ts_utc,
                }

                mem_f.write(json.dumps(memory_entry) + "\n")

                receipt_data = {
                    "receipt_id": receipt_id,
                    "candidate_id": candidate_id,
                    "decision": "promoted",
                    "reason": f"Generic orchestrator ingestion — {obs.primitive_type.value}",
                    "confidence": obs.confidence,
                    "promoter": "generic-ingestion-orchestrator",
                    "timestamp": ts_utc,
                    "rollback_reference": f"candidate:{candidate_id}",
                }

                rec_f.write(json.dumps(receipt_data) + "\n")

                all_memory_ids.append(memory_id)
                all_receipts.append(PromotionReceipt(**receipt_data))

                if index is not None:
                    index["entries"][memory_id] = {
                        "memory_type": "canonical",
                        "primitive_type": obs.primitive_type.value,
                        "label": obs.label,
                        "source_document_id": doc_id,
                        "timestamp": ts_utc,
                    }

                if summary is not None:
                    summary["promoted_canonical"].append(
                        {
                            "memory_id": memory_id,
                            "receipt_id": receipt_id,
                            "label": obs.label,
                            "type": obs.primitive_type.value,
                        }
                    )

            for proj in projections:
                proj_mem_id = f"mem-{uuid.uuid4().hex[:16]}"
                proj_cand_id = f"cand-{uuid.uuid4().hex[:16]}"
                proj_receipt_id = f"receipt-{uuid.uuid4().hex[:16]}"

                proj_entry = {
                    "memory_id": proj_mem_id,
                    "candidate_id": proj_cand_id,
                    "memory_type": "domain_projection",
                    "domain_id": proj.domain_id,
                    "domain_primitive_type": proj.domain_primitive_type,
                    "label": proj.label,
                    "content": proj.description,
                    "confidence": proj.confidence,
                    "authority_tier": proj.authority_tier,
                    "source_document_id": doc_id,
                    "source_content_hash": raw.sha256,
                    "source_decomposition_id": decomp.decomposition_id,
                    "ontology_observation_ref": proj.ontology_observation_ref,
                    "projection_id": proj.projection_id,
                    "promotion_receipt_id": proj_receipt_id,
                    "properties": proj.properties,
                    "provenance": {
                        "evidence": proj.evidence,
                    },
                    "lineage": {
                        "candidate_id": proj_cand_id,
                        "decomposition_id": decomp.decomposition_id,
                        "document_id": doc_id,
                        "document_path": meta.get("path", "unknown"),
                        "content_hash": raw.sha256,
                        "classification_reason": f"domain projection: {proj.domain_id}/{proj.domain_primitive_type}",
                    },
                    "timestamp": ts_utc,
                }

                mem_f.write(json.dumps(proj_entry) + "\n")

                proj_receipt_data = {
                    "receipt_id": proj_receipt_id,
                    "candidate_id": proj_cand_id,
                    "decision": "promoted",
                    "reason": f"Domain projection — {proj.domain_id}/{proj.domain_primitive_type}",
                    "confidence": proj.confidence,
                    "promoter": "generic-ingestion-orchestrator",
                    "timestamp": ts_utc,
                    "rollback_reference": f"candidate:{proj_cand_id}",
                }

                rec_f.write(json.dumps(proj_receipt_data) + "\n")

                all_memory_ids.append(proj_mem_id)
                all_receipts.append(PromotionReceipt(**proj_receipt_data))

                if index is not None:
                    index["entries"][proj_mem_id] = {
                        "memory_type": "domain_projection",
                        "domain_id": proj.domain_id,
                        "domain_primitive_type": proj.domain_primitive_type,
                        "label": proj.label,
                        "source_document_id": doc_id,
                        "timestamp": ts_utc,
                    }

                if summary is not None:
                    summary["promoted_canonical"].append(
                        {
                            "memory_id": proj_mem_id,
                            "receipt_id": proj_receipt_id,
                            "label": proj.label,
                            "type": f"projection:{proj.domain_primitive_type}",
                        }
                    )

        if index is not None:
            self._index_path.write_text(json.dumps(index, indent=2))

        if summary is not None:
            self._summary_path.write_text(json.dumps(summary, indent=2))

        after_count = len(self._memories_path.read_text().strip().split("\n"))
        dur = round((time.monotonic() - t0) * 1000, 2)

        mem_write = MemoryWrite(
            signal_id=signal.signal_id,
            new_canonical_memory_entry_id=first_memory_id,
            governance_decision="autonomous",
            governance_scope=scope.to_dict(),
            provenance_chain={
                "signal_id": signal.signal_id,
                "decomposition_id": decomp.decomposition_id,
                "candidate_id": first_candidate_id,
                "memory_id": first_memory_id,
                "receipt_id": first_receipt_id,
            },
            confidence_score=best_obs.confidence,
            timestamp_utc=ts_utc,
            persist_duration_ms=dur,
            memories_jsonl_before=before_count,
            memories_jsonl_after=after_count,
            memory_ids_written=all_memory_ids,
            entries_written=len(all_memory_ids),
        )

        return mem_write, all_receipts

    def _query_back(
        self,
        signal: Signal,
        mem_write: MemoryWrite,
        raw: RawContent,
    ) -> QueryProof:
        t0 = time.monotonic()

        words = raw.content.split()
        distinctive = " ".join(words[10:16]) if len(words) > 16 else " ".join(words[:6])
        query_string = distinctive
        query_derivation = f"Words 10-16 from source content as distinctive phrase"

        all_memories = []
        for line in self._memories_path.read_text().strip().split("\n"):
            all_memories.append(json.loads(line))

        query_terms = set(query_string.lower().split())

        def score(entry: dict[str, Any]) -> float:
            text = f"{entry.get('label', '')} {entry.get('content', '')}".lower()
            text_terms = set(text.split())
            overlap = len(query_terms & text_terms)
            return overlap / max(len(query_terms), 1)

        scored = [(score(m), m) for m in all_memories]
        scored.sort(key=lambda x: x[0], reverse=True)
        top5 = scored[:5]

        written_ids = (
            set(mem_write.memory_ids_written)
            if mem_write.memory_ids_written
            else {mem_write.new_canonical_memory_entry_id}
        )
        new_rank = None
        for i, (s, m) in enumerate(scored):
            if m.get("memory_id") in written_ids:
                new_rank = i + 1
                break

        dur = round((time.monotonic() - t0) * 1000, 2)

        return QueryProof(
            signal_id=signal.signal_id,
            query_string=query_string,
            query_derivation=query_derivation,
            retrieval_method="term_overlap_scoring",
            retrieved_entries=[
                {
                    "rank": i + 1,
                    "memory_id": m.get("memory_id"),
                    "label": m.get("label", "")[:80],
                    "score": round(s, 4),
                    "is_new_entry": m.get("memory_id") in written_ids,
                    "authority_tier": get_authority_tier(m),
                }
                for i, (s, m) in enumerate(top5)
            ],
            new_entry_appears_in_results=new_rank is not None and new_rank <= 5,
            new_entry_rank=new_rank,
            total_entries_searched=len(all_memories),
            query_duration_ms=dur,
        )

    def _write_proofs(self, result: IngestionResult) -> None:
        """Write proof artifacts to proof_dir."""
        if self._proof_dir is None:
            return
        self._proof_dir.mkdir(parents=True, exist_ok=True)

        def _write(name: str, data: Any) -> None:
            path = self._proof_dir / name
            if isinstance(data, str):
                path.write_text(data)
            else:
                path.write_text(json.dumps(data, indent=2, default=str))

        if result.signal:
            _write("01_perceive_signal.json", result.signal.to_dict())
        if result.interpretation:
            _write("02_interpretation.json", result.interpretation.to_dict())
        if result.decomposition:
            decomp_dict = result.decomposition.to_dict()
            decomp_dict["signal_id"] = getattr(result.decomposition, "_signal_id", "")
            decomp_dict["decompose_duration_ms"] = getattr(result.decomposition, "_duration_ms", 0)
            decomp_dict["counts"] = getattr(result.decomposition, "_counts", {})
            decomp_dict["entry_point_invoked"] = {
                "module": "runtime.ingestion.orchestrator",
                "function": "GenericIngestionOrchestrator._decompose",
            }
            _write("03_decomposition.json", decomp_dict)
        if result.projections:
            _write(
                "03b_bridge_projections.json",
                [p.to_dict() for p in result.projections],
            )
        if result.world_update:
            _write("04_world_update.json", result.world_update.to_dict())
        if result.memory_write:
            _write("05_memory_write.json", result.memory_write.to_dict())
        if result.promotion_receipts:
            _write("05_promotion_receipts.json", [r.to_dict() for r in result.promotion_receipts])
        elif result.promotion_receipt:
            _write("05_promotion_receipt.json", result.promotion_receipt.to_dict())
        if result.query_proof:
            _write("06_query_proof.json", result.query_proof.to_dict())
