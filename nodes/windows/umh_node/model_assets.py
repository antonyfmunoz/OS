"""Governed model asset resolution for the Windows node daemon."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


YOLOV8N_MODEL_ID = "yolov8n"
YOLOV8N_FILENAME = "yolov8n.pt"
YOLOV8N_SHA256 = "F59B3D833E2FF32E194B5BB8E08D211DC7C5BDF144B90D2C8412C47CCFC83B36"
YOLOV8N_SOURCE = "ultralytics/yolov8n.pt"


class ModelAssetError(RuntimeError):
    """Raised when a model asset violates the runtime-state boundary."""


@dataclass(frozen=True)
class ModelAsset:
    model_id: str
    path: Path
    sha256: str
    source: str


def default_runtime_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "UMH"
    return Path(os.environ.get("UMH_RUNTIME_ROOT", str(Path.home() / ".umh")))


def default_model_root() -> Path:
    return Path(os.environ.get("UMH_MODEL_ASSET_ROOT", str(default_runtime_root() / "models")))


def default_cache_root() -> Path:
    return Path(os.environ.get("UMH_CACHE_ROOT", str(default_runtime_root() / "cache")))


def default_run_root() -> Path:
    return Path(os.environ.get("UMH_RUN_ROOT", str(default_runtime_root() / "run")))


def configure_process_runtime_environment() -> Path:
    """Pin mutable daemon state to governed runtime directories outside Git."""
    runtime_root = default_runtime_root()
    cache_root = default_cache_root()
    run_root = default_run_root()
    for path in (runtime_root, cache_root, run_root):
        path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("UMH_RUNTIME_ROOT", str(runtime_root))
    os.environ.setdefault("UMH_MODEL_ASSET_ROOT", str(default_model_root()))
    os.environ.setdefault("UMH_CACHE_ROOT", str(cache_root))
    os.environ.setdefault("UMH_RUN_ROOT", str(run_root))
    os.environ.setdefault("YOLO_CONFIG_DIR", str(cache_root / "ultralytics"))
    os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(cache_root / "ultralytics"))
    os.environ.setdefault("TORCH_HOME", str(cache_root / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "xdg"))
    os.environ.setdefault("TMP", str(run_root / "tmp"))
    os.environ.setdefault("TEMP", str(run_root / "tmp"))
    (run_root / "tmp").mkdir(parents=True, exist_ok=True)
    return run_root


def _is_inside(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
    except OSError:
        return False


def path_is_inside_git_worktree(path: Path) -> bool:
    """Detect paths under a Git checkout without invoking git."""
    resolved = path.resolve()
    for parent in (resolved, *resolved.parents):
        if (parent / ".git").exists():
            return True
    return False


def _assert_not_git_path(path: Path) -> None:
    if path_is_inside_git_worktree(path):
        raise ModelAssetError(f"model asset path is inside a Git worktree: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def yolo_model_path() -> Path:
    override = os.environ.get("UMH_YOLOV8N_MODEL_PATH")
    if override:
        return Path(override)
    return default_model_root() / YOLOV8N_MODEL_ID / YOLOV8N_SHA256 / YOLOV8N_FILENAME


def resolve_yolov8n_asset() -> ModelAsset:
    configure_process_runtime_environment()
    path = yolo_model_path()
    _assert_not_git_path(path)
    if not path.exists():
        raise ModelAssetError(
            f"required model asset missing: {path}; install {YOLOV8N_SOURCE} with SHA-256 {YOLOV8N_SHA256}"
        )
    if not path.is_file():
        raise ModelAssetError(f"model asset is not a file: {path}")
    actual = sha256_file(path)
    if actual != YOLOV8N_SHA256:
        raise ModelAssetError(
            f"model asset hash mismatch for {path}: expected {YOLOV8N_SHA256}, got {actual}"
        )
    return ModelAsset(
        model_id=YOLOV8N_MODEL_ID,
        path=path.resolve(),
        sha256=actual,
        source=YOLOV8N_SOURCE,
    )


def install_yolov8n_asset(source: Path, model_root: Path | None = None) -> ModelAsset:
    """Atomically install a verified YOLOv8n artifact into governed storage."""
    source = source.resolve()
    if not source.is_file():
        raise ModelAssetError(f"source model asset is not a file: {source}")
    if sha256_file(source) != YOLOV8N_SHA256:
        raise ModelAssetError(f"source model asset hash mismatch: {source}")

    root = (model_root or default_model_root()).resolve()
    _assert_not_git_path(root)
    dest_dir = root / YOLOV8N_MODEL_ID / YOLOV8N_SHA256
    dest = dest_dir / YOLOV8N_FILENAME
    dest_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{YOLOV8N_FILENAME}.", suffix=".tmp", dir=str(dest_dir))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(source, tmp)
        if sha256_file(tmp) != YOLOV8N_SHA256:
            raise ModelAssetError("copied model asset hash mismatch")
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink()

    return resolve_yolov8n_asset()
