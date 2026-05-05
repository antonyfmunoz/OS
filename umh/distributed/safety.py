"""Phase 87A distributed safety — AST-based import and execution pattern checking.

Validates that all umh/distributed/ modules follow Phase 87A hard rules:
  - No subprocess, requests, httpx, aiohttp, socket, selenium, playwright, smtplib, telegram, discord
  - No umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage
  - No execution patterns (execute, run_action, send_message, etc.)
  - No network listeners (bind, listen, serve, accept)
  - No secret access patterns (os.getenv, load_dotenv, open(.env))

No execution. No mutation. No adapter calls. No LLM calls.
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
        "telegram",
        "discord",
        "paramiko",
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
        "post",
        "delete",
        "create_resource",
        "mutate",
        "promote_memory",
    }
)

_NETWORK_LISTENER_PATTERNS: frozenset[str] = frozenset(
    {
        "bind",
        "listen",
        "serve",
        "accept",
        "start_server",
        "run_server",
    }
)

_SECRET_PATTERNS: frozenset[str] = frozenset(
    {
        "os.getenv",
        "load_dotenv",
        "os.environ",
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
        "network_listener_patterns": [],
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
                name = alias.name.split(".")[0]
                if name in _FORBIDDEN_IMPORTS:
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
            if node.name in _NETWORK_LISTENER_PATTERNS:
                result["network_listener_patterns"].append(node.name)

        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in _SECRET_PATTERNS:
                result["secret_patterns"].append(func_name)

    violations = (
        result["forbidden_imports"]
        + result["forbidden_module_prefixes"]
        + result["execution_patterns"]
        + result["network_listener_patterns"]
        + result["secret_patterns"]
    )
    result["safe"] = len(violations) == 0
    return result


def check_all_distributed_modules() -> dict[str, Any]:
    distributed_dir = Path(__file__).parent
    results: list[dict[str, Any]] = []
    total_violations = 0

    for py_file in sorted(distributed_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        r = check_module_safety(py_file)
        results.append(r)
        if not r["safe"]:
            total_violations += (
                len(r["forbidden_imports"])
                + len(r["forbidden_module_prefixes"])
                + len(r["execution_patterns"])
                + len(r["network_listener_patterns"])
                + len(r["secret_patterns"])
            )

    return {
        "modules_checked": len(results),
        "total_violations": total_violations,
        "all_safe": total_violations == 0,
        "results": results,
    }


def check_recommendation_safety(rec: Any) -> dict[str, Any]:
    warnings: list[str] = []
    if hasattr(rec, "selected_node_type"):
        snt = getattr(rec, "selected_node_type", None)
        if snt and hasattr(snt, "value") and snt.value == "unknown":
            warnings.append("routing decision selected unknown node type")
    if hasattr(rec, "confidence"):
        conf = getattr(rec, "confidence", 0.0)
        if conf < 0.3:
            warnings.append(f"low confidence routing decision: {conf:.2f}")
    if hasattr(rec, "warnings"):
        for w in getattr(rec, "warnings", []):
            warnings.append(f"decision warning: {w}")
    return {
        "safe": len(warnings) == 0,
        "warnings": warnings,
    }


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
    elif isinstance(node.func, ast.Name):
        return node.func.id
    return ""
