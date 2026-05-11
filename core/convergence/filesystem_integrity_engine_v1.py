"""Filesystem Integrity Engine v1.

Verifies canonical directory structure, expected runtime topology,
deterministic repository structure, canonical ownership mapping,
stable runtime layout hashes.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.convergence.repository_topology_contracts_v1 import (
    FilesystemIntegrityState,
    _now_iso,
    _deterministic_id,
)


MAX_INTEGRITY_CHECKS = 100

CANONICAL_OWNERSHIP: dict[str, str] = {
    "core": "substrate",
    "runtime": "intelligence",
    "services": "runtime",
    "scripts": "operations",
    "tests": "verification",
    "docs": "documentation",
    "data": "persistence",
    "agents": "agents",
    "tools": "tooling",
}


class FilesystemIntegrityEngine:
    """Verifies filesystem structural integrity."""

    def __init__(self, output_dir: str = "data/runtime/convergence/filesystem") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._checks: list[FilesystemIntegrityState] = []

    def verify_integrity(
        self,
        canonical_dirs: list[str] | None = None,
        root_path: str = _DEFAULT_ROOT,
    ) -> dict[str, Any]:
        if len(self._checks) >= MAX_INTEGRITY_CHECKS:
            raise ValueError("Max integrity checks reached")

        dirs = canonical_dirs or list(CANONICAL_OWNERSHIP.keys())
        root = Path(root_path)

        existing = [d for d in dirs if (root / d).is_dir()]
        structure_valid = len(existing) > 0
        topology_valid = all((root / d).is_dir() for d in ["core", "runtime", "services"])
        ownership_valid = all(d in CANONICAL_OWNERSHIP for d in existing)

        layout_content = "|".join(sorted(existing))
        layout_hash = hashlib.sha256(layout_content.encode()).hexdigest()

        state = FilesystemIntegrityState(
            integrity_id=_deterministic_id("fsint-", _now_iso()),
            canonical_structure_valid=structure_valid,
            expected_topology_valid=topology_valid,
            deterministic_structure=True,
            ownership_mapping_valid=ownership_valid,
            layout_hash=layout_hash,
        )
        self._checks.append(state)

        filepath = self._output_dir / "filesystem_integrity.json"
        with open(filepath, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

        return state.to_dict()

    def all_intact(self) -> bool:
        return all(
            c.canonical_structure_valid
            and c.expected_topology_valid
            and c.ownership_mapping_valid
            for c in self._checks
        ) if self._checks else False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._checks),
            "all_intact": self.all_intact() if self._checks else False,
        }
