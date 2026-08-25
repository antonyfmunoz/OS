from __future__ import annotations

import hashlib

from transports.api.cockpit_core_routes import _cockpit_frontend_asset_info


def test_build_info_extracts_main_vite_assets_and_content_hashes(tmp_path) -> None:
    root = tmp_path
    dist = root / "cockpit" / "dist-web"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    js = assets / "main-Dr3BHW-_.js"
    css = assets / "main-Cp0Dy9tI.css"
    js.write_text("console.log('candidate')\n", encoding="utf-8")
    css.write_text("body{color:black}\n", encoding="utf-8")
    (dist / "index.html").write_text(
        """
        <script type="module" crossorigin src="/assets/main-Dr3BHW-_.js"></script>
        <link rel="stylesheet" crossorigin href="/assets/main-Cp0Dy9tI.css">
        """,
        encoding="utf-8",
    )

    info = _cockpit_frontend_asset_info(root)

    assert info["frontend_assets_ok"] is True
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
