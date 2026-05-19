"""Execution queue — ordered, priority-aware queue for work packets."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterator
from uuid import UUID

from services.umh.protocols.work_packet import WorkPacket, WorkPacketPriority, WorkPacketStatus

_PRIORITY_ORDER: dict[WorkPacketPriority, int] = {
    WorkPacketPriority.CRITICAL: 0,
    WorkPacketPriority.HIGH: 1,
    WorkPacketPriority.NORMAL: 2,
    WorkPacketPriority.LOW: 3,
    WorkPacketPriority.BACKGROUND: 4,
}


@dataclass(order=True)
class _QueueEntry:
    sort_key: int
    sequence: int
    packet: WorkPacket = field(compare=False)


class ExecutionQueue:
    """In-memory priority queue for work packets.

    Packets are dequeued in priority order (CRITICAL first).
    Within the same priority, FIFO order is maintained via
    an incrementing sequence counter.
    """

    def __init__(self) -> None:
        self._heap: list[_QueueEntry] = []
        self._seq: int = 0
        self._seen: set[UUID] = set()

    def enqueue(self, packet: WorkPacket) -> bool:
        """Add a packet to the queue. Returns False if already queued."""
        if packet.id in self._seen:
            return False
        priority_val = _PRIORITY_ORDER.get(packet.priority, 2)
        entry = _QueueEntry(sort_key=priority_val, sequence=self._seq, packet=packet)
        heapq.heappush(self._heap, entry)
        self._seen.add(packet.id)
        self._seq += 1
        return True

    def dequeue(self) -> WorkPacket | None:
        """Remove and return the highest-priority packet, or None if empty."""
        while self._heap:
            entry = heapq.heappop(self._heap)
            if entry.packet.id in self._seen:
                self._seen.discard(entry.packet.id)
                return entry.packet
        return None

    def peek(self) -> WorkPacket | None:
        """Return the next packet without removing it."""
        if self._heap:
            return self._heap[0].packet
        return None

    @property
    def size(self) -> int:
        return len(self._seen)

    @property
    def is_empty(self) -> bool:
        return len(self._seen) == 0

    def drain(self) -> Iterator[WorkPacket]:
        """Yield all packets in priority order, emptying the queue."""
        while not self.is_empty:
            packet = self.dequeue()
            if packet is not None:
                yield packet
