"""MutationCatalog — maps HTTP endpoints to MutationSpec names.

Loaded from data/umh/c34/mutation_registry.json (produced by the
C34 census). Provides audit queries: which endpoints are governed,
which are ungoverned, what's the coverage rate.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DEFAULT_CATALOG_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "c34", "mutation_registry.json"
)


@dataclass(frozen=True)
class EndpointEntry:
    file: str
    method: str
    path: str
    mutation_name: str
    risk: str
    blast_radius: str
    reversibility: str
    require_approval: bool
    current_path: str
    governed: bool
    owner: str


class MutationCatalog:
    """Maps HTTP endpoints to MutationSpec names for audit and enforcement."""

    def __init__(self, catalog_path: str = _DEFAULT_CATALOG_PATH) -> None:
        self._entries: list[EndpointEntry] = []
        self._by_key: dict[tuple[str, str], EndpointEntry] = {}
        self._load(catalog_path)

    def _load(self, path: str) -> None:
        if not os.path.isfile(path):
            logger.debug("mutation catalog not found: %s", path)
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for ep in data.get("endpoints", []):
                entry = EndpointEntry(
                    file=ep.get("file", ""),
                    method=ep.get("method", ""),
                    path=ep.get("path", ""),
                    mutation_name=ep.get("mutation_name", ""),
                    risk=ep.get("risk", "low"),
                    blast_radius=ep.get("blast_radius", "LOCAL_RUNTIME"),
                    reversibility=ep.get("reversibility", "FULLY_REVERSIBLE"),
                    require_approval=ep.get("require_approval", False),
                    current_path=ep.get("current_path", "direct_write"),
                    governed=ep.get("governed", False),
                    owner=ep.get("owner", ""),
                )
                self._entries.append(entry)
                self._by_key[(entry.method, entry.path)] = entry
        except Exception as exc:
            logger.error("failed to load mutation catalog: %s", exc)

    def lookup(self, method: str, path: str) -> EndpointEntry | None:
        return self._by_key.get((method, path))

    def all_entries(self) -> list[EndpointEntry]:
        return list(self._entries)

    def governed_entries(self) -> list[EndpointEntry]:
        return [e for e in self._entries if e.governed]

    def ungoverned_entries(self) -> list[EndpointEntry]:
        return [e for e in self._entries if not e.governed]

    def entries_by_file(self, file_path: str) -> list[EndpointEntry]:
        return [e for e in self._entries if e.file == file_path]

    def entries_by_risk(self, risk: str) -> list[EndpointEntry]:
        return [e for e in self._entries if e.risk == risk]

    def coverage_pct(self) -> float:
        if not self._entries:
            return 0.0
        governed = sum(1 for e in self._entries if e.governed)
        return round(governed / len(self._entries) * 100, 1)

    def summary(self) -> dict[str, Any]:
        by_risk: dict[str, int] = {}
        for e in self._entries:
            by_risk[e.risk] = by_risk.get(e.risk, 0) + 1
        return {
            "total": len(self._entries),
            "governed": len(self.governed_entries()),
            "ungoverned": len(self.ungoverned_entries()),
            "coverage_pct": self.coverage_pct(),
            "by_risk": by_risk,
        }
