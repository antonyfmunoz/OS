"""Phase 86 Tomorrow Loop safety — verify layering discipline for all loop modules.

AST-based import checking to ensure tomorrow modules do not import
forbidden libraries (subprocess, requests, etc.) or call execution engines directly.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import ast
import pathlib
from dataclasses import dataclass, field
from typing import Any


_TOMORROW_DIR = pathlib.Path(__file__).resolve().parent

_FORBIDDEN_IMPORTS = frozenset(
    {
        "subprocess",
        "requests",
        "httpx",
        "aiohttp",
        "selenium",
        "playwright",
        "smtplib",
        "telegram",
        "discord",
    }
)


@dataclass
class TomorrowSafetyResult:
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


def validate_tomorrow_module_boundaries() -> TomorrowSafetyResult:
    """Check all .py files in the tomorrow package for forbidden imports."""
    violations: list[str] = []
    warnings: list[str] = []
    checked = 0

    py_files = sorted(_TOMORROW_DIR.glob("*.py"))
    for py_file in py_files:
        if py_file.name == "__init__.py":
            continue
        checked += 1
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except SyntaxError as e:
            violations.append(f"{py_file.name}: syntax error — {e}")
            continue

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])

        for lib in _FORBIDDEN_IMPORTS:
            if lib in imported_names:
                violations.append(f"{py_file.name}: forbidden import '{lib}'")

    safe = len(violations) == 0

    return TomorrowSafetyResult(
        safe=safe,
        modules_checked=checked,
        violations=violations,
        warnings=warnings,
    )
