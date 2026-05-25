"""Understanding Bridge — wires the understanding layer into the execution pipeline.

Steps 3-8 of the 27-step canonical spine:
  3. Interpretation (observe → pattern → decompose → hypothesize → uncertainty)
  4. Decomposition (primitives extraction)
  5. Domain Mapping (business/creator/life bridge projections)
  6. Law Kernel check (14 enacted laws)
  7. Reality Model retrieval (canonical patterns + instance observations)

Non-blocking: if any step fails, the pipeline continues with whatever
context was assembled. Deterministic-first — no LLM calls in this path.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from substrate.ontology.laws import LawRegistry
from substrate.reality_model.canonical import CanonicalRealityModel
from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
from substrate.understanding.interpretation.interpretation_engine_v1 import (
    InterpretationEngineV1,
    InterpretationInput,
    InterpretationResult,
)
from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
)
from substrate.understanding.breadth_expansion import BreadthExpansionEngine, BreadthResult
from substrate.understanding.domains.contract import DomainProjection
from substrate.understanding.domains.registry import default_registry as domain_registry

logger = logging.getLogger(__name__)


@dataclass
class UnderstandingContext:
    """Enrichment context produced by the understanding pipeline."""

    interpretation: InterpretationResult | None = None
    decomposition: DecompositionResult | None = None
    domain_projections: list[DomainProjection] = field(default_factory=list)
    law_violations: list[str] = field(default_factory=list)
    law_context: dict[str, Any] = field(default_factory=dict)
    breadth: BreadthResult | None = None
    canonical_patterns: list[dict[str, Any]] = field(default_factory=list)
    instance_observations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    breadth_domains: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_interpretation": self.interpretation is not None,
            "has_decomposition": self.decomposition is not None,
            "domain_projection_count": len(self.domain_projections),
            "breadth": self.breadth.to_dict() if self.breadth else None,
            "breadth_domains": self.breadth_domains,
            "law_violations": self.law_violations,
            "canonical_pattern_count": len(self.canonical_patterns),
            "instance_observation_count": len(self.instance_observations),
            "confidence": self.confidence,
            "errors": self.errors,
        }


class UnderstandingBridge:
    """Runs the understanding pipeline (steps 3-8) and returns enrichment context.

    Fault-tolerant: each step is wrapped in try/except so a failure in
    interpretation doesn't prevent execution.
    """

    def __init__(
        self,
        law_registry: LawRegistry | None = None,
        canonical_model: CanonicalRealityModel | None = None,
        instance_model: InstanceRealityModel | None = None,
    ) -> None:
        self._interpreter = InterpretationEngineV1()
        self._breadth = BreadthExpansionEngine()
        self._law_registry = law_registry or LawRegistry()
        self._canonical = canonical_model or CanonicalRealityModel()
        self._instance = instance_model or InstanceRealityModel(
            user_id="default", org_id="default"
        )
        self._ensure_domain_bridges()

    def _ensure_domain_bridges(self) -> None:
        if not domain_registry.get_all():
            try:
                import substrate.understanding.domains.business  # noqa: F401
                import substrate.understanding.domains.creator  # noqa: F401
                import substrate.understanding.domains.life  # noqa: F401
            except Exception as e:
                logger.debug("domain bridge import: %s", e)

    def process(
        self,
        content: str,
        signal_id: str = "",
        trace_id: str = "",
        pipeline_context: dict[str, Any] | None = None,
    ) -> UnderstandingContext:
        ctx = UnderstandingContext()
        pipeline_context = pipeline_context or {}

        # Step 3: Interpretation
        try:
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            interp_input = InterpretationInput(
                input_id=signal_id or str(uuid4()),
                source_content=content,
                source_content_hash=content_hash,
                source_trace_id=trace_id,
            )
            ctx.interpretation = self._interpreter.interpret(interp_input)
            ctx.confidence = (
                ctx.interpretation.confidence_envelope.overall_confidence
                if ctx.interpretation.confidence_envelope
                else 0.0
            )
        except Exception as e:
            ctx.errors.append(f"interpretation: {e}")
            logger.warning("interpretation failed (non-blocking): %s", e)

        # Step 4: Decomposition (extracted from interpretation result)
        if ctx.interpretation and ctx.interpretation.decomposition:
            ctx.decomposition = ctx.interpretation.decomposition

        # Step 5: Domain Mapping
        observations = (
            ctx.interpretation.observations if ctx.interpretation else []
        )
        try:
            bridges = domain_registry.get_all()
            for obs in observations:
                for bridge in bridges:
                    try:
                        projection = bridge.bridge(obs)
                        if projection:
                            ctx.domain_projections.append(projection)
                    except Exception:
                        pass
        except Exception as e:
            ctx.errors.append(f"domain_mapping: {e}")
            logger.warning("domain mapping failed (non-blocking): %s", e)

        # Step 5b: Breadth Expansion (cross-domain signal amplification)
        try:
            existing = [p.domain_id for p in ctx.domain_projections]
            ctx.breadth = self._breadth.expand(content, existing_domains=existing)
            ctx.breadth_domains = ctx.breadth.primary_domains + [
                e.domain for e in ctx.breadth.expanded_domains
            ]
        except Exception as e:
            ctx.errors.append(f"breadth_expansion: {e}")
            logger.warning("breadth expansion failed (non-blocking): %s", e)

        # Step 6: Law Kernel check
        try:
            law_ctx = {
                "routed_through_control_plane": True,
                "executed_through_spine": True,
                "has_governance_verdict": pipeline_context.get(
                    "has_governance_verdict", False
                ),
                "uses_typed_contract": True,
                "writes_through_memory_system": True,
                "has_environment_declaration": pipeline_context.get(
                    "has_environment_declaration", True
                ),
                "has_trace": True,
                "has_deterministic_fallback": True,
                "uses_adapter_boundary": pipeline_context.get(
                    "uses_adapter_boundary", True
                ),
                "entities_separated": True,
                "mastery_verified": pipeline_context.get("mastery_verified", False),
                "entered_through_signal": True,
                "has_confidence_score": ctx.confidence > 0,
            }
            ctx.law_context = law_ctx
            ctx.law_violations = self._law_registry.hard_violations(law_ctx)
        except Exception as e:
            ctx.errors.append(f"law_check: {e}")
            logger.warning("law check failed (non-blocking): %s", e)

        # Step 7: Reality Model retrieval
        try:
            keywords = [obs.label for obs in observations[:5]]
            search_term = " ".join(keywords) if keywords else content[:100]

            for pattern in self._canonical.all()[:10]:
                ctx.canonical_patterns.append(
                    {
                        "name": pattern.name,
                        "domain": pattern.domain,
                        "confidence": pattern.confidence,
                    }
                )

            for obs in self._instance.query(search_term, limit=10):
                ctx.instance_observations.append(
                    {
                        "content": obs.content[:200],
                        "domain": obs.domain,
                        "confidence": obs.confidence,
                    }
                )
        except Exception as e:
            ctx.errors.append(f"reality_model: {e}")
            logger.warning("reality model retrieval failed (non-blocking): %s", e)

        return ctx

    def record_outcome(
        self,
        content: str,
        outcome_type: str,
        signal_id: str = "",
        trace_id: str = "",
        domain: str = "execution",
    ) -> None:
        """Record an execution outcome as an instance observation (step 27 partial)."""
        try:
            from uuid import UUID

            observation = InstanceObservation(
                content=f"{outcome_type}: {content[:500]}",
                domain=domain,
                confidence=0.7,
                source_signal_id=UUID(signal_id) if signal_id else None,
                source_trace_id=UUID(trace_id) if trace_id else None,
            )
            self._instance.record(observation)
        except Exception as e:
            logger.debug("outcome recording failed: %s", e)
