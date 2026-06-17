"""Project Registry — first-class project entities for UMH.

Projects are the top-level organizational unit in the operator's world.
Each project links to repositories, documents, infrastructure, capabilities,
owner devices, and an optional UMH projection.

Seeded from infra/project_registry.json. Read-only — mutations to project
state route through CanonicalRealityWritePath, not this registry.

Campaign 5.2. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class ProjectDefinition:
    project_id: str
    name: str
    description: str = ""
    projection: str = ""
    repositories: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    infrastructure: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    owner_device_ids: list[str] = field(default_factory=list)
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "projection": self.projection,
            "repositories": self.repositories,
            "documents": self.documents,
            "infrastructure": self.infrastructure,
            "decisions": self.decisions,
            "capabilities": self.capabilities,
            "owner_device_ids": self.owner_device_ids,
            "status": self.status,
        }


# ── Registry ──────────────────────────────────────────────────────────────


class ProjectRegistry:
    """Read-only registry of projects seeded from JSON."""

    def __init__(self, registry_path: str | None = None) -> None:
        self._path = registry_path or os.path.join(_ROOT, "infra", "project_registry.json")
        self._projects: dict[str, ProjectDefinition] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path, "r") as f:
                raw = json.load(f)
        except FileNotFoundError:
            logger.debug("Project registry not found at %s", self._path)
            return
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in project registry %s: %s", self._path, exc)
            return

        if not isinstance(raw, list):
            logger.warning("Project registry is not a list: %s", self._path)
            return

        for entry in raw:
            if not isinstance(entry, dict) or "project_id" not in entry:
                continue
            proj = ProjectDefinition(
                project_id=entry["project_id"],
                name=entry.get("name", entry["project_id"]),
                description=entry.get("description", ""),
                projection=entry.get("projection", ""),
                repositories=entry.get("repositories", []),
                documents=entry.get("documents", []),
                infrastructure=entry.get("infrastructure", []),
                decisions=entry.get("decisions", []),
                capabilities=entry.get("capabilities", []),
                owner_device_ids=entry.get("owner_device_ids", []),
                status=entry.get("status", "active"),
            )
            self._projects[proj.project_id] = proj

        logger.debug("Loaded %d projects from %s", len(self._projects), self._path)

    # ── Lookups ───────────────────────────────────────────────────────

    def get(self, project_id: str) -> ProjectDefinition | None:
        return self._projects.get(project_id)

    def list_projects(self, status: str | None = None) -> list[ProjectDefinition]:
        projects = list(self._projects.values())
        if status is not None:
            projects = [p for p in projects if p.status == status]
        return projects

    def find_by_repo(self, repo_id: str) -> ProjectDefinition | None:
        for proj in self._projects.values():
            if repo_id in proj.repositories:
                return proj
        return None

    def find_by_name(self, name: str) -> ProjectDefinition | None:
        lower = name.lower()
        for proj in self._projects.values():
            if proj.name.lower() == lower:
                return proj
        for proj in self._projects.values():
            if lower in proj.name.lower():
                return proj
        return None

    def find_by_projection(self, projection: str) -> ProjectDefinition | None:
        lower = projection.lower()
        for proj in self._projects.values():
            if proj.projection.lower() == lower:
                return proj
        return None

    def all_project_ids(self) -> list[str]:
        return list(self._projects.keys())

    # ── Context Bundle ────────────────────────────────────────────────

    def context_for_project(self, project_id: str) -> dict[str, Any]:
        proj = self.get(project_id)
        if proj is None:
            return {"error": f"Project not found: {project_id}"}
        return {
            "project": proj.to_dict(),
            "repo_count": len(proj.repositories),
            "doc_count": len(proj.documents),
            "infra_count": len(proj.infrastructure),
            "capability_count": len(proj.capabilities),
            "device_count": len(proj.owner_device_ids),
            "decision_count": len(proj.decisions),
            "has_projection": bool(proj.projection),
        }

    @property
    def project_count(self) -> int:
        return len(self._projects)
