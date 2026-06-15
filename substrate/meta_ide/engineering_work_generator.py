"""Engineering Work Generator — bridge from plans to governed work packets.

Converts approved engineering plans into WorkPackets via the existing
WorkPacketEngine and enqueues them via the existing UniversalWorkQueue.
No new queue, no new packet types, no new execution authority.

Phase 22. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.meta_ide.engineering_intent import (
    EngineeringPlan,
    EngineeringPlanReceipt,
    EngineeringTask,
)

logger = logging.getLogger(__name__)


class EngineeringWorkGenerator:
    """Converts engineering plans into governed work packets.

    Composes with existing WorkPacketEngine and UniversalWorkQueue.
    Does not create new packet types or queues.
    """

    def __init__(
        self,
        work_packet_engine: Any | None = None,
        work_queue: Any | None = None,
    ) -> None:
        self._engine = work_packet_engine
        self._queue = work_queue

    def _get_engine(self) -> Any:
        if self._engine is None:
            from substrate.organism.work_packet_engine import WorkPacketEngine

            self._engine = WorkPacketEngine()
        return self._engine

    def _get_queue(self) -> Any:
        if self._queue is None:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            self._queue = UniversalWorkQueue()
        return self._queue

    def generate_packets(self, plan: EngineeringPlan) -> EngineeringPlanReceipt:
        """Convert approved plan tasks into work packets.

        Each EngineeringTask becomes a WorkPacket created via the existing
        WorkPacketEngine.create_packet_from_intent() and enqueued via
        UniversalWorkQueue.ingest_work_packet().
        """
        if plan.status not in ("draft", "approved"):
            return EngineeringPlanReceipt(
                plan_id=plan.plan_id,
                status="failed",
            )

        engine = self._get_engine()
        queue = self._get_queue()

        packet_ids: list[str] = []
        task_to_packet: dict[str, str] = {}
        first_packet_id: str = ""

        roadmap_phase = plan.roadmap_context.get("current_phase", "")

        for task in plan.tasks:
            try:
                packet = engine.create_packet_from_intent(
                    user_intent=task.description,
                    desired_end_state=f"{task.title} complete",
                    constraints=plan.intent.constraints,
                    source_type="engineering_plan",
                    source_id=plan.plan_id,
                )

                if not first_packet_id:
                    first_packet_id = packet.packet_id
                else:
                    packet.parent_packet_id = first_packet_id

                if roadmap_phase:
                    packet.linked_roadmap_phase = roadmap_phase

                task_deps = task.dependencies
                packet_deps = [
                    task_to_packet[dep_id] for dep_id in task_deps if dep_id in task_to_packet
                ]
                if packet_deps:
                    packet.dependencies = packet_deps

                queue.ingest_work_packet(packet)

                packet_ids.append(packet.packet_id)
                task_to_packet[task.task_id] = packet.packet_id

            except Exception as exc:
                logger.warning(
                    "engineering_work_generator: failed to create packet for task %s: %s",
                    task.task_id,
                    exc,
                )

        plan.status = "approved"

        return EngineeringPlanReceipt(
            plan_id=plan.plan_id,
            work_packet_ids=packet_ids,
            status="packets_generated" if packet_ids else "failed",
        )
