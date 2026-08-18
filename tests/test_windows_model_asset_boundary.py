from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nodes.windows.umh_node import model_assets


def _write_expected_asset(path: Path) -> None:
    path.write_bytes(b"model")


def test_model_assets_resolve_outside_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "Program Data" / "UMH" / "models"
    asset = root / model_assets.YOLOV8N_MODEL_ID / model_assets.YOLOV8N_SHA256 / model_assets.YOLOV8N_FILENAME
    asset.parent.mkdir(parents=True)
    _write_expected_asset(asset)
    monkeypatch.setenv("UMH_MODEL_ASSET_ROOT", str(root))
    monkeypatch.setattr(model_assets, "sha256_file", lambda path: model_assets.YOLOV8N_SHA256)

    resolved = model_assets.resolve_yolov8n_asset()

    assert resolved.path == asset.resolve()
    assert resolved.sha256 == model_assets.YOLOV8N_SHA256
    assert resolved.source == model_assets.YOLOV8N_SOURCE


def test_paths_inside_git_are_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    model_root = checkout / "models"
    asset = model_root / model_assets.YOLOV8N_MODEL_ID / model_assets.YOLOV8N_SHA256 / model_assets.YOLOV8N_FILENAME
    asset.parent.mkdir(parents=True)
    (checkout / ".git").mkdir()
    _write_expected_asset(asset)
    monkeypatch.setenv("UMH_MODEL_ASSET_ROOT", str(model_root))
    monkeypatch.setattr(model_assets, "sha256_file", lambda path: model_assets.YOLOV8N_SHA256)

    with pytest.raises(model_assets.ModelAssetError, match="inside a Git worktree"):
        model_assets.resolve_yolov8n_asset()


def test_missing_model_fails_deterministically(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UMH_MODEL_ASSET_ROOT", str(tmp_path / "models"))

    with pytest.raises(model_assets.ModelAssetError, match="required model asset missing"):
        model_assets.resolve_yolov8n_asset()


def test_hash_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "models"
    asset = root / model_assets.YOLOV8N_MODEL_ID / model_assets.YOLOV8N_SHA256 / model_assets.YOLOV8N_FILENAME
    asset.parent.mkdir(parents=True)
    _write_expected_asset(asset)
    monkeypatch.setenv("UMH_MODEL_ASSET_ROOT", str(root))
    monkeypatch.setattr(model_assets, "sha256_file", lambda path: "0" * 64)

    with pytest.raises(model_assets.ModelAssetError, match="hash mismatch"):
        model_assets.resolve_yolov8n_asset()


def test_install_is_atomic_and_rollback_keeps_prior_release(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "download" / model_assets.YOLOV8N_FILENAME
    source.parent.mkdir()
    _write_expected_asset(source)
    root = tmp_path / "Program Data" / "UMH" / "models"
    monkeypatch.setenv("UMH_MODEL_ASSET_ROOT", str(root))
    monkeypatch.setattr(model_assets, "sha256_file", lambda path: model_assets.YOLOV8N_SHA256)

    installed = model_assets.install_yolov8n_asset(source)
    prior = installed.path.read_bytes()
    source.write_bytes(b"replacement")
    reinstalled = model_assets.install_yolov8n_asset(source)

    assert reinstalled.path == installed.path
    assert reinstalled.path.read_bytes() == b"replacement"
    reinstalled.path.write_bytes(prior)
    assert model_assets.resolve_yolov8n_asset().path == installed.path


def test_runtime_environment_moves_caches_and_tmp_outside_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for key in (
        "UMH_MODEL_ASSET_ROOT",
        "UMH_CACHE_ROOT",
        "UMH_RUN_ROOT",
        "YOLO_CONFIG_DIR",
        "ULTRALYTICS_CONFIG_DIR",
        "TORCH_HOME",
        "XDG_CACHE_HOME",
        "TMP",
        "TEMP",
    ):
        monkeypatch.delenv(key, raising=False)
    runtime_root = tmp_path / "Program Data" / "UMH"
    monkeypatch.setenv("UMH_RUNTIME_ROOT", str(runtime_root))

    run_root = model_assets.configure_process_runtime_environment()

    assert run_root == runtime_root / "run"
    assert os.environ["YOLO_CONFIG_DIR"] == str(runtime_root / "cache" / "ultralytics")
    assert os.environ["TORCH_HOME"] == str(runtime_root / "cache" / "torch")
    assert os.environ["TMP"] == str(runtime_root / "run" / "tmp")
    assert (runtime_root / "run" / "tmp").is_dir()


def test_object_detector_passes_absolute_model_path_to_yolo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    asset_path = tmp_path / "Program Data" / "UMH" / "models" / "yolov8n.pt"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"model")
    fake_asset = model_assets.ModelAsset(
        model_id=model_assets.YOLOV8N_MODEL_ID,
        path=asset_path,
        sha256=model_assets.YOLOV8N_SHA256,
        source=model_assets.YOLOV8N_SOURCE,
    )

    fake_yolo = MagicMock()
    fake_torch = MagicMock()
    fake_torch.cuda.is_available.return_value = False

    with patch("nodes.windows.umh_node.model_assets.resolve_yolov8n_asset", return_value=fake_asset), patch.dict(
        "sys.modules",
        {"ultralytics": MagicMock(YOLO=fake_yolo), "torch": fake_torch},
    ):
        from nodes.windows.umh_node.adapters.object_detector import ObjectDetector

        detector = ObjectDetector()
        assert detector.load_model() is True

    fake_yolo.assert_called_once_with(str(asset_path))
    assert detector.get_status()["model_asset_sha256"] == model_assets.YOLOV8N_SHA256


def test_object_detector_missing_asset_does_not_call_yolo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_yolo = MagicMock()

    with patch(
        "nodes.windows.umh_node.model_assets.resolve_yolov8n_asset",
        side_effect=model_assets.ModelAssetError("missing"),
    ), patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=fake_yolo), "torch": MagicMock()}):
        from nodes.windows.umh_node.adapters.object_detector import ObjectDetector

        detector = ObjectDetector()
        assert detector.load_model() is False

    fake_yolo.assert_not_called()
    assert "missing" in detector.load_error
