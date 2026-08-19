import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APIFY_DOCS = (
    ROOT / "skills/tools/apify/SKILL.md",
    ROOT / "skills/tools/apify/references/best_practices.md",
    ROOT / "skills/tools/apify/references/xquik_x_actors.md",
)
REFERENCE = APIFY_DOCS[-1]


def python_blocks(path: Path) -> list[str]:
    return re.findall(
        r"```python\n(.*?)```",
        path.read_text(encoding="utf-8"),
        re.DOTALL,
    )


def load_reference_helpers(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    namespace: dict[str, object] = {}
    block = next(block for block in python_blocks(REFERENCE) if "def start_paid_actor" in block)
    exec(compile(block, str(REFERENCE), "exec"), namespace)
    return namespace


def test_apify_python_blocks_parse() -> None:
    parsed = 0
    for path in APIFY_DOCS:
        for index, block in enumerate(python_blocks(path), 1):
            ast.parse(block, filename=f"{path}:python-block-{index}")
            parsed += 1
    assert parsed == 38


def test_paid_actor_uses_pay_per_event_option_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = load_reference_helpers(monkeypatch)
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 201

        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def json() -> dict[str, object]:
            return {"data": {"id": "run-1"}}

    class FakeRequests:
        class Timeout(Exception):
            pass

        class ConnectionError(Exception):
            pass

        @staticmethod
        def post(
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, object],
            params: dict[str, object],
            timeout: int,
        ) -> FakeResponse:
            captured.update(
                url=url,
                headers=headers,
                json=json,
                params=params,
                timeout=timeout,
            )
            return FakeResponse()

    namespace["requests"] = FakeRequests
    actor_input = {"maxItems": 50, "maxItemsPerTarget": 25}
    live_pricing = {
        "pricingModel": "PAY_PER_EVENT",
        "startedAt": "2026-04-23T18:16:44.850Z",
    }
    run_options = {"maxTotalChargeUsd": 5.0}
    fingerprint = namespace["canonical_request_fingerprint"](
        "xquik~x-tweet-scraper",
        actor_input,
        run_options,
        live_pricing,
    )

    run_id = namespace["start_paid_actor"](
        "xquik~x-tweet-scraper",
        actor_input,
        approved_input_max_items=50,
        max_total_charge_usd=5.0,
        configured_input_max_items=100,
        configured_max_total_charge_usd=5.0,
        live_pricing=live_pricing,
        approval_record={
            "approved": True,
            "requestFingerprint": fingerprint,
        },
    )

    assert run_id == "run-1"
    assert captured["params"] == {"maxTotalChargeUsd": 5.0}
    assert "maxItems" not in captured["params"]
    assert captured["json"] == actor_input
    assert captured["headers"] == {"Authorization": "Bearer test-token"}
    assert captured["timeout"] == 30


def test_paid_actor_rejects_pricing_model_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace = load_reference_helpers(monkeypatch)
    with pytest.raises(ValueError, match="PAY_PER_EVENT"):
        namespace["start_paid_actor"](
            "xquik~x-tweet-scraper",
            {"maxItems": 50},
            approved_input_max_items=50,
            max_total_charge_usd=5.0,
            configured_input_max_items=100,
            configured_max_total_charge_usd=5.0,
            live_pricing={"pricingModel": "PAY_PER_RESULT"},
            approval_record={},
        )
