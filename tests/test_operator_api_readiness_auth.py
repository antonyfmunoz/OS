from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

import services.operator_api as operator_api


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

