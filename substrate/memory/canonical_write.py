"""CanonicalWritePath -- single facade for organism-loop memory writes.

The organism execution loop produces ExecutionBundles. This module is the
one canonical entry point that converts an execution result into a durable
memory candidate, evaluates it for promotion, and -- if promoted -- bridges
the result into the InstanceRealityModel as an observation.

It orchestrates existing writers (MemoryCandidateGenerator, MemoryPromoter,
InstanceRealityModel) without replacing or duplicating them.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from substrate.execution.executor import ExecutionBundle
from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.reality_model.instance import InstanceObservation, InstanceRealityModel
from substrate.types import ExecutionOutcome, ProofStatus

logger = logging.getLogger(__name__)


@dataclass
class MemoryWriteReceipt:
    """Receipt returned after a canonical memory write attempt."""

    receipt_id: str
    candidate_id: str | None
    promoted: bool
    observation_id: str | None  # InstanceRealityModel observation ID if written
    memory_store_entry_id: str | None  # promoted memory entry ID if promoted
    trace_id: str
    work_packet_id: str
    timestamp: str = ""  # ISO UTC

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class CanonicalWritePath:
    """Single canonical memory write facade for the organism loop.

    Accepts an ExecutionBundle and orchestrates:
    1. Memory candidate generation (via MemoryCandidateGenerator)
    2. Promotion evaluation (via MemoryPromoter)
    3. Reality model bridging (via InstanceRealityModel) on promotion
    """

    def __init__(
        self,
        candidate_generator: MemoryCandidateGenerator | None = None,
        promoter: MemoryPromoter | None = None,
        reality_model: InstanceRealityModel | None = None,
    ) -> None:
        self._generator = candidate_generator or MemoryCandidateGenerator()
        self._promoter = promoter or MemoryPromoter()
        self._reality_model = reality_model

    def write_from_execution(
        self,
        execution_bundle: ExecutionBundle,
        trace_id: str,
        input_signal: str,
        work_packet_id: str,
    ) -> MemoryWriteReceipt:
        """Write memory from an execution bundle through the canonical path.

        Steps:
        1. Extract outcome info from the bundle's result and proof
        2. Inject proof evidence into candidate metadata
        3. Generate a MemoryCandidate via the candidate generator
        4. Evaluate promotion via the promoter
        5. If promoted, write an InstanceObservation to the reality model
        6. Return a MemoryWriteReceipt summarising what happened

        Args:
            execution_bundle: Complete execution output (result + proof + governance_proof).
            trace_id: Trace identifier for this execution.
            input_signal: The original input signal text.
            work_packet_id: The work packet that was executed.

        Returns:
            MemoryWriteReceipt documenting what was written and where.
        """
        receipt_id = f"mwr-{uuid4().hex[:12]}"
        result = execution_bundle.result
        proof = execution_bundle.proof

        # Map ExecutionOutcome to the string tokens generate_from_trace expects
        outcome_str = self._map_outcome(result.outcome)

        # Build outcome detail from result data
        outcome_detail = result.error or ""
        if not outcome_detail and result.output_data:
            # Summarise output keys as detail
            keys = list(result.output_data.keys())[:5]
            outcome_detail = f"output keys: {', '.join(keys)}"

        # Build execution_result dict for the generator (matches its expected shape)
        exec_result_dict: dict[str, Any] = {
            "output": result.output_data,
        }

        # Inject proof evidence into execution_result metadata so the
        # candidate generator can carry it forward
        if proof.evidence:
            exec_result_dict["proof_evidence"] = {
                k: str(v)[:200] for k, v in proof.evidence.items()
            }
        if proof.status == ProofStatus.VERIFIED:
            exec_result_dict["proof_verified"] = True

        # Step 1: Generate memory candidate
        candidate = self._generator.generate_from_trace(
            trace_id=trace_id,
            input_signal=input_signal,
            outcome=outcome_str,
            outcome_detail=outcome_detail,
            execution_result=exec_result_dict,
        )

        if candidate is None:
            # generate_from_trace returns None for non-success/partial outcomes
            logger.debug(
                "canonical_write: no candidate generated for trace=%s outcome=%s",
                trace_id,
                outcome_str,
            )
            return MemoryWriteReceipt(
                receipt_id=receipt_id,
                candidate_id=None,
                promoted=False,
                observation_id=None,
                memory_store_entry_id=None,
                trace_id=trace_id,
                work_packet_id=work_packet_id,
            )

        # Enrich candidate metadata with proof evidence before promotion eval
        if proof.evidence:
            candidate.metadata["proof_evidence"] = {
                k: str(v)[:200] for k, v in proof.evidence.items()
            }
        candidate.metadata["work_packet_id"] = work_packet_id

        # Step 2: Evaluate promotion
        eval_result = self._promoter.evaluate(candidate)
        promoted = eval_result.get("promoted", False)
        memory_id = eval_result.get("memory_id")

        # Step 3: If promoted, bridge to reality model
        observation_id: str | None = None
        if promoted and self._reality_model is not None:
            try:
                obs = InstanceObservation(
                    content=candidate.content[:2000],
                    domain="execution",
                    confidence=candidate.confidence,
                    source_trace_id=_safe_uuid(trace_id),
                    tags=candidate.tags + ["memory-promoted", "canonical-write"],
                    metadata={
                        "candidate_id": candidate.candidate_id,
                        "memory_id": memory_id,
                        "work_packet_id": work_packet_id,
                        "proof_status": proof.status.value,
                    },
                )
                obs_uuid = self._reality_model.record(obs)
                observation_id = str(obs_uuid)
            except Exception as exc:
                logger.warning(
                    "canonical_write: reality model write failed for trace=%s: %s",
                    trace_id,
                    exc,
                )

        logger.debug(
            "canonical_write: trace=%s promoted=%s candidate=%s observation=%s",
            trace_id,
            promoted,
            candidate.candidate_id,
            observation_id,
        )

        return MemoryWriteReceipt(
            receipt_id=receipt_id,
            candidate_id=candidate.candidate_id,
            promoted=promoted,
            observation_id=observation_id,
            memory_store_entry_id=memory_id,
            trace_id=trace_id,
            work_packet_id=work_packet_id,
        )

    @staticmethod
    def _map_outcome(outcome: ExecutionOutcome) -> str:
        """Map ExecutionOutcome enum to the string tokens expected by generate_from_trace."""
        if outcome == ExecutionOutcome.SUCCESS:
            return "success"
        if outcome == ExecutionOutcome.PARTIAL_SUCCESS:
            return "partial"
        # All other outcomes (FAILURE, TIMEOUT, BLOCKED, REJECTED) are non-promotable
        return outcome.value


def _safe_uuid(value: str) -> UUID | None:
    """Parse a string as UUID, returning None if it is not valid."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None
