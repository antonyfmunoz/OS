"""JavaScript parser — regex-based symbol + import extraction.

Deliberately dependency-free: no node_modules, no tree-sitter. Good enough
for graph-level relationships; opens the source file when precise ASTs matter.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import ParsedFile, ParsedImport, ParsedSymbol, Parser

ROOT = Path("/opt/OS")

RE_IMPORT_FROM = re.compile(
    r"""import\s+(?:(?P<default>[\w$]+)\s*,?\s*)?(?:\{(?P<named>[^}]+)\}\s*)?(?:\*\s+as\s+(?P<star>[\w$]+)\s*)?from\s+['"](?P<mod>[^'"]+)['"]""",
    re.M,
)
RE_REQUIRE = re.compile(
    r"""(?:const|let|var)\s+(?P<lhs>[\w${},:\s]+?)\s*=\s*require\(\s*['"](?P<mod>[^'"]+)['"]\s*\)""",
    re.M,
)
RE_SIDE_IMPORT = re.compile(r"""^\s*import\s+['"](?P<mod>[^'"]+)['"]""", re.M)
RE_EXPORT_FN = re.compile(
    r"""^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(?P<name>[\w$]+)\s*\(""",
    re.M,
)
RE_EXPORT_CLASS = re.compile(
    r"""^\s*(?:export\s+(?:default\s+)?)?class\s+(?P<name>[\w$]+)""", re.M
)
RE_ARROW_CONST = re.compile(
    r"""^\s*(?:export\s+)?const\s+(?P<name>[\w$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>""",
    re.M,
)
RE_ENTRY = re.compile(r"(?:app|server|bot)\.listen\(|process\.argv|#!/usr/bin/env\s+node")


class JSParser(Parser):
    language = "javascript"
    extensions = (".js", ".jsx", ".mjs", ".cjs")

    def parse(self, path: Path) -> ParsedFile:
        source = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        parsed = ParsedFile(
            path=rel,
            language=self.language,
            line_count=source.count("\n") + 1,
            size_bytes=path.stat().st_size,
            is_entry_point=bool(RE_ENTRY.search(source)),
        )

        self._extract_imports(source, parsed)
        self._extract_symbols(source, parsed)
        return parsed

    def _extract_imports(self, source: str, parsed: ParsedFile) -> None:
        for m in RE_IMPORT_FROM.finditer(source):
            mod = m.group("mod")
            if m.group("default"):
                parsed.imports.append(
                    ParsedImport(module=mod, symbol=m.group("default"), kind="import")
                )
            if m.group("named"):
                for name in m.group("named").split(","):
                    n = name.strip().split(" as ")[0].strip()
                    if n:
                        parsed.imports.append(
                            ParsedImport(module=mod, symbol=n, kind="from")
                        )
            if m.group("star"):
                parsed.imports.append(
                    ParsedImport(module=mod, alias=m.group("star"), kind="import")
                )
        for m in RE_REQUIRE.finditer(source):
            parsed.imports.append(ParsedImport(module=m.group("mod"), kind="require"))
        for m in RE_SIDE_IMPORT.finditer(source):
            parsed.imports.append(ParsedImport(module=m.group("mod"), kind="import"))

    def _extract_symbols(self, source: str, parsed: ParsedFile) -> None:
        for m in RE_EXPORT_CLASS.finditer(source):
            line = source[: m.start()].count("\n") + 1
            parsed.symbols.append(ParsedSymbol(name=m.group("name"), kind="class", line=line))
        for m in RE_EXPORT_FN.finditer(source):
            line = source[: m.start()].count("\n") + 1
            parsed.symbols.append(
                ParsedSymbol(name=m.group("name"), kind="function", line=line)
            )
        for m in RE_ARROW_CONST.finditer(source):
            line = source[: m.start()].count("\n") + 1
            parsed.symbols.append(
                ParsedSymbol(name=m.group("name"), kind="function", line=line)
            )
