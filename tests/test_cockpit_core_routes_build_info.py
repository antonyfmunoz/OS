from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    sys.path.remove(str(ROOT))
except ValueError:
    pass
sys.path.insert(0, str(ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "candidate_cockpit_core_routes",
    ROOT / "transports" / "api" / "cockpit_core_routes.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_cockpit_frontend_asset_info = _MODULE._cockpit_frontend_asset_info
_current_source_sha = _MODULE._current_source_sha


def _manifest_digest(manifest: dict) -> str:
    stable = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    return hashlib.sha256(
        json.dumps(stable, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _write_manifest(dist: Path, sha: str, bytes_proof: dict, **overrides: object) -> dict:
    manifest = {
        "candidate_sha": sha,
        "source_head": sha,
        "source_tree": "b" * 40,
        "index_sha256": bytes_proof["index_sha256"],
        "assets": bytes_proof["assets"],
        "build_status": "SUCCEEDED",
        "artifact_contract": "wave2_exact_candidate_frontend",
    }
    manifest.update(overrides)
    manifest["manifest_sha256"] = _manifest_digest(manifest)
    (dist / ".umh-wave2-artifact.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_current_source_sha_accepts_candidate_container_build_commit(monkeypatch, tmp_path) -> None:
    sha = "f" * 40
    for key in ("UMH_SOURCE_SHA", "SOURCE_SHA", "UMH_RELEASE_SHA", "UMH_CANDIDATE_SHA"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("UMH_BUILD_COMMIT", sha)

    assert _current_source_sha(tmp_path) == sha


def test_build_info_extracts_main_vite_assets_and_content_hashes(tmp_path) -> None:
    root = tmp_path
    dist = root / "cockpit" / "dist-web"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    js = assets / "main-Dr3BHW-_.js"
    css = assets / "main-Cp0Dy9tI.css"
    js.write_text("console.log('candidate')\n", encoding="utf-8")
    css.write_text("body{color:black}\n", encoding="utf-8")
    sha = "a" * 40
    index = """
        <script type="module" crossorigin src="/assets/main-Dr3BHW-_.js"></script>
        <link rel="stylesheet" crossorigin href="/assets/main-Cp0Dy9tI.css">
        """
    (dist / "index.html").write_text(index, encoding="utf-8")
    _write_manifest(
        dist,
        sha,
        {
            "index_sha256": hashlib.sha256((dist / "index.html").read_bytes()).hexdigest(),
            "assets": {
                "js": {"name": js.name, "sha256": hashlib.sha256(js.read_bytes()).hexdigest()},
                "css": {"name": css.name, "sha256": hashlib.sha256(css.read_bytes()).hexdigest()},
            },
        },
    )

    info = _cockpit_frontend_asset_info(root, expected_sha=sha)

    assert info["frontend_assets_ok"] is True
    assert info["frontend_artifact_ok"] is True
    assert info["js_asset"] == "main-Dr3BHW-_.js"
    assert info["css_asset"] == "main-Cp0Dy9tI.css"
    assert info["js_sha256"] == hashlib.sha256(js.read_bytes()).hexdigest()
    assert info["css_sha256"] == hashlib.sha256(css.read_bytes()).hexdigest()


def test_build_info_fails_when_referenced_asset_is_missing(tmp_path) -> None:
    root = tmp_path
    dist = root / "cockpit" / "dist-web"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (assets / "main-Cp0Dy9tI.css").write_text("body{}\n", encoding="utf-8")
    (dist / "index.html").write_text(
        """
        <script type="module" src="/assets/main-missing.js"></script>
        <link rel="stylesheet" href="/assets/main-Cp0Dy9tI.css">
        """,
        encoding="utf-8",
    )

    info = _cockpit_frontend_asset_info(root)

    assert info["frontend_assets_ok"] is False
    assert "js asset missing: main-missing.js" in info["frontend_asset_errors"]


def test_build_info_requires_exact_candidate_artifact_manifest(tmp_path) -> None:
    root = tmp_path
    dist = root / "cockpit" / "dist-web"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (assets / "main.js").write_text("console.log('old')\n", encoding="utf-8")
    (assets / "main.css").write_text("body{}\n", encoding="utf-8")
    (dist / "index.html").write_text(
        """
        <script type="module" src="/assets/main.js"></script>
        <link rel="stylesheet" href="/assets/main.css">
        """,
        encoding="utf-8",
    )
    bytes_proof = {
        "index_sha256": hashlib.sha256((dist / "index.html").read_bytes()).hexdigest(),
        "assets": {
            "js": {
                "name": "main.js",
                "sha256": hashlib.sha256((assets / "main.js").read_bytes()).hexdigest(),
            },
            "css": {
                "name": "main.css",
                "sha256": hashlib.sha256((assets / "main.css").read_bytes()).hexdigest(),
            },
        },
    }

    missing = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert missing["frontend_assets_ok"] is False
    assert missing["frontend_artifact_ok"] is False
    assert "artifact manifest missing" in missing["frontend_artifact_errors"]

    _write_manifest(
        dist,
        "d" * 40,
        bytes_proof,
        source_tree="e" * 40,
    )

    stale = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert stale["frontend_assets_ok"] is False
    assert stale["frontend_artifact_ok"] is False
    assert "artifact candidate SHA mismatch" in stale["frontend_artifact_errors"]
    assert "artifact source HEAD mismatch" in stale["frontend_artifact_errors"]

    _write_manifest(dist, "c" * 40, bytes_proof, build_status="FAILED")
    failed_build = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert failed_build["frontend_artifact_ok"] is False
    assert "artifact build status is not SUCCEEDED" in failed_build["frontend_artifact_errors"]

    manifest = _write_manifest(dist, "c" * 40, bytes_proof)
    manifest["source_tree"] = "f" * 40
    (dist / ".umh-wave2-artifact.json").write_text(json.dumps(manifest), encoding="utf-8")
    tampered = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert tampered["frontend_artifact_ok"] is False
    assert "artifact manifest digest mismatch" in tampered["frontend_artifact_errors"]


def test_build_info_can_verify_external_release_artifact(monkeypatch, tmp_path) -> None:
    source_root = tmp_path / "source"
    artifact_root = tmp_path / "artifact-dist"
    assets = artifact_root / "assets"
    assets.mkdir(parents=True)
    js = assets / "main.js"
    css = assets / "main.css"
    js.write_text("console.log('candidate')\n", encoding="utf-8")
    css.write_text("body{}\n", encoding="utf-8")
    (artifact_root / "index.html").write_text(
        """
        <script type="module" src="/assets/main.js"></script>
        <link rel="stylesheet" href="/assets/main.css">
        """,
        encoding="utf-8",
    )
    sha = "a" * 40
    _write_manifest(
        artifact_root,
        sha,
        {
            "index_sha256": hashlib.sha256((artifact_root / "index.html").read_bytes()).hexdigest(),
            "assets": {
                "js": {"name": js.name, "sha256": hashlib.sha256(js.read_bytes()).hexdigest()},
                "css": {"name": css.name, "sha256": hashlib.sha256(css.read_bytes()).hexdigest()},
            },
        },
    )
    monkeypatch.setenv("UMH_COCKPIT_DIST_WEB", str(artifact_root))

    info = _cockpit_frontend_asset_info(source_root, expected_sha=sha)

    assert info["frontend_assets_ok"] is True
    assert info["frontend_artifact_ok"] is True
    assert info["frontend_artifact_manifest"].startswith(str(artifact_root))


def test_build_info_rejects_manifest_when_served_bytes_change(tmp_path) -> None:
    root = tmp_path
    dist = root / "cockpit" / "dist-web"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    js = assets / "main.js"
    css = assets / "main.css"
    js.write_text("console.log('fresh')\n", encoding="utf-8")
    css.write_text("body{}\n", encoding="utf-8")
    (dist / "index.html").write_text(
        """
        <script type="module" src="/assets/main.js"></script>
        <link rel="stylesheet" href="/assets/main.css">
        """,
        encoding="utf-8",
    )
    sha = "c" * 40
    _write_manifest(
        dist,
        sha,
        {
            "index_sha256": hashlib.sha256((dist / "index.html").read_bytes()).hexdigest(),
            "assets": {
                "js": {"name": js.name, "sha256": hashlib.sha256(js.read_bytes()).hexdigest()},
                "css": {"name": css.name, "sha256": hashlib.sha256(css.read_bytes()).hexdigest()},
            },
        },
        source_tree="e" * 40,
    )
    js.write_text("console.log('stale')\n", encoding="utf-8")

    info = _cockpit_frontend_asset_info(root, expected_sha=sha)

    assert info["frontend_assets_ok"] is False
    assert info["frontend_artifact_ok"] is False
    assert "artifact asset hash mismatch" in info["frontend_artifact_errors"]
