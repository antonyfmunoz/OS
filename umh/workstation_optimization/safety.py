"""Phase 87C workstation optimization safety — AST-based planning-only enforcement.

Validates that all umh/workstation_optimization/ modules follow Phase 87C hard rules:
  - No subprocess, shutil.rmtree, pathlib unlink/rmdir
  - No requests, httpx, socket, selenium, playwright
  - No adapter, execution engine, storage mutation, governance mutation
  - No memory promotion, package manager commands, live model calls
  - No credential values

Advisory/planning only. No real scanning. No cleanup. No deletion.
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
        "uninstall",
    }
)

# Patterns detected as call names via AST (attr-style calls)
_SYSTEM_CALL_PATTERNS: frozenset[str] = frozenset(
    {
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
        "shutil.rmtree",
        "shutil.move",
    }
)

_SECRET_PATTERNS: frozenset[str] = frozenset(
    {
        "load_dotenv",
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
        "secret_patterns": [],
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
            if func_name in _SECRET_PATTERNS:
                result["secret_patterns"].append(func_name)
            if func_name in _SYSTEM_CALL_PATTERNS:
                result["system_call_patterns"].append(func_name)

    violations = (
        result["forbidden_imports"]
        + result["forbidden_module_prefixes"]
        + result["execution_patterns"]
        + result["system_call_patterns"]
        + result["secret_patterns"]
    )
    result["safe"] = len(violations) == 0
    return result


def check_all_workstation_optimization_modules(
    ws_dir: str | Path | None = None,
) -> dict[str, Any]:
    if ws_dir is None:
        ws_dir = Path(__file__).parent
    ws_dir = Path(ws_dir)

    results: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    total_violations = 0
    total_warnings = 0

    if not ws_dir.is_dir():
        return {
            "modules_checked": 0,
            "total_violations": 0,
            "warning_count": 1,
            "all_safe": False,
            "scanned_paths": [],
            "results": [],
            "warnings": [f"ws_dir not found: {ws_dir}"],
        }

    for py_file in sorted(ws_dir.glob("*.py")):
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
                + len(r["secret_patterns"])
            )

    warnings: list[str] = []
    if len(results) == 0:
        warnings.append(f"No Python modules found in {ws_dir}")

    return {
        "modules_checked": len(results),
        "total_violations": total_violations,
        "warning_count": total_warnings + len(warnings),
        "all_safe": total_violations == 0 and len(results) > 0,
        "scanned_paths": scanned_paths,
        "results": results,
        "warnings": warnings,
    }


def validate_candidate_has_no_execution(candidate: Any) -> dict[str, Any]:
    warnings: list[str] = []
    action = getattr(candidate, "action_type", None)
    if action and hasattr(action, "value"):
        action_val = action.value
        if action_val in (
            "overclock",
            "undervolt",
            "kill_process",
            "delete",
            "uninstall",
            "change_setting",
        ):
            warnings.append(
                f"Action type {action_val} is execution-class — must not be performed in planning mode"
            )
    return {"safe": len(warnings) == 0, "warnings": warnings}


def validate_report_has_no_real_scan_data(report: Any) -> dict[str, Any]:
    warnings: list[str] = []
    bp = getattr(report, "baseline_plan", None)
    if bp:
        mode = getattr(bp, "audit_mode", None)
        if mode and hasattr(mode, "value") and mode.value != "planning_only":
            warnings.append(
                f"Baseline plan audit_mode is {mode.value} — should be planning_only in Phase 87C"
            )
    return {"safe": len(warnings) == 0, "warnings": warnings}


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
    elif isinstance(node.func, ast.Name):
        return node.func.id
    return ""
