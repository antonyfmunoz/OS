"""Runtime Resume Packet Generator v1.

Generates resumable context packets from continuity state,
open loops, recent outcomes, and relevant canonical memories.

UMH substrate subsystem. Phase 96.8BN.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_cognition_contracts_v1 import (
    RuntimeResumePacket,
    _deterministic_id,
)
from .runtime_continuity_store_v1 import RuntimeContinuityStore
from .open_loop_registry_v1 import OpenLoopRegistry


class ResumePacketGenerator:
    """Generates resume packets from current continuity state."""

    def __init__(
        self,
        continuity_store: RuntimeContinuityStore | None = None,
        loop_registry: OpenLoopRegistry | None = None,
        memory_store_dir: str | Path = "data/runtime/reconciliation_memory_store",
    ):
        self.continuity_store = continuity_store or RuntimeContinuityStore()
        self.loop_registry = loop_registry or OpenLoopRegistry()
        self.memory_store_dir = Path(memory_store_dir)

    def generate(
        self,
        session_id: str = "",
        active_goals: list[str] | None = None,
        environment_state: dict[str, Any] | None = None,
        suggested_next_actions: list[str] | None = None,
    ) -> RuntimeResumePacket:
        """Generate a resume packet from current system state."""
        snapshot = self.continuity_store.load_latest_snapshot()
        recent_outcomes = self.continuity_store.load_recent_outcomes(limit=10)
        recent_traces = self.continuity_store.load_recent_traces(limit=10)
        open_loops = self.loop_registry.get_open_loops()

        unresolved_blockers = [
            loop["description"]
            for loop in open_loops
            if loop.get("loop_type")
            in ("failed_execution", "pending_governance", "unresolved_contradiction")
        ]

        pending_approvals = [
            loop["description"]
            for loop in open_loops
            if loop.get("loop_type") == "pending_governance"
        ]

        relevant_memories = self._load_recent_memories(limit=10)

        env_state = environment_state or self._detect_environment()

        summary = self.continuity_store.load_all_summaries()
        latest_summary = summary[-1] if summary else {}

        packet = RuntimeResumePacket(
            continuity_state=snapshot or {},
            active_goals=active_goals or (snapshot or {}).get("active_goals", []),
            unresolved_blockers=unresolved_blockers,
            recent_outcomes=[o for o in recent_outcomes],
            pending_approvals=pending_approvals,
            relevant_memories=relevant_memories,
            recent_traces=[t for t in recent_traces],
            open_loops=open_loops,
            environment_state=env_state,
            suggested_next_actions=suggested_next_actions or [],
            session_summary=latest_summary,
        )

        self.continuity_store.save_resume_packet(packet.to_dict())
        return packet

    def _load_recent_memories(self, limit: int = 10) -> list[dict[str, Any]]:
        """Load recent memories from the canonical store."""
        memories_path = self.memory_store_dir / "memories.jsonl"
        if not memories_path.exists():
            return []
        memories = []
        with open(memories_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    memories.append(json.loads(line))
        return memories[-limit:]

    def _detect_environment(self) -> dict[str, Any]:
        """Detect current environment state."""
        import os
        import platform

        return {
            "hostname": platform.node(),
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "working_dir": os.getcwd(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
