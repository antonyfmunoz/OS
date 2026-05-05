"""Phase 87 leverage safety — verify layering discipline for all leverage modules.

AST-based import checking to ensure leverage modules do not import
forbidden libraries or call execution engines directly.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import ast
import pathlib
from dataclasses import dataclass, field
from typing import Any


_LEVERAGE_DIR = pathlib.Path(__file__).resolve().parent

_FORBIDDEN_IMPORTS = frozenset(
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
    }
)

_FORBIDDEN_MODULE_PREFIXES = (
    "umh.adapters",
    "umh.execution",
    "umh.governance",
    "umh.memory",
    "umh.storage",
)

_EXECUTION_PATTERNS = frozenset(
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


@dataclass
class LeverageSafetyResult:
    safe: bool = True
    modules_checked: int = 0
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "modules_checked": self.modules_checked,
            "violations": self.violations,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def validate_leverage_modules_are_advisory_only(
    root_path: str | None = None,
) -> LeverageSafetyResult:
    base = pathlib.Path(root_path) if root_path else _LEVERAGE_DIR
    result = _scan_directory(base)
    exec_result = scan_leverage_for_execution_patterns(
        [str(f) for f in sorted(base.glob("*.py")) if f.name != "__init__.py"]
    )
    result.violations.extend(exec_result.violations)
    result.warnings.extend(exec_result.warnings)
    result.safe = len(result.violations) == 0
    return result


def scan_leverage_for_forbidden_imports(
    paths: list[str] | None = None,
) -> LeverageSafetyResult:
    if paths:
        return _scan_files([pathlib.Path(p) for p in paths])
    return _scan_directory(_LEVERAGE_DIR)


def _scan_directory(base: pathlib.Path) -> LeverageSafetyResult:
    py_files = sorted(base.glob("*.py"))
    return _scan_files([f for f in py_files if f.name != "__init__.py"])


def _scan_files(files: list[pathlib.Path]) -> LeverageSafetyResult:
    violations: list[str] = []
    warnings: list[str] = []
    checked = 0

    for py_file in files:
        if not py_file.exists():
            warnings.append(f"{py_file}: file not found")
            continue
        checked += 1
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except SyntaxError as e:
            violations.append(f"{py_file.name}: syntax error — {e}")
            continue

        imported_names: set[str] = set()
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])
                    imported_modules.add(node.module)

        for lib in _FORBIDDEN_IMPORTS:
            if lib in imported_names:
                violations.append(f"{py_file.name}: forbidden import '{lib}'")

        for mod in imported_modules:
            for prefix in _FORBIDDEN_MODULE_PREFIXES:
                if mod.startswith(prefix):
                    violations.append(f"{py_file.name}: forbidden module import '{mod}'")

    return LeverageSafetyResult(
        safe=len(violations) == 0,
        modules_checked=checked,
        violations=violations,
        warnings=warnings,
    )


def scan_leverage_for_execution_patterns(
    paths: list[str] | None = None,
) -> LeverageSafetyResult:
    violations: list[str] = []
    warnings: list[str] = []
    checked = 0

    files = [pathlib.Path(p) for p in (paths or [])]
    if not files:
        files = [f for f in sorted(_LEVERAGE_DIR.glob("*.py")) if f.name != "__init__.py"]

    for py_file in files:
        if not py_file.exists():
            continue
        checked += 1
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                fname = ""
                if isinstance(func, ast.Name):
                    fname = func.id
                elif isinstance(func, ast.Attribute):
                    fname = func.attr
                if fname in _EXECUTION_PATTERNS:
                    violations.append(
                        f"{py_file.name}:{node.lineno}: execution pattern '{fname}()'"
                    )

    return LeverageSafetyResult(
        safe=len(violations) == 0,
        modules_checked=checked,
        violations=violations,
        warnings=warnings,
    )


def validate_leverage_recommendation_has_no_execution(
    recommendation: Any,
) -> LeverageSafetyResult:
    violations: list[str] = []
    warnings: list[str] = []

    action = getattr(recommendation, "action", None)
    if action and hasattr(action, "value"):
        action_val = action.value
    else:
        action_val = str(action or "")

    if action_val in ("execute", "deploy", "send", "post", "delete"):
        violations.append(f"Recommendation action '{action_val}' implies execution")

    first_step = getattr(recommendation, "first_step", "")
    for pattern in ["execute immediately", "deploy now", "send message", "post to"]:
        if pattern in first_step.lower():
            warnings.append(f"First step contains execution-like language: '{pattern}'")

    return LeverageSafetyResult(
        safe=len(violations) == 0,
        modules_checked=1,
        violations=violations,
        warnings=warnings,
    )


def leverage_safety_result_to_dict(result: LeverageSafetyResult) -> dict[str, Any]:
    return result.to_dict()
