import ast
import copy
import inspect
import re
import textwrap
from pathlib import Path
from typing import cast

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


def documented_function(name: str) -> ast.FunctionDef:
    for block in python_blocks(REFERENCE):
        module = ast.parse(block, filename=str(REFERENCE))
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
    raise AssertionError(f"Documented function not found: {name}")


def reference_validate_x_dataset(
    items: object,
    approved_global_cap: int,
    approved_per_target_cap: int,
    approved_targets: list[str],
) -> list[dict[str, object]]:
    """Validate object rows against approved aggregate and per-target caps."""
    approved_caps = (approved_global_cap, approved_per_target_cap)
    if any(isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0 for cap in approved_caps):
        raise ValueError("Invalid caps. Use positive approved caps.")
    if not approved_targets or any(
        not isinstance(target, str) or not target.strip().removeprefix("@").strip()
        for target in approved_targets
    ):
        raise ValueError("Invalid targets. Use approved target identities.")
    normalized_targets = {
        target.strip().removeprefix("@").casefold() for target in approved_targets
    }
    if not isinstance(items, list):
        raise ValueError("Invalid dataset. Expected a list.")
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("Invalid dataset. Expected object rows.")
    data_items = [item for item in items if item.get("resultType") != "diagnostic"]
    target_items: list[dict[str, object]] = []
    target_counts = {target: 0 for target in normalized_targets}
    for item in data_items:
        row_targets: list[object] = []
        if isinstance(item.get("sourceTargets"), list):
            row_targets.extend(item["sourceTargets"])
        if item.get("sourceTarget") is not None:
            row_targets.append(item["sourceTarget"])
        normalized_row_targets = {
            value.strip().removeprefix("@").casefold()
            for value in row_targets
            if isinstance(value, str) and value.strip()
        }
        if not normalized_row_targets:
            raise ValueError("Missing target provenance. Stop processing.")
        matched_targets = normalized_targets & normalized_row_targets
        if matched_targets:
            target_items.append(item)
        for matched_target in matched_targets:
            target_counts[matched_target] += 1
    if len(target_items) > approved_global_cap:
        raise ValueError("Cap exceeded. Stop downstream processing.")
    if any(count > approved_per_target_cap for count in target_counts.values()):
        raise ValueError("Per-target cap exceeded. Stop processing.")
    return target_items


def test_apify_python_blocks_parse_without_execution() -> None:
    parsed = 0
    for path in APIFY_DOCS:
        for index, block in enumerate(python_blocks(path), 1):
            ast.parse(block, filename=f"{path}:python-block-{index}")
            parsed += 1
    assert parsed == 38


def test_paid_actor_documents_safe_request_contract() -> None:
    function = documented_function("start_paid_actor")
    run_options = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "run_options" for target in node.targets
        )
    )
    expected_options = ast.parse(
        '{"maxTotalChargeUsd": max_total_charge_usd}',
        mode="eval",
    ).body
    post_call = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "requests.post"
    )
    post_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in post_call.keywords}
    exception_types = {
        ast.unparse(handler.type)
        for handler in ast.walk(function)
        if isinstance(handler, ast.ExceptHandler) and handler.type is not None
    }
    raised_names = [
        ast.unparse(node.exc.func)
        for node in ast.walk(function)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, (ast.Name, ast.Attribute))
    ]
    called_names = {
        ast.unparse(node.func) for node in ast.walk(function) if isinstance(node, ast.Call)
    }
    constants = {
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert ast.dump(run_options.value) == ast.dump(expected_options)
    assert "/v2/actors/" in ast.unparse(post_call.args[0])
    assert "/v2/acts/" not in ast.unparse(post_call.args[0])
    assert post_keywords["params"] == "run_options"
    assert post_keywords["json"] == "actor_input"
    assert post_keywords["timeout"] == "30"
    assert "requests.RequestException" in exception_types
    assert raised_names.count("RunSubmissionUncertain") >= 4
    assert "retry_after_seconds" in called_names
    assert "time.sleep" in called_names
    assert "PAY_PER_EVENT" in constants


def test_dataset_reference_matches_documentation() -> None:
    documented = copy.deepcopy(documented_function("validate_x_dataset"))
    trusted = ast.parse(textwrap.dedent(inspect.getsource(reference_validate_x_dataset))).body[0]
    assert isinstance(trusted, ast.FunctionDef)
    documented.name = trusted.name
    assert ast.dump(documented) == ast.dump(trusted)


def test_dataset_filters_diagnostics_and_unapproved_targets() -> None:
    approved = {"id": "approved", "sourceTarget": "@OpenAI"}
    overlap = {"id": "overlap", "sourceTargets": ["openai", "GitHub"]}
    items = [
        {"resultType": "diagnostic", "message": "partial"},
        approved,
        {"id": "unapproved", "sourceTarget": "other"},
        overlap,
    ]

    result = reference_validate_x_dataset(items, 2, 2, ["openai", "@github"])

    assert result == [approved, overlap]


@pytest.mark.parametrize(
    ("items", "global_cap", "per_target_cap", "message"),
    (
        (
            [{"sourceTarget": "openai"}, {"sourceTarget": "openai"}],
            1,
            2,
            "Cap exceeded",
        ),
        (
            [{"sourceTarget": "openai"}, {"sourceTarget": "openai"}],
            2,
            1,
            "Per-target cap exceeded",
        ),
        ([{"id": "missing"}], 1, 1, "Missing target provenance"),
    ),
)
def test_dataset_rejects_invalid_bounds_or_provenance(
    items: list[dict[str, object]],
    global_cap: int,
    per_target_cap: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        reference_validate_x_dataset(
            items,
            global_cap,
            per_target_cap,
            ["openai"],
        )


@pytest.mark.parametrize(
    ("global_cap", "per_target_cap", "approved_targets", "message"),
    (
        (True, 1, ["openai"], "Invalid caps"),
        (1, 1.5, ["openai"], "Invalid caps"),
        (1, 1, [], "Invalid targets"),
        (1, 1, ["@"], "Invalid targets"),
        (1, 1, [1], "Invalid targets"),
    ),
)
def test_dataset_rejects_invalid_approval_contract(
    global_cap: object,
    per_target_cap: object,
    approved_targets: list[object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        reference_validate_x_dataset(
            [],
            cast(int, global_cap),
            cast(int, per_target_cap),
            cast(list[str], approved_targets),
        )
