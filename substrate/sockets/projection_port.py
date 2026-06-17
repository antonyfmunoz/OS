"""Projection Port — abstract consumption layer for projections.

Ensures projections consume UMH substrate rather than recreating it.
The projection anti-drift gate.

Projections register here to declare:
  - Which capabilities they consume
  - Which routes they mount
  - Whether they are drifting (importing from wrong layers)

This is a read-only audit and registration layer.
It does NOT modify any projection code.

Gate 10 — Projection Consumption Layer. UMH substrate socket. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_PORT_DIR = os.path.join(_REPO_ROOT, "data", "umh", "projections")
_PORT_PATH = os.path.join(_PORT_DIR, "registrations.jsonl")

# Legacy in-memory registry (backward compat with original API)
_projections: dict[str, dict[str, Any]] = {}


def register_projection(projection_id: str, config: dict[str, Any]) -> None:
    _projections[projection_id] = config


def get_projection(projection_id: str) -> dict[str, Any] | None:
    return _projections.get(projection_id)


def list_projections() -> list[str]:
    return list(_projections.keys())


def unregister_projection(projection_id: str) -> bool:
    return _projections.pop(projection_id, None) is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ProjectionRegistration:
    projection_id: str = field(default_factory=lambda: f"proj-{uuid4().hex[:8]}")
    name: str = ""
    capabilities_consumed: list[str] = field(default_factory=list)
    routes_mounted: list[str] = field(default_factory=list)
    substrate_imports: list[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectionRegistration:
        d = dict(d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@runtime_checkable
class ProjectionPortProtocol(Protocol):
    def register(self, registration: ProjectionRegistration) -> bool: ...
    def list_registrations(self) -> list[ProjectionRegistration]: ...
    def capabilities_for(self, projection_id: str) -> list[str]: ...
    def unregister(self, projection_id: str) -> bool: ...


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Drift detection — deterministic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ALLOWED_IMPORT_PREFIXES = [
    "substrate.",
    "adapters.",
    "transports.",
]


def detect_import_drift(
    projection_name: str,
    imports: list[str],
) -> dict[str, Any]:
    """Check if a projection imports from forbidden layers."""
    violations: list[str] = []
    clean: list[str] = []
    for imp in imports:
        allowed = any(imp.startswith(prefix) for prefix in _ALLOWED_IMPORT_PREFIXES)
        if allowed:
            clean.append(imp)
        else:
            violations.append(imp)

    return {
        "projection": projection_name,
        "total_imports": len(imports),
        "clean": len(clean),
        "violations": violations,
        "violation_count": len(violations),
        "drifting": len(violations) > 0,
    }


def scan_projection_imports(projection_dir: str) -> list[str]:
    """Scan a projection directory for Python imports."""
    imports: list[str] = []
    if not os.path.isdir(projection_dir):
        return imports
    for root, _dirs, files in os.walk(projection_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("from ") and " import " in line:
                            module = line.split("from ", 1)[1].split(" import")[0].strip()
                            imports.append(module)
                        elif line.startswith("import ") and not line.startswith("import os"):
                            module = line.split("import ", 1)[1].split(" as")[0].strip()
                            imports.append(module)
            except OSError:
                continue
    return imports


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProjectionPort:
    """Registry and drift detection for projections consuming UMH."""

    def __init__(self, store_path: str = _PORT_PATH) -> None:
        self._path = store_path
        self._lock = threading.Lock()
        self._registrations: dict[str, ProjectionRegistration] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        reg = ProjectionRegistration.from_dict(d)
                        self._registrations[reg.projection_id] = reg
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.debug("Skip malformed JSONL line: %s", e)
        except OSError as e:
            logger.debug("Cannot read %s: %s", self._path, e)

    def _append(self, reg: ProjectionRegistration) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(reg.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for reg in self._registrations.values():
                f.write(json.dumps(reg.to_dict(), default=str) + "\n")

    # ── Registration ───────────────────────────────────────────────

    def register(self, registration: ProjectionRegistration) -> bool:
        with self._lock:
            self._registrations[registration.projection_id] = registration
            self._append(registration)
        logger.info(
            "Registered projection: %s (%s)",
            registration.name,
            registration.projection_id,
        )
        return True

    def unregister(self, projection_id: str) -> bool:
        if projection_id not in self._registrations:
            return False
        with self._lock:
            del self._registrations[projection_id]
            self._rewrite()
        return True

    def get(self, projection_id: str) -> ProjectionRegistration | None:
        return self._registrations.get(projection_id)

    def list_registrations(self) -> list[ProjectionRegistration]:
        return sorted(
            self._registrations.values(),
            key=lambda r: r.registered_at,
            reverse=True,
        )

    def capabilities_for(self, projection_id: str) -> list[str]:
        reg = self._registrations.get(projection_id)
        return reg.capabilities_consumed if reg else []

    # ── Drift detection ────────────────────────────────────────────

    def audit_projection(self, projection_name: str) -> dict[str, Any]:
        proj_dir = os.path.join(_REPO_ROOT, "projections", projection_name)
        imports = scan_projection_imports(proj_dir)
        return detect_import_drift(projection_name, imports)

    def audit_all(self) -> dict[str, Any]:
        projections_dir = os.path.join(_REPO_ROOT, "projections")
        if not os.path.isdir(projections_dir):
            return {"projections": [], "total_violations": 0}

        results: list[dict[str, Any]] = []
        total_violations = 0
        for name in sorted(os.listdir(projections_dir)):
            proj_dir = os.path.join(projections_dir, name)
            if not os.path.isdir(proj_dir):
                continue
            result = self.audit_projection(name)
            results.append(result)
            total_violations += result["violation_count"]

        return {
            "projections": results,
            "total_violations": total_violations,
            "all_clean": total_violations == 0,
        }

    # ── Summary ────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        return {
            "total_registrations": len(self._registrations),
            "projections": [
                {
                    "name": r.name,
                    "projection_id": r.projection_id,
                    "capabilities_count": len(r.capabilities_consumed),
                    "routes_count": len(r.routes_mounted),
                }
                for r in self._registrations.values()
            ],
        }
