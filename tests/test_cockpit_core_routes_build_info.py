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
    (dist / ".umh-wave2-artifact.json").write_text(
        json.dumps(
            {
                "candidate_sha": sha,
                "source_head": sha,
                "source_tree": "b" * 40,
            }
        ),
        encoding="utf-8",
    )
    (dist / "index.html").write_text(
        """
        <script type="module" crossorigin src="/assets/main-Dr3BHW-_.js"></script>
        <link rel="stylesheet" crossorigin href="/assets/main-Cp0Dy9tI.css">
        """,
        encoding="utf-8",
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

    missing = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert missing["frontend_assets_ok"] is False
    assert missing["frontend_artifact_ok"] is False
    assert "artifact manifest missing" in missing["frontend_artifact_errors"]

    (dist / ".umh-wave2-artifact.json").write_text(
        json.dumps(
            {
                "candidate_sha": "d" * 40,
                "source_head": "d" * 40,
                "source_tree": "e" * 40,
            }
        ),
        encoding="utf-8",
    )

    stale = _cockpit_frontend_asset_info(root, expected_sha="c" * 40)
    assert stale["frontend_assets_ok"] is False
    assert stale["frontend_artifact_ok"] is False
    assert "artifact candidate SHA mismatch" in stale["frontend_artifact_errors"]
    assert "artifact source HEAD mismatch" in stale["frontend_artifact_errors"]
