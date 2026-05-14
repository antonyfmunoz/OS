"""Python parser — wraps the existing AST scanner in codebase_graph.py.

The authoritative Python scanner lives at scripts/codebase_graph.py and
drives the full JSON graph. This wrapper lets the modular parser system
route Python files through that same logic so the graph stays single-source.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

from .base import ParsedFile, ParsedImport, ParsedSymbol, Parser

ROOT = Path("/opt/OS")
ENTRY_PATTERNS = [
    r'if\s+__name__\s*==\s*["\']__main__["\']',
    r"app\.run\(",
    r"bot\.run\(",
    r"uvicorn\.run\(",
    r"argparse\.ArgumentParser",
]


def _load_legacy_scanner():
    """Load scripts/codebase_graph.py as a module for reuse."""
    spec = importlib.util.spec_from_file_location(
        "_eos_codebase_graph", ROOT / "scripts" / "codebase_graph.py"
    )
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_eos_codebase_graph"] = mod
    spec.loader.exec_module(mod)
    return mod


_LEGACY = None


class PythonParser(Parser):
    language = "python"
    extensions = (".py",)

    def parse(self, path: Path) -> ParsedFile:
        global _LEGACY
        if _LEGACY is None:
            _LEGACY = _load_legacy_scanner()

        source = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        parsed = ParsedFile(
            path=rel,
            language=self.language,
            line_count=source.count("\n") + 1,
            size_bytes=path.stat().st_size,
            is_entry_point=any(re.search(p, source) for p in ENTRY_PATTERNS),
        )

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return parsed

        parsed.docstring = ast.get_docstring(tree)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parsed.imports.append(
                        ParsedImport(module=alias.name, alias=alias.asname, kind="import")
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    parsed.imports.append(
                        ParsedImport(
                            module=module,
                            symbol=alias.name,
                            alias=alias.asname,
                            kind="from",
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                parsed.symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        kind="class",
                        line=node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parsed.symbols.append(
                            ParsedSymbol(
                                name=item.name,
                                kind="function",
                                line=item.lineno,
                                parent=node.name,
                                docstring=ast.get_docstring(item),
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed.symbols.append(
                    ParsedSymbol(
                        name=node.name,
                        kind="function",
                        line=node.lineno,
                        docstring=ast.get_docstring(node),
                    )
                )

        for child in ast.walk(tree):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    parsed.calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    parsed.calls.append(child.func.attr)

        return parsed
