"""ProofStore — JSON-based proof artifact persistence.

Proof artifacts are evidence that a trace produced a verifiable outcome.
Each proof is a standalone JSON file keyed by proof_id, stored in a
date-partitioned directory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


@dataclass
class ProofArtifact:
    """A proof artifact linked to a trace."""

    proof_id: str
    trace_id: str
    proof_type: str  # e.g. "execution_output", "file_diff", "test_result", "snapshot"
    content: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProofArtifact:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProofStore:
    """Date-partitioned JSON proof artifact store."""

    def __init__(self, store_dir: str | Path = "data/umh/proofs"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _date_dir(self) -> Path:
        d = self.store_dir / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        d.mkdir(parents=True, exist_ok=True)
        return d

    def store_proof(
        self,
        trace_id: str,
        proof_type: str,
        content: dict[str, Any],
        *,
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ProofArtifact:
        """Create and persist a proof artifact. Returns the ProofArtifact."""
        proof_id = _deterministic_id(
            "proof",
            f"{trace_id}:{proof_type}:{json.dumps(content, sort_keys=True)[:256]}",
        )
        proof = ProofArtifact(
            proof_id=proof_id,
            trace_id=trace_id,
            proof_type=proof_type,
            content=content,
            summary=summary,
            metadata=metadata or {},
        )
        out_path = self._date_dir() / f"{proof_id}.json"
        out_path.write_text(json.dumps(proof.to_dict(), indent=2))
        return proof

    def get_proof(self, proof_id: str) -> ProofArtifact | None:
        """Look up a proof artifact by ID across all date partitions."""
        for date_dir in sorted(self.store_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            candidate = date_dir / f"{proof_id}.json"
            if candidate.exists():
                return ProofArtifact.from_dict(json.loads(candidate.read_text()))
        return None

    def proofs_for_trace(self, trace_id: str) -> list[ProofArtifact]:
        """Get all proof artifacts for a given trace ID."""
        results: list[ProofArtifact] = []
        for date_dir in sorted(self.store_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            for f in date_dir.glob("proof-*.json"):
                data = json.loads(f.read_text())
                if data.get("trace_id") == trace_id:
                    results.append(ProofArtifact.from_dict(data))
        return results

    def recent_proofs(self, n: int = 10) -> list[ProofArtifact]:
        """Get the N most recent proof artifacts."""
        all_proofs: list[ProofArtifact] = []
        for date_dir in sorted(self.store_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            for f in sorted(date_dir.glob("proof-*.json"), reverse=True):
                all_proofs.append(ProofArtifact.from_dict(json.loads(f.read_text())))
                if len(all_proofs) >= n:
                    return all_proofs
        return all_proofs
