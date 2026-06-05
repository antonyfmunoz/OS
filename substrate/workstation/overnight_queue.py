"""Overnight safe-work queue scaffold — thin MVP for queuing permitted work.

Queues low-risk work for overnight execution, pauses high-risk work,
creates approval objects for blocked work, and traces all decisions.
Does not implement full autonomous execution — keeps everything as
queued/dry-run/approval-only.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OvernightWorkItem:
    """A work item queued for overnight processing."""

    item_id: str = ""
    work_packet_id: str = ""
    title: str = ""
    risk_level: str = ""  # LOW, MEDIUM, HIGH, CRITICAL
    status: str = "queued"  # queued, approved, paused, blocked, completed, skipped
    reason: str = ""
    queued_at: str = ""
    decided_at: str = ""
    approval_required: bool = False
    approval_id: str = ""

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = f"owi_{uuid.uuid4().hex[:12]}"
        if not self.queued_at:
            self.queued_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OvernightWorkItem:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class OvernightQueue:
    """Manages the overnight safe-work queue.

    Risk gating:
    - LOW risk: queued for autonomous execution
    - MEDIUM risk: queued but requires approval before execution
    - HIGH/CRITICAL: paused, not queued, approval object created
    """

    SAFE_RISK_LEVELS = frozenset({"LOW"})
    APPROVAL_RISK_LEVELS = frozenset({"MEDIUM"})
    BLOCKED_RISK_LEVELS = frozenset({"HIGH", "CRITICAL"})

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            state_dir = os.path.join(root, "data", "umh", "workstation_state")
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._queue_path = self._dir / "overnight_queue.jsonl"
        self._items: list[OvernightWorkItem] = []
        self._load()

    def queue_work(
        self,
        work_packet_id: str,
        title: str,
        risk_level: str,
        reason: str = "",
    ) -> OvernightWorkItem:
        """Queue a work item, applying risk gating."""
        risk_upper = risk_level.upper()

        if risk_upper in self.BLOCKED_RISK_LEVELS:
            item = OvernightWorkItem(
                work_packet_id=work_packet_id,
                title=title,
                risk_level=risk_upper,
                status="blocked",
                reason=f"Risk level {risk_upper} blocked for overnight. {reason}".strip(),
                approval_required=True,
                approval_id=f"appr_{uuid.uuid4().hex[:12]}",
            )
            item.decided_at = datetime.now(timezone.utc).isoformat()
        elif risk_upper in self.APPROVAL_RISK_LEVELS:
            item = OvernightWorkItem(
                work_packet_id=work_packet_id,
                title=title,
                risk_level=risk_upper,
                status="queued",
                reason=f"MEDIUM risk queued with approval gate. {reason}".strip(),
                approval_required=True,
                approval_id=f"appr_{uuid.uuid4().hex[:12]}",
            )
        else:
            item = OvernightWorkItem(
                work_packet_id=work_packet_id,
                title=title,
                risk_level=risk_upper,
                status="queued",
                reason=f"LOW risk, safe for overnight. {reason}".strip(),
                approval_required=False,
            )

        self._items.append(item)
        self._persist(item)

        logger.info(
            "Overnight queue: %s (%s) -> %s",
            title, risk_upper, item.status,
        )
        return item

    def get_queue(self, status: str | None = None) -> list[OvernightWorkItem]:
        """Return queued items, optionally filtered by status."""
        if status:
            return [i for i in self._items if i.status == status]
        return list(self._items)

    def get_safe_work(self) -> list[OvernightWorkItem]:
        """Return items safe for autonomous execution (queued + no approval needed)."""
        return [
            i for i in self._items
            if i.status == "queued" and not i.approval_required
        ]

    def get_blocked(self) -> list[OvernightWorkItem]:
        """Return blocked items requiring operator action."""
        return [i for i in self._items if i.status == "blocked"]

    def get_pending_approval(self) -> list[OvernightWorkItem]:
        """Return items queued but needing approval."""
        return [i for i in self._items if i.approval_required and i.status == "queued"]

    def approve(self, item_id: str) -> OvernightWorkItem | None:
        """Approve a queued item for execution."""
        for item in self._items:
            if item.item_id == item_id:
                item.approval_required = False
                item.decided_at = datetime.now(timezone.utc).isoformat()
                self._rewrite()
                return item
        return None

    def morning_summary(self) -> dict[str, Any]:
        """Generate a morning summary of overnight queue state."""
        return {
            "total": len(self._items),
            "queued": len([i for i in self._items if i.status == "queued"]),
            "safe_to_run": len(self.get_safe_work()),
            "pending_approval": len(self.get_pending_approval()),
            "blocked": len(self.get_blocked()),
            "completed": len([i for i in self._items if i.status == "completed"]),
            "skipped": len([i for i in self._items if i.status == "skipped"]),
            "items": [i.to_dict() for i in self._items],
        }

    def clear(self) -> None:
        """Clear the queue (for new overnight cycle)."""
        self._items.clear()
        if self._queue_path.exists():
            self._queue_path.unlink()

    def _load(self) -> None:
        if not self._queue_path.exists():
            return
        try:
            with open(self._queue_path, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        self._items.append(OvernightWorkItem.from_dict(json.loads(stripped)))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.debug("Overnight queue load failed: %s", exc)

    def _persist(self, item: OvernightWorkItem) -> None:
        with open(self._queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item.to_dict(), separators=(",", ":"), default=str) + "\n")

    def _rewrite(self) -> None:
        with open(self._queue_path, "w", encoding="utf-8") as f:
            for item in self._items:
                f.write(json.dumps(item.to_dict(), separators=(",", ":"), default=str) + "\n")
