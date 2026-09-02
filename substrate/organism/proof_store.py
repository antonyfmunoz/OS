"""Proof Store — JSONL persistence for proof packages.

C28 Phase 4.5. Every execution can generate a proof package containing:
files changed, commands run, logs, browser evidence, verification results.
Packages survive restarts and are queryable via API.

Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from substrate.state.runtime_paths import runtime_state_dir, runtime_state_path

logger = logging.getLogger(__name__)

_STORE_PATH = runtime_state_path("organism", "proof_packages.jsonl", create_parent=False)
_EVIDENCE_DIR = runtime_state_dir("organism", create=False) / "proof_evidence"


@dataclass
class ProofStorePackage:
    proof_id: str = field(default_factory=lambda: f"proof-{uuid4().hex[:12]}")
    request_id: str = ""
    execution_id: str = ""
    packet_id: str = ""
    description: str = ""
    status: str = "pending"
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    browser_evidence: list[str] = field(default_factory=list)
    review_notes: str = ""
    reviewed_by: str = ""
    created_at: float = field(default_factory=time.time)
    reviewed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProofStorePackage:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def evidence_dir(self) -> Path:
        return _EVIDENCE_DIR / self.proof_id


class ProofStore:
    """Append-only proof package store with JSONL persistence."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _STORE_PATH
        self._packages: list[ProofStorePackage] = []
        self._by_id: dict[str, ProofStorePackage] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            for line in self._path.read_text().strip().splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    pkg = ProofStorePackage.from_dict(row)
                    self._packages.append(pkg)
                    self._by_id[pkg.proof_id] = pkg
                except (json.JSONDecodeError, TypeError):
                    continue
            logger.info("Loaded %d proof packages", len(self._packages))
        except Exception as exc:
            logger.warning("Failed to load proof store: %s", exc)

    def _append(self, pkg: ProofStorePackage) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as f:
                f.write(json.dumps(pkg.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist proof package: %s", exc)

    def create(
        self,
        request_id: str = "",
        execution_id: str = "",
        packet_id: str = "",
        description: str = "",
        files_changed: list[str] | None = None,
        commands_run: list[str] | None = None,
        logs: list[str] | None = None,
        verification_results: list[dict[str, Any]] | None = None,
    ) -> ProofStorePackage:
        pkg = ProofStorePackage(
            request_id=request_id,
            execution_id=execution_id,
            packet_id=packet_id,
            description=description,
            files_changed=files_changed or [],
            commands_run=commands_run or [],
            logs=logs or [],
            verification_results=verification_results or [],
        )
        self._packages.append(pkg)
        self._by_id[pkg.proof_id] = pkg
        self._append(pkg)
        pkg.evidence_dir.mkdir(parents=True, exist_ok=True)
        return pkg

    def get(self, proof_id: str) -> ProofStorePackage | None:
        return self._by_id.get(proof_id)

    def approve(
        self, proof_id: str, notes: str = "", reviewer: str = "operator"
    ) -> ProofStorePackage | None:
        pkg = self._by_id.get(proof_id)
        if pkg is None:
            return None
        pkg.status = "approved"
        pkg.review_notes = notes
        pkg.reviewed_by = reviewer
        pkg.reviewed_at = time.time()
        self._append(pkg)
        return pkg

    def reject(
        self, proof_id: str, notes: str = "", reviewer: str = "operator"
    ) -> ProofStorePackage | None:
        pkg = self._by_id.get(proof_id)
        if pkg is None:
            return None
        pkg.status = "rejected"
        pkg.review_notes = notes
        pkg.reviewed_by = reviewer
        pkg.reviewed_at = time.time()
        self._append(pkg)
        return pkg

    def query(
        self,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProofStorePackage]:
        filtered = self._packages
        if status:
            filtered = [p for p in filtered if p.status == status]
        filtered.sort(key=lambda p: p.created_at, reverse=True)
        return filtered[offset : offset + limit]

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for pkg in self._packages:
            by_status[pkg.status] = by_status.get(pkg.status, 0) + 1
        return {
            "total": len(self._packages),
            "by_status": by_status,
        }


_store_instance: ProofStore | None = None


def get_proof_store() -> ProofStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = ProofStore()
    return _store_instance


# Compatibility for legacy callers of this JSONL proof-store facade. The
# canonical ProofPackage type lives in substrate.organism.proof_runtime.
ProofPackage = ProofStorePackage
