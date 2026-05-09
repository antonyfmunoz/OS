"""Runtime Bootstrap State v1.

Initializes all required runtime directories, proof folders,
config markers, and registry caches. Provides a single bootstrap
lifecycle that all runtime systems depend on.

Phase 96.8AL. UMH substrate.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class BootstrapStage(Enum):
    BOOTSTRAP_START = "bootstrap_start"
    BOOTSTRAP_PATHS_INITIALIZED = "bootstrap_paths_initialized"
    BOOTSTRAP_REGISTRY_INITIALIZED = "bootstrap_registry_initialized"
    BOOTSTRAP_PROOFS_INITIALIZED = "bootstrap_proofs_initialized"
    BOOTSTRAP_RUNTIME_READY = "bootstrap_runtime_ready"
    BOOTSTRAP_FAILED = "bootstrap_failed"


REQUIRED_RUNTIME_DIRS = [
    "data/runtime/local_worker_runtime/inbox",
    "data/runtime/local_worker_runtime/processed",
    "data/runtime/local_worker_runtime/failed",
    "data/runtime/runtime_proofs",
    "data/runtime/spine_dispatch_queue/inbox",
    "data/runtime/spine_dispatch_queue/outbox",
    "data/runtime/spine_dispatch_queue/archive",
    "data/runtime/spine_dispatch_queue/results",
    "data/runtime/spine_gate_proofs",
    "data/runtime/spine_proofs",
    "data/runtime/sync_proofs",
    "data/runtime/live_execution_proofs",
    "data/runtime/execution_authority_proofs",
    "data/runtime/workpacket_execution_gate_proofs",
    "data/runtime/transformation_ledger/spine",
    "data/runtime/transformation_ledger/proof_run",
    "data/runtime/command_surface_proofs",
]

REQUIRED_CONFIG_FILES = [
    "config/control_plane_router_v1.json",
    "data/registries/local_worker_adapter_registry_v1.json",
]

NEVER_AUTO_HEAL = [
    "eos_ai/.env",
    "services/.env",
    "config/control_plane_router_v1.json",
    "data/registries/local_worker_adapter_registry_v1.json",
]


@dataclass
class BootstrapValidation:
    """Result of a bootstrap validation check."""

    valid: bool = False
    stage: BootstrapStage = BootstrapStage.BOOTSTRAP_START
    missing_dirs: list[str] = field(default_factory=list)
    missing_configs: list[str] = field(default_factory=list)
    auto_healed: list[str] = field(default_factory=list)
    denial_reasons: list[str] = field(default_factory=list)
    registry_loaded: bool = False
    registry_hash: str = ""
    registry_count: int = 0
    runtime_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "stage": self.stage.value,
            "missing_dirs": self.missing_dirs,
            "missing_configs": self.missing_configs,
            "auto_healed": self.auto_healed,
            "denial_reasons": self.denial_reasons,
            "registry_loaded": self.registry_loaded,
            "registry_hash": self.registry_hash,
            "registry_count": self.registry_count,
            "runtime_id": self.runtime_id,
            "timestamp": self.timestamp,
        }


class RuntimeBootstrapStateV1:
    """Manages the full runtime bootstrap lifecycle.

    Initializes directories, loads the canonical registry,
    validates config, and produces a deterministic runtime ID.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._stage = BootstrapStage.BOOTSTRAP_START
        self._runtime_id = f"RUNTIME-{uuid.uuid4().hex[:8]}"
        self._validation: BootstrapValidation | None = None
        self._registry = None
        self._ledger_entries: list[dict[str, Any]] = []

    @property
    def stage(self) -> BootstrapStage:
        return self._stage

    @property
    def runtime_id(self) -> str:
        return self._runtime_id

    @property
    def is_ready(self) -> bool:
        return self._stage == BootstrapStage.BOOTSTRAP_RUNTIME_READY

    @property
    def validation(self) -> BootstrapValidation | None:
        return self._validation

    def bootstrap(self, auto_heal: bool = True) -> BootstrapValidation:
        """Run the full bootstrap lifecycle."""
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        v = BootstrapValidation(runtime_id=self._runtime_id)
        self._emit_ledger("BOOTSTRAP_START", {"runtime_id": self._runtime_id})

        v.missing_dirs = self._check_dirs()
        if auto_heal and v.missing_dirs:
            v.auto_healed = self._auto_heal_dirs(v.missing_dirs)
            v.missing_dirs = [d for d in v.missing_dirs if d not in v.auto_healed]

        if v.missing_dirs:
            v.denial_reasons.append(f"missing_dirs: {', '.join(v.missing_dirs)}")
        self._stage = BootstrapStage.BOOTSTRAP_PATHS_INITIALIZED
        self._emit_ledger(
            "BOOTSTRAP_PATHS_INITIALIZED",
            {
                "missing": v.missing_dirs,
                "healed": v.auto_healed,
            },
        )

        registry = get_canonical_registry()
        self._registry = registry
        v.registry_loaded = True
        v.registry_hash = registry.registry_hash()
        v.registry_count = len(registry)
        self._stage = BootstrapStage.BOOTSTRAP_REGISTRY_INITIALIZED
        self._emit_ledger(
            "BOOTSTRAP_REGISTRY_INITIALIZED",
            {
                "hash": v.registry_hash,
                "count": v.registry_count,
            },
        )

        v.missing_configs = self._check_configs()
        if v.missing_configs:
            v.denial_reasons.append(f"missing_configs: {', '.join(v.missing_configs)}")

        config_marker = self._base_dir / "data/runtime/spine_gate_proofs/config_marker.json"
        if not config_marker.exists():
            if auto_heal:
                self._create_config_marker(config_marker, v.registry_hash)
                v.auto_healed.append(str(config_marker.relative_to(self._base_dir)))

        self._stage = BootstrapStage.BOOTSTRAP_PROOFS_INITIALIZED
        self._emit_ledger(
            "BOOTSTRAP_PROOFS_INITIALIZED",
            {
                "missing_configs": v.missing_configs,
            },
        )

        if not v.denial_reasons:
            self._stage = BootstrapStage.BOOTSTRAP_RUNTIME_READY
            v.valid = True
            v.stage = BootstrapStage.BOOTSTRAP_RUNTIME_READY
        else:
            self._stage = BootstrapStage.BOOTSTRAP_FAILED
            v.stage = BootstrapStage.BOOTSTRAP_FAILED

        self._emit_ledger(self._stage.value, {"valid": v.valid})
        self._validation = v
        self._persist_ledger()
        return v

    def _check_dirs(self) -> list[str]:
        missing = []
        for rel in REQUIRED_RUNTIME_DIRS:
            if not (self._base_dir / rel).exists():
                missing.append(rel)
        return missing

    def _check_configs(self) -> list[str]:
        missing = []
        for rel in REQUIRED_CONFIG_FILES:
            if not (self._base_dir / rel).exists():
                missing.append(rel)
        return missing

    def _auto_heal_dirs(self, missing: list[str]) -> list[str]:
        healed = []
        for rel in missing:
            if rel in NEVER_AUTO_HEAL:
                continue
            path = self._base_dir / rel
            path.mkdir(parents=True, exist_ok=True)
            healed.append(rel)
        return healed

    def _create_config_marker(self, path: Path, registry_hash: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        marker = {
            "created_by": "runtime_bootstrap_v1",
            "runtime_id": self._runtime_id,
            "registry_hash": registry_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, "w") as f:
            json.dump(marker, f, indent=2)

    def _emit_ledger(self, stage: str, data: dict[str, Any]) -> None:
        self._ledger_entries.append(
            {
                "state_id": f"STATE-{uuid.uuid4().hex[:8]}",
                "runtime_id": self._runtime_id,
                "stage": stage,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _persist_ledger(self) -> None:
        ledger_dir = self._base_dir / "data/runtime/transformation_ledger/bootstrap"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = ledger_dir / f"BOOTSTRAP-{ts}-{self._runtime_id}.json"
        with open(path, "w") as f:
            json.dump(self._ledger_entries, f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self._runtime_id,
            "stage": self._stage.value,
            "is_ready": self.is_ready,
            "validation": self._validation.to_dict() if self._validation else None,
        }
