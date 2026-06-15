"""Canonical reality write path — governed entry point for non-execution observations.

Accepts a RealityMutation and validates shape, source, and confidence before
writing an InstanceObservation into the existing InstanceRealityModel.

This is PARALLEL to CanonicalWritePath (substrate/memory/canonical_write.py),
which handles execution-domain writes with candidate generation and promotion.
CanonicalRealityWritePath handles non-execution observations (governance
decisions, conversation insights, ad-hoc observations) that do not need
candidate generation or promotion evaluation.

Both converge at InstanceRealityModel.record() — the true canonical storage.

Phase 19. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from substrate.reality_model.reality_mutation import (
    MutationSource,
    RealityMutation,
    RealityMutationReceipt,
)

logger = logging.getLogger(__name__)


def _safe_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


class CanonicalRealityWritePath:
    """Single governed entry point for non-execution reality observations.

    Validates mutation shape, source, and confidence, then delegates to
    InstanceRealityModel.record(). Does NOT call governance (caller's
    responsibility) and does NOT do candidate generation or promotion.
    """

    def __init__(
        self,
        reality_model: Any | None = None,
        event_spine: Any | None = None,
    ) -> None:
        self._reality_model = reality_model
        self._event_spine = event_spine

    def apply_mutation(self, mutation: RealityMutation) -> RealityMutationReceipt:
        rejection = self._validate(mutation)
        if rejection:
            return rejection

        observation_id = self._write_observation(mutation)
        self._emit_event(mutation, observation_id)

        return RealityMutationReceipt(
            mutation_id=mutation.mutation_id,
            observation_id=observation_id,
            accepted=True,
            reason="recorded",
        )

    def _validate(self, mutation: RealityMutation) -> RealityMutationReceipt | None:
        if not mutation.mutation_id:
            return self._reject(mutation, "empty mutation_id")
        if not mutation.content:
            return self._reject(mutation, "empty content")
        if len(mutation.content) > 2000:
            return self._reject(mutation, f"content exceeds 2000 chars ({len(mutation.content)})")
        if not isinstance(mutation.source_system, MutationSource):
            return self._reject(mutation, f"invalid source_system: {mutation.source_system}")
        if not (0.0 <= mutation.confidence <= 1.0):
            return self._reject(mutation, f"confidence out of range: {mutation.confidence}")
        return None

    def _reject(self, mutation: RealityMutation, reason: str) -> RealityMutationReceipt:
        logger.debug("reality_write rejected: %s (mutation=%s)", reason, mutation.mutation_id)
        return RealityMutationReceipt(
            mutation_id=mutation.mutation_id or "unknown",
            observation_id=None,
            accepted=False,
            reason=reason,
        )

    def _write_observation(self, mutation: RealityMutation) -> str | None:
        if self._reality_model is None:
            return None

        try:
            from substrate.reality_model.instance import InstanceObservation

            merged_metadata: dict[str, Any] = {
                "mutation_id": mutation.mutation_id,
                "source_system": mutation.source_system.value,
                "source_id": mutation.source_id,
                **mutation.evidence,
                **mutation.metadata,
            }
            if mutation.governance_context:
                merged_metadata["governance_context"] = mutation.governance_context

            obs = InstanceObservation(
                content=mutation.content,
                domain=mutation.domain,
                confidence=mutation.confidence,
                source_trace_id=_safe_uuid(mutation.source_id),
                tags=mutation.tags + [
                    f"source:{mutation.source_system.value}",
                    f"mutation:{mutation.mutation_type.value}",
                ],
                metadata=merged_metadata,
            )
            obs_uuid = self._reality_model.record(obs)
            return str(obs_uuid)
        except Exception as exc:
            logger.warning("reality_write: observation write failed: %s", exc)
            return None

    def _emit_event(self, mutation: RealityMutation, observation_id: str | None) -> None:
        if self._event_spine is None:
            return

        try:
            from substrate.organism.event_spine import EventDomain
            self._event_spine.emit(
                domain=EventDomain.MEMORY,
                event_type="reality_mutation_applied",
                source="canonical_reality_write",
                data={
                    "mutation_id": mutation.mutation_id,
                    "source_system": mutation.source_system.value,
                    "mutation_type": mutation.mutation_type.value,
                    "domain": mutation.domain,
                    "confidence": mutation.confidence,
                    "observation_id": observation_id,
                },
                correlation_id=mutation.source_id,
            )
        except Exception as exc:
            logger.debug("reality_write: event emission failed: %s", exc)
