"""Coherence Gate — fail-closed execution guard.

No work packet executes without passing the coherence gate.
The gate verifies that the packet has a valid CoherenceEnvelope
proving it descended from the canonical UMH spine.

Fail-closed: if the gate cannot confirm coherence, execution
is blocked with BLOCK_EXECUTION: INCOMPLETE_CANONICAL_SPINE.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from typing import Any

from .spine_coherence_validator import (
    validate_coherence_envelope,
    validate_coherence_envelope_dict,
)
from .spine_lineage_contracts import (
    CoherenceEnvelope,
    CoherenceStatus,
    CoherenceValidationResult,
)


class CoherenceGateBlocked(Exception):
    """Raised when the coherence gate blocks execution."""

    def __init__(self, result: CoherenceValidationResult):
        self.result = result
        super().__init__(f"BLOCK_EXECUTION: {result.status} — errors: {result.errors}")


def evaluate_coherence_before_execution(
    packet: dict[str, Any],
) -> CoherenceValidationResult:
    """Evaluate coherence envelope from a work packet dict.

    Returns a CoherenceValidationResult. Does not raise.
    """
    envelope_dict = packet.get("coherence_envelope")
    if not envelope_dict:
        result = CoherenceValidationResult()
        result.errors.append("MISSING_COHERENCE_ENVELOPE: packet has no coherence_envelope")
        result.status = CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value
        return result

    return validate_coherence_envelope_dict(envelope_dict)


def assert_coherent_or_block(
    packet: dict[str, Any],
) -> None:
    """Assert that a packet is coherent or raise CoherenceGateBlocked.

    Call this before any execution. If the packet is not coherent,
    raises CoherenceGateBlocked with full diagnostic.
    """
    result = evaluate_coherence_before_execution(packet)
    if not result.coherent:
        raise CoherenceGateBlocked(result)


def coherence_gate_allows_execution(
    packet: dict[str, Any],
) -> tuple[bool, CoherenceValidationResult]:
    """Check if the coherence gate allows execution.

    Returns (allowed, result) tuple. Does not raise.
    """
    result = evaluate_coherence_before_execution(packet)
    return result.coherent, result
