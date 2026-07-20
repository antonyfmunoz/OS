"""Proof Runtime — complete proof packages per execution.

Produces ProofPackage records with before-state, action, after-state,
and evidence for every governed execution. Reuses existing ProofGenerator
for governance/execution proofs. Adds before/after state diff.

ProofRuntime is the authority on proof packages. It persists them
in-memory with bounded history.

Gate 3 — Governed Work Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ProofEvidence:
    """A single piece of evidence within a proof package."""

    evidence_type: str = ""
    description: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "description": self.description,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class ProofPackage:
    """Complete proof for one execution — before/action/after/evidence."""

    proof_id: str = field(default_factory=lambda: f"proof-{uuid4().hex[:12]}")
    work_id: str = ""
    before_state: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    evidence: list[ProofEvidence] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    operator: str = "operator"
    governance_proofs: list[dict[str, Any]] = field(default_factory=list)
    execution_duration_ms: float = 0.0
    outcome: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "work_id": self.work_id,
            "before_state": self.before_state,
            "action": self.action,
            "after_state": self.after_state,
            "evidence": [e.to_dict() for e in self.evidence],
            "timestamp": self.timestamp,
            "operator": self.operator,
            "governance_proofs": self.governance_proofs,
            "execution_duration_ms": self.execution_duration_ms,
            "outcome": self.outcome,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Before-state snapshots (pending capture_after)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class _PendingSnapshot:
    snapshot_id: str = ""
    work_id: str = ""
    before_state: dict[str, Any] = field(default_factory=dict)
    captured_at: float = field(default_factory=time.time)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ProofRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProofRuntime:
    """Produces and stores proof packages for governed executions.

    Lifecycle:
      1. capture_before(work_id) — snapshot current state, returns snapshot_id
      2. [execution happens]
      3. capture_after(work_id, snapshot_id, action, outcome) — builds ProofPackage
      4. package_for(work_id) — retrieve proof for a given work item

    Persistence: JSONL file at <runtime-state>/organism/proof_packages.jsonl.
    """

    _MAX_HISTORY = 200

    def __init__(self, store_path: str | None = None) -> None:
        self._pending: dict[str, _PendingSnapshot] = {}
        self._packages: dict[str, ProofPackage] = {}
        self._history: deque[str] = deque(maxlen=self._MAX_HISTORY)
        self._by_work_id: dict[str, str] = {}

        if store_path is None:
            from substrate.state.runtime_paths import runtime_state_path

            store_path = str(runtime_state_path("organism", "proof_packages.jsonl"))
        self._store_path = store_path
        self._load_from_disk()

    def capture_before(self, work_id: str, state: dict[str, Any] | None = None) -> str:
        """Capture before-state snapshot. Returns snapshot_id."""
        snapshot_id = f"snap-{uuid4().hex[:12]}"

        before_state = state if state is not None else self._collect_state()

        self._pending[snapshot_id] = _PendingSnapshot(
            snapshot_id=snapshot_id,
            work_id=work_id,
            before_state=before_state,
        )
        return snapshot_id

    def capture_after(
        self,
        work_id: str,
        snapshot_id: str,
        action: dict[str, Any] | None = None,
        outcome: str = "success",
        after_state: dict[str, Any] | None = None,
        governance_proofs: list[dict[str, Any]] | None = None,
        operator: str = "operator",
        duration_ms: float = 0.0,
    ) -> ProofPackage:
        """Build complete ProofPackage from before-snapshot + execution results."""
        pending = self._pending.pop(snapshot_id, None)

        before = pending.before_state if pending else {}
        after = after_state if after_state is not None else self._collect_state()

        diff = self._compute_diff(before, after)

        package = ProofPackage(
            work_id=work_id,
            before_state=before,
            action=action or {},
            after_state=after,
            evidence=[
                ProofEvidence(
                    evidence_type="state_diff",
                    description="Before/after state difference",
                    data=diff,
                ),
            ],
            operator=operator,
            governance_proofs=governance_proofs or [],
            execution_duration_ms=duration_ms,
            outcome=outcome,
        )

        self._packages[package.proof_id] = package
        self._by_work_id[work_id] = package.proof_id
        self._history.append(package.proof_id)
        self._persist_package(package)

        return package

    def create_direct(
        self,
        work_id: str,
        action: dict[str, Any],
        outcome: str = "success",
        operator: str = "operator",
    ) -> ProofPackage:
        """Create a proof package without before/after capture."""
        package = ProofPackage(
            work_id=work_id,
            action=action,
            outcome=outcome,
            operator=operator,
            evidence=[
                ProofEvidence(
                    evidence_type="action_record",
                    description="Action performed without state capture",
                    data=action,
                ),
            ],
        )
        self._packages[package.proof_id] = package
        self._by_work_id[work_id] = package.proof_id
        self._history.append(package.proof_id)
        self._persist_package(package)
        return package

    def package_for(self, work_id: str) -> ProofPackage | None:
        proof_id = self._by_work_id.get(work_id)
        if proof_id is None:
            return None
        return self._packages.get(proof_id)

    def get(self, proof_id: str) -> ProofPackage | None:
        return self._packages.get(proof_id)

    def recent(self, limit: int = 20) -> list[ProofPackage]:
        result: list[ProofPackage] = []
        for proof_id in reversed(self._history):
            pkg = self._packages.get(proof_id)
            if pkg:
                result.append(pkg)
            if len(result) >= limit:
                break
        return result

    def all_proofs(self) -> list[ProofPackage]:
        return list(self._packages.values())

    # ── Persistence ────────────────────────────────────────────

    def _load_from_disk(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        pkg = ProofPackage(
                            proof_id=d.get("proof_id", ""),
                            work_id=d.get("work_id", ""),
                            before_state=d.get("before_state", {}),
                            action=d.get("action", {}),
                            after_state=d.get("after_state", {}),
                            evidence=[ProofEvidence(**e) for e in d.get("evidence", [])],
                            timestamp=d.get("timestamp", 0.0),
                            operator=d.get("operator", "operator"),
                            governance_proofs=d.get("governance_proofs", []),
                            execution_duration_ms=d.get("execution_duration_ms", 0.0),
                            outcome=d.get("outcome", ""),
                        )
                        self._packages[pkg.proof_id] = pkg
                        self._by_work_id[pkg.work_id] = pkg.proof_id
                        self._history.append(pkg.proof_id)
                    except (json.JSONDecodeError, TypeError, KeyError) as exc:
                        logger.debug("skip malformed proof line: %s", exc)
        except OSError as exc:
            logger.debug("cannot read proof packages: %s", exc)

    def _persist_package(self, package: ProofPackage) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        try:
            with open(self._store_path, "a") as f:
                f.write(json.dumps(package.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("cannot persist proof package: %s", exc)

    # ── Internal helpers ─────────────────────────────────────────

    def _collect_state(self) -> dict[str, Any]:
        """Collect current organism state for snapshot."""
        state: dict[str, Any] = {"captured_at": time.time()}
        try:
            from substrate.organism.work_graph import WorkGraph

            graph = WorkGraph()
            snap = graph.snapshot()
            state["work_graph"] = {
                "total": snap.total,
                "active": snap.active,
                "blocked": snap.blocked,
                "completed": snap.completed,
                "failed": snap.failed,
            }
        except Exception:
            state["work_graph"] = {"error": "unavailable"}
        return state

    @staticmethod
    def _compute_diff(
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute simple key-level diff between two state dicts."""
        diff: dict[str, Any] = {}
        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            bval = before.get(key)
            aval = after.get(key)
            if bval != aval:
                diff[key] = {"before": bval, "after": aval}
        return diff
