from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

import services.operator_api as operator_api

ROOT = Path(__file__).resolve().parents[1]


def _request(key: str | None) -> SimpleNamespace:
    headers = {}
    if key is not None:
        headers["X-API-Key"] = key
    return SimpleNamespace(headers=headers)


def test_operator_api_auth_missing_or_empty_key_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(operator_api, "API_KEY", "")

    with pytest.raises(HTTPException) as missing:
        asyncio.run(operator_api.verify_api_key(_request("anything")))
    with pytest.raises(HTTPException) as empty:
        asyncio.run(operator_api.verify_api_key(_request("")))

    assert missing.value.status_code == 503
    assert empty.value.status_code == 503


def test_operator_api_missing_key_import_initializes_not_ready() -> None:
    env = dict(os.environ)
    env["UMH_OPERATOR_API_KEY"] = ""
    env["PYTHONPATH"] = str(ROOT)
    script = (
        "import json; "
        "import services.operator_api as op; "
        "status = op.operator_readiness_status(); "
        "print(json.dumps(status['components']['operator_api_key'], sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    component = json.loads(result.stdout)
    assert component["required"] is True
    assert component["ready"] is False
    assert "not configured" in component["detail"]


def test_operator_api_pins_umh_root_before_substrate_import(tmp_path) -> None:
    foreign = tmp_path / "foreign"
    (foreign / "substrate" / "execution").mkdir(parents=True)
    (foreign / "substrate" / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "substrate" / "execution" / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "substrate" / "execution" / "cpu_gate.py").write_text(
        "def gated_subprocess_run(*args, **kwargs):\n"
        "    raise RuntimeError('foreign substrate imported')\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["UMH_ROOT"] = str(ROOT)
    env["UMH_OPERATOR_API_KEY"] = "secret"
    env["PYTHONPATH"] = os.pathsep.join([str(foreign), str(ROOT)])
    script = (
        "import json, services.operator_api as op; "
        "print(json.dumps({'file': op.gated_subprocess_run.__code__.co_filename}))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(tmp_path),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    payload = json.loads(result.stdout)
    assert payload["file"].startswith(str(ROOT))
    assert "/foreign/" not in payload["file"]
    assert "foreign substrate imported" not in result.stderr


def test_operator_api_default_root_is_own_worktree_not_opt_os() -> None:
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    env["UMH_OPERATOR_API_KEY"] = "secret"
    env["PYTHONPATH"] = str(ROOT)
    script = (
        "import json, services.operator_api as op; "
        "print(json.dumps({'root': str(op.UMH_ROOT), 'file': op.__file__}))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    payload = json.loads(result.stdout)
    assert payload["root"] == str(ROOT)
    assert payload["file"].startswith(str(ROOT))


def test_operator_api_refuses_to_mount_stale_cockpit_dist(tmp_path) -> None:
    dist = tmp_path / "cockpit" / "dist-web"
    (dist / "assets").mkdir(parents=True)
    (dist / "assets" / "main.js").write_text("console.log('stale')\n", encoding="utf-8")
    (dist / "assets" / "main.css").write_text("body{}\n", encoding="utf-8")
    (dist / "index.html").write_text(
        """
        <script type="module" src="/assets/main.js"></script>
        <link rel="stylesheet" href="/assets/main.css">
        """,
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["UMH_ROOT"] = str(tmp_path)
    env["UMH_SOURCE_SHA"] = "a" * 40
    env["UMH_OPERATOR_API_KEY"] = "secret"
    env["PYTHONPATH"] = str(ROOT)
    script = (
        "import json, services.operator_api as op; "
        "print(json.dumps({'mounted': any(getattr(r, 'name', '') == 'cockpit' for r in op.app.routes)}))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )

    payload = json.loads(result.stdout)
    assert payload["mounted"] is False


def test_operator_api_auth_rejects_empty_wrong_and_accepts_exact_key(monkeypatch) -> None:
    monkeypatch.setattr(operator_api, "API_KEY", "secret-token")

    for provided in (None, "", "   ", "wrong"):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(operator_api.verify_api_key(_request(provided)))
        assert exc.value.status_code == 401
        assert "secret-token" not in str(exc.value.detail)

    assert asyncio.run(operator_api.verify_api_key(_request("secret-token"))) is None


def test_cockpit_api_auth_rejects_blank_server_and_client_tokens(monkeypatch) -> None:
    import transports.api.cockpit as cockpit

    request = SimpleNamespace(state=SimpleNamespace(clerk_user_id=None))
    monkeypatch.setattr(cockpit, "_DEV_BYPASS", False)

    monkeypatch.setattr(cockpit, "_API_KEY", "   ")
    with pytest.raises(HTTPException) as missing_config:
        asyncio.run(cockpit._require_api_key(request, "   "))
    assert missing_config.value.status_code == 503

    monkeypatch.setattr(cockpit, "_API_KEY", "secret-token")
    for provided in (None, "", "   ", "wrong"):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(cockpit._require_api_key(request, provided))
        assert exc.value.status_code == 401

    assert asyncio.run(cockpit._require_api_key(request, " secret-token ")) == " secret-token "


def test_operator_websocket_auth_rejects_whitespace_configured_key(monkeypatch) -> None:
    monkeypatch.setattr(operator_api, "_WS_TOKEN", "   ")
    monkeypatch.setattr(operator_api, "_DEV_BYPASS", False)
    ws = SimpleNamespace(
        headers={},
        query_params={"token": "   "},
        client=SimpleNamespace(host="203.0.113.10"),
    )

    assert operator_api._validate_ws_auth(ws) is False


def test_cockpit_core_ws_rejects_blank_server_and_client_tokens(monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from transports.api import cockpit_core_routes

    def _private(_ip: str) -> bool:
        return False

    def _no_clerk(_ws):
        return None

    cockpit_core_routes.configure(
        require_operator_dep=lambda: "operator",
        is_private_ip_fn=_private,
        validate_ws_clerk_token_fn=_no_clerk,
        ws_token="   ",
        dev_bypass=False,
        trusted_proxies=set(),
    )
    app = FastAPI()
    app.include_router(cockpit_core_routes.core_ws_router)

    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=%20%20%20"):
                pass


def test_ready_distinguishes_required_startup_from_optional_voice_warmup(monkeypatch) -> None:
    components = {
        "operator_api_key": {"required": True, "ready": True, "detail": "configured"},
        "execution_spine": {"required": True, "ready": True, "detail": "loaded"},
        "adapter_sockets": {"required": True, "ready": True, "detail": "registered"},
        "config_store": {"required": True, "ready": True, "detail": "registered"},
        "organism_daemon": {"required": True, "ready": True, "detail": "started"},
        "organism_port": {"required": True, "ready": True, "detail": "registered"},
        "cockpit_frontend_artifact": {
            "required": True,
            "ready": True,
            "detail": "exact artifact verified",
        },
        "voice_warmup": {"required": False, "ready": False, "detail": "fail_soft"},
    }
    monkeypatch.setattr(operator_api, "_readiness_components", deepcopy(components))

    ready = asyncio.run(operator_api.ready())
    assert isinstance(ready, dict)
    assert ready["ready"] is True
    assert ready["components"]["voice_warmup"]["detail"] == "fail_soft"

    not_ready_components = deepcopy(components)
    not_ready_components["execution_spine"]["ready"] = False
    monkeypatch.setattr(operator_api, "_readiness_components", not_ready_components)

    not_ready = asyncio.run(operator_api.ready())
    assert isinstance(not_ready, JSONResponse)
    assert not_ready.status_code == 503


def test_ready_requires_exact_frontend_artifact(monkeypatch) -> None:
    components = {
        "operator_api_key": {"required": True, "ready": True, "detail": "configured"},
        "execution_spine": {"required": True, "ready": True, "detail": "loaded"},
        "adapter_sockets": {"required": True, "ready": True, "detail": "registered"},
        "config_store": {"required": True, "ready": True, "detail": "registered"},
        "organism_daemon": {"required": True, "ready": True, "detail": "started"},
        "organism_port": {"required": True, "ready": True, "detail": "registered"},
        "cockpit_frontend_artifact": {
            "required": True,
            "ready": False,
            "detail": "artifact manifest missing",
        },
        "voice_warmup": {"required": False, "ready": False, "detail": "WARMING"},
    }
    monkeypatch.setattr(operator_api, "_readiness_components", deepcopy(components))

    not_ready = asyncio.run(operator_api.ready())

    assert isinstance(not_ready, JSONResponse)
    assert not_ready.status_code == 503
