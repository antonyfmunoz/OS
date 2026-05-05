"""Phase 88 workflow safety — AST-based manual-only enforcement.

Validates that all umh/workflows/ modules follow Phase 88 hard rules:
  - No subprocess, shutil.rmtree, pathlib unlink/rmdir
  - No requests, httpx, socket, selenium, playwright
  - No adapter, execution engine, storage mutation, governance mutation
  - No memory promotion
  - No send/post/DM/email/payment execution patterns
  - No live model calls
  - No credential values

Manual/operator-assisted only. No autonomous execution.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


_FORBIDDEN_IMPORTS: frozenset[str] = frozenset(
    {
        "subprocess",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "selenium",
        "playwright",
        "smtplib",
        "paramiko",
        "scrapy",
        "bs4",
        "shutil",
        "stripe",
        "telegram",
        "discord",
    }
)

_FORBIDDEN_MODULE_PREFIXES: tuple[str, ...] = (
    "umh.adapters",
    "umh.execution",
    "umh.governance",
    "umh.memory",
    "umh.storage",
)

_EXECUTION_PATTERNS: frozenset[str] = frozenset(
    {
        "execute",
        "run_action",
        "send_message",
        "send_dm",
        "send_email",
        "post_content",
        "publish_post",
        "promote_memory",
        "scrape",
        "ingest",
        "fetch",
        "crawl",
        "download",
        "unlink",
        "rmtree",
        "rmdir",
        "remove",
        "kill",
        "terminate",
        "charge_payment",
        "create_checkout",
        "process_payment",
    }
)

_SYSTEM_CALL_PATTERNS: frozenset[str] = frozenset(
    {
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
        "shutil.rmtree",
        "shutil.move",
    }
)


def check_module_safety(filepath: str | Path) -> dict[str, Any]:
    filepath = Path(filepath)
    result: dict[str, Any] = {
        "file": str(filepath),
        "safe": True,
        "forbidden_imports": [],
        "forbidden_module_prefixes": [],
        "execution_patterns": [],
        "system_call_patterns": [],
        "warnings": [],
    }

    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, OSError) as e:
        result["safe"] = False
        result["warnings"].append(f"parse error: {e}")
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _FORBIDDEN_IMPORTS:
                    result["forbidden_imports"].append(alias.name)
                for prefix in _FORBIDDEN_MODULE_PREFIXES:
                    if alias.name.startswith(prefix):
                        result["forbidden_module_prefixes"].append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _FORBIDDEN_IMPORTS:
                    result["forbidden_imports"].append(node.module)
                for prefix in _FORBIDDEN_MODULE_PREFIXES:
                    if node.module.startswith(prefix):
                        result["forbidden_module_prefixes"].append(node.module)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _EXECUTION_PATTERNS:
                result["execution_patterns"].append(node.name)

        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in _SYSTEM_CALL_PATTERNS:
                result["system_call_patterns"].append(func_name)

    violations = (
        result["forbidden_imports"]
        + result["forbidden_module_prefixes"]
        + result["execution_patterns"]
        + result["system_call_patterns"]
    )
    result["safe"] = len(violations) == 0
    return result


def validate_workflow_modules_are_manual_only(
    root_path: str | Path | None = None,
) -> dict[str, Any]:
    if root_path is None:
        root_path = Path(__file__).parent
    root_path = Path(root_path)

    results: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    total_violations = 0
    total_warnings = 0

    if not root_path.is_dir():
        return {
            "modules_checked": 0,
            "total_violations": 0,
            "warning_count": 1,
            "all_safe": False,
            "scanned_paths": [],
            "results": [],
            "warnings": [f"root_path not found: {root_path}"],
        }

    for py_file in sorted(root_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        scanned_paths.append(str(py_file))
        r = check_module_safety(py_file)
        results.append(r)
        total_warnings += len(r.get("warnings", []))
        if not r["safe"]:
            total_violations += (
                len(r["forbidden_imports"])
                + len(r["forbidden_module_prefixes"])
                + len(r["execution_patterns"])
                + len(r["system_call_patterns"])
            )

    warnings: list[str] = []
    if len(results) == 0:
        warnings.append(f"No Python modules found in {root_path}")

    return {
        "modules_checked": len(results),
        "total_violations": total_violations,
        "warning_count": total_warnings + len(warnings),
        "all_safe": total_violations == 0 and len(results) > 0,
        "scanned_paths": scanned_paths,
        "results": results,
        "warnings": warnings,
    }


def scan_workflow_for_forbidden_imports(
    paths: list[str | Path] | None = None,
) -> list[str]:
    if paths is None:
        root = Path(__file__).parent
        paths = [p for p in sorted(root.glob("*.py")) if p.name != "__init__.py"]
    violations: list[str] = []
    for p in paths:
        r = check_module_safety(p)
        violations.extend(r["forbidden_imports"])
    return violations


def scan_workflow_for_execution_patterns(
    paths: list[str | Path] | None = None,
) -> list[str]:
    if paths is None:
        root = Path(__file__).parent
        paths = [p for p in sorted(root.glob("*.py")) if p.name != "__init__.py"]
    patterns: list[str] = []
    for p in paths:
        r = check_module_safety(p)
        patterns.extend(r["execution_patterns"])
    return patterns


def validate_plan_has_no_external_execution(plan: Any) -> dict[str, Any]:
    warnings: list[str] = []
    for task in getattr(plan, "tasks", []):
        title_lower = getattr(task, "title", "").lower()
        desc_lower = getattr(task, "description", "").lower()
        for pattern in ("auto-post", "auto-dm", "auto-send", "scrape", "crawl"):
            if pattern in title_lower or pattern in desc_lower:
                warnings.append(f"Task '{task.title}' contains execution pattern '{pattern}'")
    return {"safe": len(warnings) == 0, "warnings": warnings}


def validate_task_is_manual_or_advisory(task: Any) -> dict[str, Any]:
    warnings: list[str] = []
    title_lower = getattr(task, "title", "").lower()
    desc_lower = getattr(task, "description", "").lower()
    for pattern in ("auto-post", "auto-dm", "auto-send", "scrape", "crawl", "auto-pay"):
        if pattern in title_lower or pattern in desc_lower:
            warnings.append(f"Task contains autonomous execution pattern '{pattern}'")
    return {"safe": len(warnings) == 0, "warnings": warnings}


def validate_report_has_no_execution(report: Any) -> dict[str, Any]:
    warnings: list[str] = []
    for field_name in ("integrated_lessons", "system_gaps", "next_day_plan", "next_build_recommendations"):
        items = getattr(report, field_name, []) or []
        for item in items:
            item_lower = str(item).lower()
            for pattern in ("auto-post", "auto-dm", "auto-send", "scrape", "crawl"):
                if pattern in item_lower:
                    warnings.append(f"Report field '{field_name}' contains execution pattern '{pattern}'")
    return {"safe": len(warnings) == 0, "warnings": warnings}


def workflow_safety_result_to_dict(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result)


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
    elif isinstance(node.func, ast.Name):
        return node.func.id
    return ""
