"""Unified intent receipt — canonical audit trail for every operator interaction.

Every operator intent produces an IntentReceipt regardless of route
(conversation, work_packet, hybrid, observation, approval). The receipt
tracks classification, routing, and cross-references to path-specific
artifacts (work packets, governance decisions, memory writes, etc.).

IntentReceiptStore provides JSONL append-only persistence with query methods.

Phase 18. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DEFAULT_STORE_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "operator", "intent_receipts.jsonl",
)


class ReceiptStatus(str, Enum):
    CREATED = "created"
    ROUTING = "routing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"


@dataclass
class IntentReceipt:
    intent_id: str
    raw_input: str
    route_type: str
    confidence: float

    conversation_id: str | None = None
    work_packet_id: str | None = None
    governance_decision_id: str | None = None
    execution_bundle_id: str | None = None
    memory_write_receipt_id: str | None = None
    reality_update_id: str | None = None
    event_ids: list[str] = field(default_factory=list)

    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    final_status: str = ReceiptStatus.CREATED.value
    error: str | None = None

    extracted_entities: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentReceipt:
        d = dict(d)
        d.setdefault("event_ids", [])
        d.setdefault("extracted_entities", {})
        d.setdefault("reasoning", "")
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class IntentReceiptStore:
    """JSONL append-only store for IntentReceipts."""

    def __init__(self, store_path: str | None = None) -> None:
        self._path = store_path or _DEFAULT_STORE_PATH
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def append(self, receipt: IntentReceipt) -> None:
        with open(self._path, "a") as f:
            f.write(json.dumps(receipt.to_dict(), default=str, separators=(",", ":")) + "\n")

    def load_all(self) -> list[IntentReceipt]:
        if not os.path.exists(self._path):
            return []
        receipts: list[IntentReceipt] = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    receipts.append(IntentReceipt.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.debug("Skipping malformed receipt line: %s", exc)
        return receipts

    def query_recent(self, limit: int = 50) -> list[IntentReceipt]:
        all_receipts = self.load_all()
        all_receipts.sort(key=lambda r: r.created_at, reverse=True)
        return all_receipts[:limit]

    def query_by_status(self, status: str) -> list[IntentReceipt]:
        return [r for r in self.load_all() if r.final_status == status]

    def get(self, intent_id: str) -> IntentReceipt | None:
        for r in self.load_all():
            if r.intent_id == intent_id:
                return r
        return None

    def update(self, receipt: IntentReceipt) -> None:
        """Atomic rewrite — replace matching receipt in store."""
        all_receipts = self.load_all()
        updated = False
        for i, r in enumerate(all_receipts):
            if r.intent_id == receipt.intent_id:
                all_receipts[i] = receipt
                updated = True
                break
        if not updated:
            all_receipts.append(receipt)

        dir_name = os.path.dirname(self._path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                for r in all_receipts:
                    f.write(json.dumps(r.to_dict(), default=str, separators=(",", ":")) + "\n")
            os.replace(tmp_path, self._path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
