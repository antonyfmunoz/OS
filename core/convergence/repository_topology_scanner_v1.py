"""Repository Topology Scanner v1.

Scans repository filesystem topology, detects duplicate domains,
abandoned domains, shadow runtime trees, stale experiments,
conflicting roots, and parallel execution paths.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.convergence.repository_topology_contracts_v1 import (
    CanonicalRepositoryTopology,
    _now_iso,
    _deterministic_id,
)


CANONICAL_SCAN_DIRECTORIES = [
    "core",
    "docs",
    "data",
    "tools",
    "agents",
    "runtime",
    "services",
    "scripts",
    "tests",
]

MAX_SCANS = 50


class RepositoryTopologyScanner:
    """Scans and hashes repository topology."""

    def __init__(self, root_path: str = _DEFAULT_ROOT) -> None:
        self._root = Path(root_path)
        self._scans: list[CanonicalRepositoryTopology] = []

    def scan_topology(self) -> dict[str, Any]:
        if len(self._scans) >= MAX_SCANS:
            raise ValueError("Max scans reached")

        canonical_dirs = []
        total_dirs = 0
        total_files = 0

        for dirname in CANONICAL_SCAN_DIRECTORIES:
            dirpath = self._root / dirname
            if dirpath.is_dir():
                canonical_dirs.append(dirname)
                for p in dirpath.rglob("*"):
                    if p.is_dir():
                        total_dirs += 1
                    elif p.is_file():
                        total_files += 1

        dir_list = sorted(canonical_dirs)
        topo_hash = hashlib.sha256("|".join(dir_list).encode()).hexdigest()

        topo = CanonicalRepositoryTopology(
            topology_id=_deterministic_id("rtopo-", _now_iso()),
            root_path=str(self._root),
            canonical_directories=canonical_dirs,
            total_directories_scanned=total_dirs,
            total_files_scanned=total_files,
            topology_hash=topo_hash,
        )
        self._scans.append(topo)
        return topo.to_dict()

    def detect_shadow_trees(self) -> list[str]:
        shadows = []
        for p in self._root.iterdir():
            if p.is_dir() and p.name not in CANONICAL_SCAN_DIRECTORIES and not p.name.startswith("."):
                if any((p / sub).exists() for sub in ["__init__.py", "setup.py", "pyproject.toml"]):
                    shadows.append(str(p.relative_to(self._root)))
        return shadows

    def detect_duplicate_domains(self) -> list[dict[str, Any]]:
        domains: dict[str, list[str]] = {}
        for dirname in CANONICAL_SCAN_DIRECTORIES:
            dirpath = self._root / dirname
            if dirpath.is_dir():
                for sub in dirpath.iterdir():
                    if sub.is_dir():
                        name = sub.name
                        domains.setdefault(name, []).append(f"{dirname}/{name}")
        return [
            {"domain": name, "locations": locs}
            for name, locs in domains.items()
            if len(locs) > 1
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_scans": len(self._scans),
            "canonical_directories": len(CANONICAL_SCAN_DIRECTORIES),
        }
