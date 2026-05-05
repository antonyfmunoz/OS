"""Checkpoint persistence — in-memory and optional file-based stores.

Provides crash-resumable design without requiring DB migration.
Default is in-memory. File persistence uses atomic write pattern.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any, Protocol

from umh.cells.models import CellCheckpoint
from umh.cells.workflow import WorkflowRun


class CheckpointStore(Protocol):
    """Protocol for checkpoint storage backends."""

    def save_cell_checkpoint(self, checkpoint: CellCheckpoint) -> None: ...

    def load_cell_checkpoint(self, cell_id: str) -> CellCheckpoint | None: ...

    def list_cell_checkpoints(self, cell_id: str | None = None) -> list[CellCheckpoint]: ...

    def save_workflow_run(self, run: WorkflowRun) -> None: ...

    def load_workflow_run(self, run_id: str) -> WorkflowRun | None: ...

    def list_workflow_runs(self) -> list[WorkflowRun]: ...

    def clear(self) -> None: ...


class InMemoryCheckpointStore:
    """In-memory checkpoint store. Fast, no I/O, lost on restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cell_checkpoints: dict[str, list[CellCheckpoint]] = {}
        self._workflow_runs: dict[str, WorkflowRun] = {}

    def save_cell_checkpoint(self, checkpoint: CellCheckpoint) -> None:
        with self._lock:
            self._cell_checkpoints.setdefault(checkpoint.cell_id, []).append(checkpoint)

    def load_cell_checkpoint(self, cell_id: str) -> CellCheckpoint | None:
        with self._lock:
            checkpoints = self._cell_checkpoints.get(cell_id, [])
            return checkpoints[-1] if checkpoints else None

    def list_cell_checkpoints(self, cell_id: str | None = None) -> list[CellCheckpoint]:
        with self._lock:
            if cell_id:
                return list(self._cell_checkpoints.get(cell_id, []))
            result: list[CellCheckpoint] = []
            for cps in self._cell_checkpoints.values():
                result.extend(cps)
            return result

    def save_workflow_run(self, run: WorkflowRun) -> None:
        with self._lock:
            self._workflow_runs[run.run_id] = run

    def load_workflow_run(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            return self._workflow_runs.get(run_id)

    def list_workflow_runs(self) -> list[WorkflowRun]:
        with self._lock:
            return list(self._workflow_runs.values())

    def clear(self) -> None:
        with self._lock:
            self._cell_checkpoints.clear()
            self._workflow_runs.clear()


class FileCheckpointStore:
    """File-based checkpoint store. Uses atomic write via tempfile + rename.

    Directory structure:
      base_dir/
        cells/<cell_id>/checkpoint_<n>.json
        runs/<run_id>.json
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._lock = threading.Lock()
        os.makedirs(os.path.join(base_dir, "cells"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "runs"), exist_ok=True)

    def _atomic_write(self, path: str, data: dict[str, Any]) -> None:
        dir_path = os.path.dirname(path)
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save_cell_checkpoint(self, checkpoint: CellCheckpoint) -> None:
        with self._lock:
            cell_dir = os.path.join(self._base_dir, "cells", checkpoint.cell_id)
            os.makedirs(cell_dir, exist_ok=True)
            existing = len([f for f in os.listdir(cell_dir) if f.endswith(".json")])
            path = os.path.join(cell_dir, f"checkpoint_{existing}.json")
            self._atomic_write(path, checkpoint.to_dict())

    def load_cell_checkpoint(self, cell_id: str) -> CellCheckpoint | None:
        with self._lock:
            cell_dir = os.path.join(self._base_dir, "cells", cell_id)
            if not os.path.isdir(cell_dir):
                return None
            files = sorted(f for f in os.listdir(cell_dir) if f.endswith(".json"))
            if not files:
                return None
            path = os.path.join(cell_dir, files[-1])
            with open(path) as f:
                data = json.load(f)
            from umh.cells.models import CellStatus

            return CellCheckpoint(
                checkpoint_id=data["checkpoint_id"],
                cell_id=data["cell_id"],
                status=CellStatus(data["status"]),
                context=data["context"],
                version=data["version"],
                created_at=data.get("created_at", ""),
                metadata=data.get("metadata", {}),
            )

    def list_cell_checkpoints(self, cell_id: str | None = None) -> list[CellCheckpoint]:
        results: list[CellCheckpoint] = []
        with self._lock:
            cells_dir = os.path.join(self._base_dir, "cells")
            if not os.path.isdir(cells_dir):
                return results
            dirs = [cell_id] if cell_id else os.listdir(cells_dir)
            for cid in dirs:
                cell_dir = os.path.join(cells_dir, cid)
                if not os.path.isdir(cell_dir):
                    continue
                for fname in sorted(os.listdir(cell_dir)):
                    if not fname.endswith(".json"):
                        continue
                    path = os.path.join(cell_dir, fname)
                    with open(path) as f:
                        data = json.load(f)
                    from umh.cells.models import CellStatus

                    results.append(
                        CellCheckpoint(
                            checkpoint_id=data["checkpoint_id"],
                            cell_id=data["cell_id"],
                            status=CellStatus(data["status"]),
                            context=data["context"],
                            version=data["version"],
                            created_at=data.get("created_at", ""),
                            metadata=data.get("metadata", {}),
                        )
                    )
        return results

    def save_workflow_run(self, run: WorkflowRun) -> None:
        with self._lock:
            path = os.path.join(self._base_dir, "runs", f"{run.run_id}.json")
            self._atomic_write(path, run.to_dict())

    def load_workflow_run(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            path = os.path.join(self._base_dir, "runs", f"{run_id}.json")
            if not os.path.isfile(path):
                return None
            with open(path) as f:
                data = json.load(f)
            return WorkflowRun.from_dict(data)

    def list_workflow_runs(self) -> list[WorkflowRun]:
        results: list[WorkflowRun] = []
        with self._lock:
            runs_dir = os.path.join(self._base_dir, "runs")
            if not os.path.isdir(runs_dir):
                return results
            for fname in sorted(os.listdir(runs_dir)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(runs_dir, fname)
                with open(path) as f:
                    data = json.load(f)
                results.append(WorkflowRun.from_dict(data))
        return results

    def clear(self) -> None:
        import shutil

        with self._lock:
            for subdir in ("cells", "runs"):
                d = os.path.join(self._base_dir, subdir)
                if os.path.isdir(d):
                    shutil.rmtree(d)
                os.makedirs(d, exist_ok=True)
