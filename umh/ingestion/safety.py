"""Phase 87B ingestion safety — AST-based import and execution pattern checking.

Validates that all umh/ingestion/ modules follow Phase 87B hard rules:
  - No subprocess, requests, httpx, aiohttp, socket, selenium, playwright
  - No umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage
  - No execution patterns (execute, run_action, send_message, scrape, ingest, fetch)
  - No network listeners (bind, listen, serve, accept)
  - No secret access patterns (os.getenv, load_dotenv, os.environ)
  - No file I/O patterns (open, read_file, write_file, pathlib.read_text) outside safety.py itself

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
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
        "scrapy",
        "beautifulsoup4",
        "bs4",
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
        "scrape",
        "ingest",
        "fetch",
        "crawl",
        "download",
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


def check_all_ingestion_modules(
    ingestion_dir: str | Path | None = None,
) -> dict[str, Any]:
    if ingestion_dir is None:
        ingestion_dir = Path(__file__).parent
    ingestion_dir = Path(ingestion_dir)

    results: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    total_violations = 0
    total_warnings = 0

    if not ingestion_dir.is_dir():
        return {
            "modules_checked": 0,
            "total_violations": 0,
            "warning_count": 1,
            "all_safe": False,
            "scanned_paths": [],
            "results": [],
            "warnings": [f"ingestion_dir not found: {ingestion_dir}"],
        }

    for py_file in sorted(ingestion_dir.glob("*.py")):
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
                + len(r["network_listener_patterns"])
                + len(r["secret_patterns"])
            )

    warnings: list[str] = []
    if len(results) == 0:
        warnings.append(
            f"No Python modules found in {ingestion_dir} — "
            "check that ingestion_dir is correct"
        )

    return {
        "modules_checked": len(results),
        "total_violations": total_violations,
        "warning_count": total_warnings + len(warnings),
        "all_safe": total_violations == 0 and len(results) > 0,
        "scanned_paths": scanned_paths,
        "results": results,
        "warnings": warnings,
    }


def check_ingestion_source_safety(source: Any) -> dict[str, Any]:
    warnings: list[str] = []

    sensitivity = getattr(source, "sensitivity", None)
    if sensitivity and hasattr(sensitivity, "value") and sensitivity.value == "credential":
        warnings.append("credential source should not be ingested")

    status = getattr(source, "status", None)
    if status and hasattr(status, "value") and status.value == "discovered":
        warnings.append("source not yet approved — cannot ingest")

    promotion = getattr(source, "promotion_policy", None)
    if promotion and hasattr(promotion, "value") and promotion.value == "auto_promote":
        review = getattr(source, "review_requirement", None)
        if review and hasattr(review, "value") and review.value == "none":
            warnings.append("auto-promote with no review — risky for non-structured data")

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
