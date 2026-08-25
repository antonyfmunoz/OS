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


def test_operator_api_auth_rejects_empty_wrong_and_accepts_exact_key(monkeypatch) -> None:
    monkeypatch.setattr(operator_api, "API_KEY", "secret-token")

    for provided in (None, "", "   ", "wrong"):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(operator_api.verify_api_key(_request(provided)))
        assert exc.value.status_code == 401
        assert "secret-token" not in str(exc.value.detail)

    assert asyncio.run(operator_api.verify_api_key(_request("secret-token"))) is None


def test_ready_distinguishes_required_startup_from_optional_voice_warmup(monkeypatch) -> None:
    components = {
        "operator_api_key": {"required": True, "ready": True, "detail": "configured"},
        "execution_spine": {"required": True, "ready": True, "detail": "loaded"},
        "adapter_sockets": {"required": True, "ready": True, "detail": "registered"},
        "config_store": {"required": True, "ready": True, "detail": "registered"},
        "organism_daemon": {"required": True, "ready": True, "detail": "started"},
        "organism_port": {"required": True, "ready": True, "detail": "registered"},
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
