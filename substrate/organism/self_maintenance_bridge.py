"""Self-Regulation Bridge — wires degradation detection to work packet creation.

Part of the Self-Regulation property (P9). Handles the repair pathway:
when OutcomeLearningLoop detects reliability degradation (repeated failures
+ reliability below threshold), this bridge auto-creates a work packet via
WorkPacketEngine with source_type="self_maintenance".

The closed loop:
  Mutation failure → Reliability drops → Signal generated
  → Work Packet auto-created → Proposal in Cockpit
  → Operator approves → UMH repairs itself → Reliability recovers

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def create_degradation_callback(
    work_packet_engine: Any,
) -> Any:
    """Create a callback that bridges degradation signals to work packets.

    Returns a callable suitable for OutcomeLearningLoop.register_degradation_callback().
    """
    from substrate.organism.outcome_learning import LearningSignal

    def _on_degradation(
        action_type: str,
        reliability: float,
        failure_signals: list[LearningSignal],
    ) -> None:
        evidence = [
            {
                "signal_id": s.id,
                "signal_type": s.signal_type.value
                if hasattr(s.signal_type, "value")
                else str(s.signal_type),
                "description": s.description,
                "evidence": s.evidence,
                "generated_at": s.generated_at,
            }
            for s in failure_signals
        ]

        intent = (
            f"Self-maintenance: reliability for '{action_type}' degraded to "
            f"{reliability:.2f} after repeated failures. Investigate root cause "
            f"and restore reliability above 0.90."
        )

        try:
            packet = work_packet_engine.create_packet_from_intent(
                user_intent=intent,
                desired_end_state=f"Reliability for '{action_type}' restored above 0.90",
                constraints=[
                    "Must not break other action types",
                    "Fix must be verified by re-running the failing mutation",
                ],
                source_type="self_maintenance",
                source_id=f"degradation:{action_type}:{int(time.time())}",
                source_evidence=evidence,
            )
            logger.info(
                "Self-maintenance work packet created: %s for action_type=%s (reliability=%.2f)",
                packet.packet_id if hasattr(packet, "packet_id") else "unknown",
                action_type,
                reliability,
            )
        except Exception as exc:
            logger.debug(
                "Failed to create self-maintenance work packet for %s: %s", action_type, exc
            )

    return _on_degradation


def wire_self_maintenance(
    learning_loop: Any,
    work_packet_engine: Any,
    threshold: float = 0.7,
) -> None:
    """Wire degradation detection to work packet creation.

    Call during organism startup to enable self-maintenance.
    """
    callback = create_degradation_callback(work_packet_engine)
    learning_loop.register_degradation_callback(callback, threshold=threshold)
    logger.info("Self-maintenance bridge wired (threshold=%.2f)", threshold)
